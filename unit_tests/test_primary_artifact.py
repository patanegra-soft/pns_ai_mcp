# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Primary artifact lock: first complete result is never replaced by a probe."""
from __future__ import annotations

import sys

from _load_addon import load_module

sys.modules.setdefault(
    'relaxaicode_render',
    load_module('relaxaicode_render', 'utils', 'relaxaicode_render.py'),
)
sys.modules.setdefault(
    'turn_presentation_basket',
    load_module('turn_presentation_basket', 'utils', 'turn_presentation_basket.py'),
)
pa = load_module('primary_artifact', 'utils', 'primary_artifact.py')
policy = load_module('direct_return_policy', 'utils', 'direct_return_policy.py')
basket = load_module(
    'turn_presentation_basket', 'utils', 'turn_presentation_basket.py',
)


def _complete(**extra):
    payload = {
        'data': [{'id': 1, 'Nombre': 'A'}],
        'title': 'Documento A',
        'summary': '10 localizadas',
        'map_url': 'https://example/geo/map/abc',
        '__satisfied__': True,
        '__presentation_complete__': True,
        '__phase__': 'presentation',
        'formatted_text': '<div class="o_ai_table_block">mapa</div>',
        '__fmt_type__': 'server_side_python',
        '__return_direct__': True,
    }
    payload.update(extra)
    return payload


def test_hollow_empty_rows_and_empty_map():
    hollow = {
        'data': [],
        'title': 'Documento A',
        'summary': '0 filas',
        'map_url': '',
        'map_pins': {'href': '', 'provider': 'google'},
        '__ready_for_presentation__': True,
        '__extraction_complete__': True,
        '__phase__': 'extraction',
    }
    assert pa.is_hollow(hollow)
    assert not pa.is_complete_artifact(hollow)


def test_page_url_without_rows_is_the_document():
    page = {
        'data': [],
        'summary': 'Weekly forecast',
        'page_url': '/chatboo/canvas/38?rev=2',
    }
    assert not pa.is_hollow(page)
    assert pa.is_complete_artifact(page)
    primary = None
    acc = []
    primary, action = pa.apply(primary, acc, page)
    assert action == pa.PIN
    table = {
        'data': [{'Day': 'Sat'}],
        'title': 'Forecast table',
        'summary': 'Seven days',
        '__phase__': 'presentation',
        '__return_direct__': True,
    }
    after, action = pa.apply(primary, acc, table)
    assert action == pa.MINOR
    assert after['page_url'] == page['page_url']
    assert acc[0].get('page_url') == page['page_url']


def test_upgrade_keeps_the_page_url_the_restyle_forgot():
    primary = None
    acc = []
    page = _complete()
    page['page_url'] = '/chatboo/canvas/7?rev=3'
    primary, _ = pa.apply(primary, acc, page)
    upgrade = _complete()
    upgrade.pop('map_url', None)
    upgrade.pop('page_url', None)
    code = (
        'rows = previous_result.get("data") if previous_result else []\n'
        'result = {"data": rows}\n'
    )
    after, action = pa.apply(primary, acc, upgrade, code)
    assert action == pa.UPGRADE
    assert after.get('page_url') == '/chatboo/canvas/7?rev=3'


def test_hollow_then_complete_pins_complete():
    hollow = {
        'data': [],
        'title': 'Documento A',
        'summary': 'Del mismo día. 0 filas.',
        'map_url': '',
        '__ready_for_presentation__': True,
        '__extraction_complete__': True,
    }
    primary = None
    acc = []
    primary, action = pa.apply(primary, acc, hollow)
    assert action == pa.PROBE
    assert primary is None
    complete = _complete()
    primary, action = pa.apply(primary, acc, complete)
    assert action == pa.PIN
    assert primary['map_url'] == 'https://example/geo/map/abc'
    assert acc
    assert acc[0].get('map_url') == primary['map_url']


def test_koan_shape_dump_does_not_replace_primary():
    """Complete A, then a {found, primco} dump: A stays, dump is a probe."""
    primary = None
    acc = []
    primary, action = pa.apply(primary, acc, _complete())
    assert action == pa.PIN
    dump = {
        'found': [{'id': 6615, 'name': 'X'}],
        'primco': [{'id': 2, 'name': 'Y'}],
        'formatted_text': '<table><tr><td>found</td></tr></table>',
        '__fmt_type__': 'server_side_python',
        '__phase__': 'extraction',
        '__ready_for_presentation__': True,
        '__extraction_complete__': True,
    }
    after, action = pa.apply(primary, acc, dump)
    assert action == pa.PROBE
    assert after is primary
    assert after['map_url'].endswith('/abc')
    assert acc[0].get('map_url', '').endswith('/abc')


