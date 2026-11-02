# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""LLM history stubs: on-screen tables are not replayed to the model."""
from __future__ import annotations

import html
import json

from _load_addon import engine_source, load_module

hc = load_module('pns_ai_mcp_history_compact', 'utils', 'history_compact.py')


def _table_html(rows, title='Results'):
    payload = html.escape(json.dumps(rows, ensure_ascii=False), quote=True)
    return (
        '<h2>%s</h2>'
        '<div class="o_ai_table_block" data-ai-dataset="%s">'
        '<div class="table-responsive"><table><tr><td>x</td></tr></table></div>'
        '</div>'
    ) % (title, payload)


def test_table_html_becomes_stub_with_shape_not_cells():
    rows = [
        {'Year': 2026, 'Name': 'Task A', '__model': 'project.task'},
        {'Year': 2026, 'Name': 'Task B', '__model': 'project.task'},
        {'Year': 2025, 'Name': 'Task C', '__model': 'project.task'},
    ]
    html_doc = _table_html(rows, title='Preventivo vs instalacion')
    out = hc.compact_assistant_content(html_doc)
    assert out.startswith(hc.STUB_PREFIX)
    assert '3 rows' in out
    assert 'Year' in out
    assert 'Name' in out
    assert '__model' not in out
    assert 'Task A' not in out
    assert 'Preventivo vs instalacion' in out
    assert 'previous_result' in out


def test_stripped_cell_dump_is_stubbed():
    dump = 'Name Result\n' + ('Preventivo fila x 12345\n' * 400)
    assert len(dump) > hc.FAT_CHARS
    out = hc.compact_assistant_content(dump)
    assert out.startswith(hc.STUB_PREFIX)
    assert 'Preventivo fila' not in out
    assert str(len(dump)) in out or 'characters' in out


def test_short_prose_is_kept():
    text = 'The three rows are from 2026, not from a code in the name.'
    assert hc.compact_assistant_content(text) == text


def test_already_stub_is_idempotent():
    stub = hc.format_stub({'kind': 'table', 'rows': 4, 'columns': ['A']})
    assert hc.compact_assistant_content(stub) == stub
    hist = [
        {'role': 'user', 'content': 'again'},
        {'role': 'assistant', 'content': stub},
    ]
    assert hc.compact_history_for_llm(hist)[1]['content'] == stub


def test_compact_history_drops_tools_and_starts_at_user():
    hist = [
        {'role': 'system', 'content': 'ignore'},
        {'role': 'assistant', 'content': 'orphan'},
        {'role': 'user', 'content': 'list rows'},
        {'role': 'assistant', 'tool_calls': [{'id': '1'}], 'content': ''},
        {'role': 'tool', 'content': '{"data":[{"a":1}]}'},
        {'role': 'assistant', 'content': _table_html([{'a': 1, 'b': 2}])},
    ]
    out = hc.compact_history_for_llm(hist)
    assert [m['role'] for m in out] == ['user', 'assistant']
    assert out[0]['content'] == 'list rows'
    assert out[1]['content'].startswith(hc.STUB_PREFIX)
    assert '{"data"' not in json.dumps(out)


def test_payload_rows_drive_stub_even_if_visible_is_short():
    payload = {
        'title': 'Split',
        'data': [
            {'Op': 'A', 'Result': 1},
            {'Op': 'B', 'Result': 2},
        ],
    }
    out = hc.compact_assistant_content('Here you go.', payload=payload)
    assert out.startswith(hc.STUB_PREFIX)
    assert '2 rows' in out
    assert 'Op' in out
    assert 'title=Split' in out


def test_map_payload_is_stubbed():
    out = hc.compact_assistant_content(
        'map html',
        payload={'map_url': 'https://example.invalid/m', 'map_pins': [{}, {}, {}]},
    )
    assert 'kind=map' in out
    assert '3 pins' in out


