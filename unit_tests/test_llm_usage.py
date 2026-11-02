# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Shape-only usage helper: tokens + vendor cost, no host checks."""
from __future__ import annotations

from _load_addon import engine_source, load_module

u = load_module('llm_usage', 'utils', 'llm_usage.py')


def test_extract_cost_aliases():
    assert u.extract_cost({'cost': 0.0042}) == 0.0042
    assert u.extract_cost({'total_cost': 1.5}) == 1.5
    assert u.extract_cost({'cost_usd': 0.01}) == 0.01
    assert u.extract_cost({'cost_in_usd_ticks': 42_000_000}) == 0.0042
    assert u.extract_cost({'prompt_tokens': 10}) is None
    assert u.extract_cost(None) is None
    # Cero conocido ≠ ausente: el chip de gasto pinta 0, no "-".
    assert u.extract_cost({'cost': 0}) == 0.0
    assert u.extract_cost({'cost': 0.0}) == 0.0


def test_missing_cost_stays_missing():
    out = u.advertise_cost(
        {'prompt_tokens': 10, 'completion_tokens': 2, 'total_tokens': 12},
    )
    assert 'cost' not in out
    assert out['total_tokens'] == 12
    assert u.advertise_cost({'cost': 0.42, 'total_tokens': 3})['cost'] == 0.42
    assert u.advertise_cost({'cost': 0})['cost'] == 0
    assert 'cost' not in u.advertise_cost({'total_tokens': 1})


def test_usage_has_tokens():
    assert u.usage_has_tokens({'prompt_tokens': 12})
    assert u.usage_has_tokens({'input_tokens': 3, 'output_tokens': 1})
    assert not u.usage_has_tokens({'cost': 0.01})
    assert not u.usage_has_tokens({})


def test_classify_usage_support():
    assert u.classify_usage_support({
        'choices': [{'message': {'content': 'ok'}}],
        'usage': {'prompt_tokens': 8, 'completion_tokens': 2, 'total_tokens': 10},
    }) == 'yes'
    assert u.classify_usage_support({
        'choices': [{'message': {'content': 'ok'}}],
    }) == 'no'
    assert u.classify_usage_support({'error': 'timeout'}) == 'unknown'


def test_normalize_sums_cache_creation_tokens():
    out = u.normalize_usage({
        'input_tokens': 100,
        'output_tokens': 20,
        'cache_creation_input_tokens': 50,
        'cache_read_input_tokens': 200,
    })
    assert out['prompt_tokens'] == 150
    assert out['completion_tokens'] == 20
    assert out['total_tokens'] == 170
    assert out['cached_tokens'] == 200
    assert out['cache_creation_tokens'] == 50


def test_normalize_and_add():
    a = u.normalize_usage({
        'prompt_tokens': 10,
        'completion_tokens': 5,
        'total_tokens': 15,
        'cost': 0.001,
        'prompt_tokens_details': {'cached_tokens': 4},
    })
    assert a['prompt_tokens'] == 10
    assert a['cached_tokens'] == 4
    assert a['cost'] == 0.001
    acc = u.add_usage({}, a)
    acc = u.add_usage(acc, {
        'input_tokens': 20,
        'output_tokens': 3,
        'cost_in_usd_ticks': 10_000_000,
    })
    assert acc['prompt_tokens'] == 30
    assert acc['completion_tokens'] == 8
    assert acc['total_tokens'] == 38
    assert abs(acc['cost'] - 0.002) < 1e-12


def test_a_satellite_folds_into_the_open_turn():
    token = u.bind_turn_side_usage()
    try:
        assert u.bound_turn_side_usage() == {}
        u.note_turn_side_usage({
            'prompt_tokens': 100, 'completion_tokens': 20, 'cost': 0.2,
        })
        bag = u.bound_turn_side_usage()
        assert bag['total_tokens'] == 120
        assert bag['cost'] == 0.2
    finally:
        u.reset_turn_side_usage(token)
    assert u.bound_turn_side_usage() == {}
    u.note_turn_side_usage({'prompt_tokens': 9})
    assert u.bound_turn_side_usage() == {}


def test_a_satellite_during_the_rounds_reaches_the_turn_total():
    """5VZC: Design ran inside relaxaicode; the summary had only Gemini."""
    token = u.bind_turn_side_usage()
    try:
        u.note_turn_side_usage({'prompt_tokens': 50, 'cost': 0.01})
        at_start = dict(u.bound_turn_side_usage())
        u.note_turn_side_usage({
            'prompt_tokens': 9000, 'completion_tokens': 7000, 'cost': 0.6,
        })
        late = u.usage_since(u.bound_turn_side_usage(), at_start)
        assert late['prompt_tokens'] == 9000
        assert late['completion_tokens'] == 7000
        assert abs(late['cost'] - 0.6) < 1e-9
        assert u.usage_since(at_start, at_start) == {}
    finally:
        u.reset_turn_side_usage(token)

    src = engine_source()
    end = src.split("usage_out = dict(turn_usage) if turn_usage else {}", 1)[0]
    assert end.rstrip().endswith(
        'add_usage(turn_usage, usage_since(self._side_usage(), side_at_start))',
    )