def test_upgrade_via_previous_result_keeps_slot():
    primary = None
    acc = []
    primary, _ = pa.apply(primary, acc, _complete())
    upgrade = _complete(
        summary='10 localizadas + chips',
        formatted_text='<div class="o_ai_table_block">mapa+chips</div>',
    )
    code = (
        'def restyle():\n'
        '    """Mejorar el documento ya entregado."""\n'
        '    rows = previous_result.get("data") if previous_result else []\n'
        '    result = {"data": rows}\n'
        'result = restyle()\n'
    )
    after, action = pa.apply(primary, acc, upgrade, code)
    assert action == pa.UPGRADE
    assert after['summary'] == '10 localizadas + chips'
    assert len(acc) == 1
    assert acc[0].get('summary') == '10 localizadas + chips'
    assert acc[0].get('map_url', '').endswith('/abc')


def test_minor_appends_after_primary():
    primary = None
    acc = []
    primary, _ = pa.apply(primary, acc, _complete())
    minor = {
        'data': [{'id': 9, 'Nombre': 'B'}],
        'title': 'Anexo',
        'summary': 'Documento menor',
        '__satisfied__': True,
        '__presentation_complete__': True,
        '__phase__': 'presentation',
        '__return_direct__': True,
        'formatted_text': '<div class="o_ai_table_block">menor</div>',
        '__fmt_type__': 'server_side_python',
    }
    after, action = pa.apply(primary, acc, minor)
    assert action == pa.MINOR
    assert after is primary
    assert len(acc) == 2
    assert acc[0].get('title') == 'Documento A'
    assert acc[1].get('title') == 'Anexo'


def test_rebuild_with_the_same_summary_replaces_the_primary():
    """Two groups, then the same two groups rebuilt: two tables, not four."""
    def _groups(n):
        return {
            'summary': 'Rentabilidad por cliente',
            'tables': [
                {'title': 'Grupo 1 (%d)' % n, 'data': [{'id': 1}]},
                {'title': 'Grupo 2', 'data': [{'id': 2}]},
            ],
            '__return_direct__': True,
        }
    primary = None
    acc = []
    primary, action = pa.apply(primary, acc, _groups(50))
    assert action == pa.PIN
    after, action = pa.apply(primary, acc, _groups(62))
    assert action == pa.UPGRADE
    assert len(acc) == 1
    assert after['tables'][0]['title'] == 'Grupo 1 (62)'


def test_should_hide_last_round_probe_when_primary_pinned():
    payload = {
        'formatted_text': '<table></table>',
        '__fmt_type__': 'server_side_python',
    }
    assert policy.should_show_direct_to_chat(
        payload, round_n=10, max_rounds=10, tool_name='relaxaicode',
    )
    assert not policy.should_show_direct_to_chat(
        payload, round_n=10, max_rounds=10, tool_name='relaxaicode',
        has_primary=True,
    )


def test_should_still_show_complete_when_primary_pinned():
    payload = {
        'formatted_text': '<table></table>',
        '__fmt_type__': 'server_side_python',
        '__presentation_complete__': True,
        '__phase__': 'presentation',
    }
    assert policy.should_show_direct_to_chat(
        payload, round_n=10, max_rounds=10, tool_name='relaxaicode',
        has_primary=True,
    )


def test_presentation_payload_keeps_contract_keys():
    src = _complete()
    out = pa.presentation_payload(src)
    assert out['data'] == src['data']
    assert out['map_url'] == src['map_url']
    assert out['title'] == src['title']
    assert out['summary'] == src['summary']
    assert 'map_pins' not in out or out.get('map_pins') is not None


def test_presentation_payload_keeps_excel_formulas():
    src = _complete()
    src['__excel_formulas__'] = {'c': '={a}-{b}'}
    out = pa.presentation_payload(src)
    assert out['__excel_formulas__'] == {'c': '={a}-{b}'}


def test_unified_probe_does_not_wipe_basket_when_protected():
    acc = []
    basket.append_presentable(acc, _complete())
    unified = {
        'tables': [
            {'title': 'Found', 'data': [{'id': 1}]},
            {'title': 'Other', 'data': [{'id': 2}]},
        ],
        '__return_direct__': True,
        '__phase__': 'presentation',
    }
    assert basket.payload_already_unified(unified)
    basket.append_presentable(acc, unified, allow_unified_replace=False)
    assert acc[0].get('title') == 'Documento A'
    assert len(acc) >= 2
