# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""A skill's result stays in the session for the next turn, like any query.

A skill resolved outside the tool loop (fast-path HTML, report handoff)
emitted neither ``query_code`` nor ``query_data``; the host dropped its
dataset cache and "now for 2025" after a skill found an empty
``previous_result``.
"""
from __future__ import annotations

import json

from _load_addon import engine_source, load_module

gate = load_module('record_delivery_gate', 'utils', 'record_delivery_gate.py')

_TABLES = {
    'tables': [
        {'title': 'ABC', 'data': [{'id': 1, 'Ingresos': 10, 'Resultado': 7}]},
        {'title': 'INC', 'data': [{'id': 2, 'Ingresos': 20, 'Resultado': 5}]},
    ],
    '__show_table__': True,
}


def test_fast_path_result_publishes_code_and_rows():
    events = list(gate.skill_result_events("result = {'tables': []}", _TABLES))
    assert [e['event'] for e in events] == ['query_code', 'query_data']
    assert events[0]['code'] == "result = {'tables': []}"
    rows = events[1]['data']
    assert [r['id'] for r in rows] == [1, 2]
    assert rows[0]['__table__'] == 'ABC' and rows[1]['__table__'] == 'INC'


def test_a_card_without_rows_leaves_only_the_code():
    events = list(gate.skill_result_events(
        'result = {}', {'formatted_text': '<div>help</div>', '__return_direct__': True},
    ))
    assert [e['event'] for e in events] == ['query_code']
    assert list(gate.skill_result_events('', {'formatted_text': 'x'})) == []


def test_the_byte_cap_of_the_tool_loop_applies():
    assert [e['event'] for e in gate.skill_result_events('code', _TABLES, 10)] == ['query_code']
    wide = len(json.dumps(_TABLES)) * 4
    assert [e['event'] for e in gate.skill_result_events('code', _TABLES, wide)] == [
        'query_code', 'query_data',
    ]


def test_both_skill_branches_emit_before_done_or_the_loop():
    src = engine_source()
    assert 'self._dataset_cache_max_bytes(),' in src.split('def _skill_result_events', 1)[1].split('\n    def ', 1)[0]
    fast = src.split("tool_name='skill_fast_path',", 1)[1].split('return True, None', 1)[0]
    assert 'self._skill_result_events(' in fast
    assert fast.index('self._skill_result_events(') < fast.index('self._done_event(')
    handoff = src.split("tool_name='skill_report_handoff',", 2)[2].split(
        '# Fall through to the LLM provider loop.', 1,
    )[0]
    assert 'self._skill_result_events(' in handoff
