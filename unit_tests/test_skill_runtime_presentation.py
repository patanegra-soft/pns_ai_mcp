# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""skill_runtime presentation recognition (no Odoo runtime)."""
from __future__ import annotations

from _load_addon import load_module, skill_source

sr = load_module('skill_runtime', 'utils', 'skill_runtime.py')


def test_presentation_from_bootstrap_accepts_tables():
    bootstrap = {
        'tables': [
            {'title': 'A', 'data': [{'x': 1}]},
            {'title': 'B', 'data': [{'y': 2}]},
        ],
        'summary': 'demo',
        'footer': 'note',
        '__return_direct__': True,
        '__stop_after_direct__': True,
    }
    pres = sr.presentation_from_bootstrap(bootstrap)
    assert pres is not None
    assert pres.get('tables')
    assert pres.get('summary') == 'demo'


def test_presentation_from_bootstrap_accepts_sections():
    bootstrap = {
        '__return_direct__': True,
        'sections': [{'title': 'S', 'data': [{'a': 1}]}],
    }
    assert sr.presentation_from_bootstrap(bootstrap) is not None


def test_presentation_from_bootstrap_rejects_meta_only():
    bootstrap = {
        '__return_direct__': True,
        'summary': 'only meta',
        'footer': 'x',
    }
    assert sr.presentation_from_bootstrap(bootstrap) is None


def test_presentation_from_bootstrap_formatted_text_without_flag():
    """Captured skills often omit __return_direct__; the card is still a result."""
    pres = sr.presentation_from_bootstrap({
        'formatted_text': '<p>5 records</p>',
    })
    assert pres is not None
    assert pres['formatted_text'] == '<p>5 records</p>'
    assert pres.get('__fmt_type__') == 'author_html'


def test_check_skill_fast_path_publishable_skips_without_env():
    assert sr.check_skill_fast_path_publishable(None, '') is None
    assert sr.check_skill_fast_path_publishable(None, "result = {'data': []}") is None


def test_empty_data_table_is_presentable_envelope():
    pres = sr.presentation_from_bootstrap({
        'data': [],
        '__show_table__': True,
    })
    assert pres is not None
    assert pres.get('data') == []


def test_ai_skill_wires_fast_path_publish_check():
    src = skill_source()
    assert 'check_skill_fast_path_publishable' in src


def test_capture_wizard_wires_fast_path_publish_check():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    src = (root / 'common' / 'wizard' / 'skill_capture_wizard.py').read_text(
        encoding='utf-8',
    )
    assert 'check_skill_fast_path_publishable' in src


def test_presentation_from_bootstrap_propose_steps_wins():
    assert sr.presentation_from_bootstrap({
        'formatted_text': '<p>wait</p>',
        'propose_steps': [{'op': 'api_call', 'server': 'x', 'tool': 'y'}],
        'continue': True,
    }) is None


def test_await_empty_args_text_card():
    pres = {
        'formatted_text': '<div>ask</div>',
        '__return_direct__': True,
    }
    assert sr.should_await_skill_args(pres, arguments='') is False
    assert sr.should_await_skill_args(
        pres, arguments='', args_policy='ask',
    ) is True
    assert sr.should_await_skill_args(
        pres, arguments='', args_policy='default',
    ) is False


def test_await_nonempty_args_text_card_without_flag():
    pres = {
        'formatted_text': '<div>err</div>',
        '__return_direct__': True,
    }
    assert sr.should_await_skill_args(pres, arguments='ytd') is False


def test_await_explicit_true_with_args():
    pres = {
        'formatted_text': '<div>unusable args</div>',
        '__await_skill_args__': True,
    }
    assert sr.should_await_skill_args(pres, arguments='blabla') is True


def test_await_explicit_false_overrides_empty_args():
    pres = {
        'formatted_text': '<div>ask</div>',
        '__await_skill_args__': False,
    }
    assert sr.should_await_skill_args(pres, arguments='') is False


def test_await_help_never():
    pres = {
        'formatted_text': '<div>help</div>',
        '__await_skill_args__': True,
    }
    assert sr.should_await_skill_args(pres, arguments='?', is_help=True) is False


def test_await_tabular_payload_not():
    pres = {
        'formatted_text': '<div>x</div>',
        'data': [{'a': 1}],
    }
    assert sr.should_await_skill_args(pres, arguments='') is False
    pres_tables = {
        'tables': [{'title': 'A', 'data': [{'x': 1}]}],
        'formatted_text': '<div>x</div>',
    }
    assert sr.should_await_skill_args(pres_tables, arguments='') is False


def test_await_skill_without_declared_params_never_sticky():
    """Empty-state card of a no-args skill must not swallow the next message."""
    pres = {
        'formatted_text': '<p>Requires Accounting</p>',
        '__return_direct__': True,
    }
    assert sr.should_await_skill_args(
        pres, arguments='', accepts_args=False,
    ) is False


def test_await_explicit_flag_wins_over_undeclared_params():
    pres = {
        'formatted_text': '<div>ask</div>',
        '__await_skill_args__': True,
    }
    assert sr.should_await_skill_args(
        pres, arguments='', accepts_args=False,
    ) is True


def test_await_no_formatted_text():
    assert sr.should_await_skill_args({}, arguments='') is False
    assert sr.should_await_skill_args(None, arguments='') is False


def test_skill_state_from_params_reads_session_json():
    raw = '{"awaiting_args": true, "state": {"periodo": "ytd", "step": 2}}'
    assert sr.skill_state_from_params(raw) == {'periodo': 'ytd', 'step': 2}


def test_skill_state_from_params_accepts_dict():
    raw = {'awaiting_args': True, 'state': {'a': 1}}
    assert sr.skill_state_from_params(raw) == {'a': 1}


def test_skill_state_from_params_survives_garbage():
    for raw in (None, '', 'not json', '[]', '{"state": "nope"}', {}, 42):
        assert sr.skill_state_from_params(raw) == {}


def test_skill_state_for_await_first_non_empty():
    pres = {'__skill_state__': {}}
    bootstrap = {'__skill_state__': {'step': 1}}
    assert sr.skill_state_for_await(pres, bootstrap) == {'step': 1}
    assert sr.skill_state_for_await(None, 'x', {}) == {}


def test_await_state_keeps_skill_alive_on_later_rounds():
    """Round 2+: args are no longer empty, state is what keeps it going."""
    pres = {
        'formatted_text': '<div>and the second question?</div>',
        '__skill_state__': {'periodo': 'ytd'},
    }
    assert sr.should_await_skill_args(
        pres, arguments='ytd', accepts_args=True,
    ) is True


def test_collect_external_sources_hosts_and_api():
    steps = [
        {'op': 'fetch_url', 'url': 'https://api.open-meteo.com/v1/forecast'},
        {'op': 'fetch_url', 'url': 'https://nominatim.openstreetmap.org/search'},
        {'op': 'api_call', 'server': 'ext-api', 'tool': 'status'},
        {'op': 'fetch_url', 'url': 'https://example.com/x', 'success': False},
        {'op': 'write', 'model': 'res.partner'},
    ]
    src = sr.collect_external_sources(steps)
    assert src == [
        'API: ext-api/status',
        'api.open-meteo.com',
        'nominatim.openstreetmap.org',
    ]


def test_await_state_ends_when_skill_drops_it():
    pres = {
        'tables': [{'title': 'Result', 'data': [{'x': 1}]}],
        'formatted_text': '<div>done</div>',
    }
    assert sr.should_await_skill_args(
        pres, arguments='ytd', accepts_args=True,
    ) is False