def test_markdown_table_is_stubbed():
    md = (
        '| Year | Name |\n'
        '| --- | --- |\n'
        '| 2026 | Alpha |\n'
        '| 2026 | Beta |\n'
    )
    out = hc.compact_assistant_content(md)
    assert out.startswith(hc.STUB_PREFIX)
    assert '2 rows' in out
    assert 'Year' in out
    assert 'Alpha' not in out


def test_turn_shown_text_keeps_report_and_coda():
    report = '# Financial health\n\nSales 1.6 M.'
    coda = 'The report is already complete.'
    messages = [
        {'role': 'user', 'content': 'old'},
        {'role': 'assistant', 'content': '[On-screen artifact | kind=table]'},
        {'role': 'user', 'content': 'estado financiero'},
        {'role': 'assistant', 'content': report},
        {'role': 'tool', 'content': 'noise'},
        {'role': 'assistant', 'content': coda, 'tool_calls': [{'id': '1'}]},
        {'role': 'assistant', 'content': coda},
    ]
    shown = hc.turn_shown_text(messages, 3)
    assert report in shown
    assert coda in shown
    assert 'On-screen artifact' not in shown
    assert 'old' not in shown


def test_append_turn_stub_keeps_user_and_stubs_assistant():
    prior = [{'role': 'user', 'content': 'hi'}, {'role': 'assistant', 'content': 'ok'}]
    out = hc.append_turn_stub(
        prior, 'show the grid',
        visible=_table_html([{'x': 1}] * 5, title='Grid'),
    )
    assert out[-2] == {'role': 'user', 'content': 'show the grid'}
    assert out[-1]['content'].startswith(hc.STUB_PREFIX)
    assert '5 rows' in out[-1]['content']


def test_multimodal_user_keeps_text_drops_images():
    hist = [{
        'role': 'user',
        'content': [
            {'type': 'text', 'text': 'what is this?'},
            {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,AAA'}},
        ],
    }, {
        'role': 'assistant',
        'content': 'A small photo.',
    }]
    out = hc.compact_history_for_llm(hist)
    assert out[0]['content'] == 'what is this?'
    assert 'data:image' not in out[0]['content']
    assert out[1]['content'] == 'A small photo.'


def test_assistant_html_image_keeps_src_in_stub():
    html = (
        '<p>The Chatboo module uses this icon:</p>'
        '<img src="/pns_ai_chatboo/static/description/icon.png" alt="Chatboo"/>'
    )
    out = hc.compact_assistant_content(html)
    assert out.startswith(hc.STUB_PREFIX)
    assert 'kind=image' in out
    assert '/pns_ai_chatboo/static/description/icon.png' in out
    assert 'data:image' not in out
    assert 'genuinely new query' in out
    assert 'system://info' not in html


def test_strip_html_preserves_image_ref_without_data_url():
    html = (
        'Look: <img src="data:image/png;base64,AAA" alt="elephant">'
        ' done'
    )
    kept = hc._strip_html(html)
    assert 'elephant' in kept
    assert 'inline-image' in kept
    assert 'data:image' not in kept
    assert 'AAA' not in kept


def test_stream_done_does_not_store_the_model_dict_as_the_user():
    engine = engine_source()
    assert not any(
        line.strip().startswith("message = piece.get('message')")
        for line in engine.splitlines()
    )
    assert "llm_message = piece.get('message')" in engine
    assert 'kept_history, _utterance' in engine
    assert "get('user_message')" in engine


def test_history_char_count_shrinks_on_fat_table():
    rows = [{'col': 'x' * 80, 'n': i} for i in range(200)]
    hist = [
        {'role': 'user', 'content': 'table please'},
        {'role': 'assistant', 'content': _table_html(rows)},
    ]
    before = hc.history_char_count(hist)
    after = hc.history_char_count(hc.compact_history_for_llm(hist))
    assert before > 5000
    assert after < 800
    assert after < before / 5
