# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""A provider whose only job is this role is tried before a generalist."""
from __future__ import annotations

from pathlib import Path

from _load_addon import engine_source, load_module

_ROOT = Path(__file__).resolve().parents[1]
fit = load_module('provider_fit', 'utils', 'provider_fit.py')
_ENGINE = (_ROOT / 'common' / 'models' / 'ai_execution_engine.py').read_text(
    encoding='utf-8',
)


def _door():
    return _ENGINE.split('def get_providers_for_agent', 1)[1].split(
        '\n    @api.model', 1,
    )[0]


def _rule():
    return _ENGINE.split('def _specialists_first', 1)[1].split(
        '\n    @api.model', 1,
    )[0]


def test_one_tick_is_a_specialist_and_two_are_not():
    assert fit.is_specialist({'design': True}, 'design') is True
    assert fit.is_specialist({'design': True, 'conversation': True}, 'design') is False
    assert fit.is_specialist({'decision': True}, 'decision') is True
    assert fit.is_specialist({'conversation': True}, 'design') is False
    # No ticks is text only, not a specialist in anything.
    assert fit.is_specialist({}, 'design') is False
    assert fit.is_specialist({}, None) is False


def test_the_specialist_jumps_the_generalist_declared_first():
    order = ['chat_and_design', 'design_only', 'chat_only']
    flags = {
        'chat_and_design': {'conversation': True, 'design': True},
        'design_only': {'design': True},
        'chat_only': {'conversation': True},
    }
    ranked = sorted(
        [code for code in order if fit.provider_fits(flags[code], 'design')],
        key=lambda code: (
            0 if fit.is_specialist(flags[code], 'design') else 1,
            order.index(code),
        ),
    )
    assert ranked == ['design_only', 'chat_and_design']


def test_the_dialogue_chain_keeps_the_order_the_human_wrote():
    rule = _rule()
    assert "if not need or need == 'conversation' or len(providers) < 2:" in rule
    assert 'return providers' in rule
    # Declared priority still breaks ties, both among specialists and among
    # generalists: the rule reorders by role, it does not shuffle.
    assert 'declared[p.id]' in rule
    assert 'is_specialist' in rule


def test_a_role_without_a_provider_leaves_a_row_for_the_admin():
    row = _ENGINE.split('def _log_role_without_provider', 1)[1].split(
        '\n    def ', 1,
    )[0]
    assert 'tool_name=CAPABILITY_SKIPPED' in row
    assert '_resolve_log_threading(turn, turn_step)' in row
    # ai.log is English on purpose; the role is whatever was asked for.
    assert "'No active provider carries the %s tick' % role" in row
    for word in ('design', 'decision', 'vision', 'chatboo'):
        assert word not in row
    caller = engine_source()
    early = caller.split('providers = engine.get_providers_for_agent(', 1)[1]
    early = early.split('if max_providers', 1)[0]
    assert 'engine._log_role_without_provider(code, need)' in early


def test_the_rule_lives_in_the_single_door_only():
    assert _ENGINE.count('def _specialists_first') == 1
    assert '_specialists_first(chain, need)' in _door()
    # Same reorder after the agent's chain or after the all-active fallback.
    assert 'if not chain and need and need != \'conversation\' and failovers:' in _door()
    # Not a second getter and not a protocol or model name.
    for word in ("'protocol'", '.protocol', 'systemone', 'jev'):
        assert word not in _rule()
    engine_calls = _ENGINE.count('_specialists_first(')
    assert engine_calls == 2  # the definition and the one call


def test_the_agent_form_states_the_role_rule():
    form = (
        _ROOT / 'stacks' / 'owl1' / 'pns_ai_mcp' / 'views' / 'ai_agent_views.xml'
    ).read_text(encoding='utf-8')
    assert 'a provider with only that role goes first' in form
    assert 'the fallback of the role' in form
    assert 'decision, design' in form
