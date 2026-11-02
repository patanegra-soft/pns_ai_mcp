# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""On MCP: author flags and HTML must be read from the inner payload."""
from __future__ import annotations

import json

from _load_addon import engine_source, load_module

payload = load_module('mcp_tool_payload', 'utils', 'mcp_tool_payload.py')


def test_unwrap_tool_payload_reads_inner_flags():
    inner = {
        'formatted_text': '<div>ok</div>',
        '__fmt_type__': 'author_html',
        '__return_direct__': True,
    }
    outer = {'content': [{'type': 'text', 'text': json.dumps(inner)}]}
    got = payload.unwrap_tool_payload(outer)
    assert got['__fmt_type__'] == 'author_html'
    assert got['formatted_text'].startswith('<div>')


def test_summarize_propose_failed_shows_error_not_empty_brackets():
    """N8L6-style: schema reject must not log as 'safe plan []'."""
    inner = {
        'success': False,
        'error': "Missing required property 'action' at arguments.body.data "
                 "(tool inputSchema).",
    }
    envelope = json.dumps({
        'content': [{'type': 'text', 'text': json.dumps(inner)}],
    })
    summary = payload.summarize_safe_plan_request(envelope)
    assert 'Propose failed:' in summary
    assert 'action' in summary
    assert 'safe plan []' not in summary


def test_summarize_propose_ok_keeps_verification_id():
    inner = {
        'success': True,
        'title': 'safe plan',
        'verification_id': 'APIC00000404',
        'status': 'confirmed',
    }
    summary = payload.summarize_safe_plan_request(json.dumps(inner))
    assert 'APIC00000404' in summary
    assert 'confirmed' in summary
    assert summary.startswith('Proposed:')


def test_unwrap_plain_dict_passthrough():
    d = {'data': [{'a': 1}], '__fmt_type__': 'server_side_python'}
    assert payload.unwrap_tool_payload(d) is d


def test_is_author_html_for_skills():
    assert payload.is_author_html_payload({
        'formatted_text': '<div/>',
        '__fmt_type__': 'author_html',
    })
    assert payload.is_author_html_payload({
        'formatted_text': '<div/>',
    })
    assert not payload.is_author_html_payload({
        'formatted_text': '<table/>',
        '__fmt_type__': 'server_side_python',
    })
    assert not payload.is_author_html_payload({'data': []})


def test_resolve_author_footer_suppress_and_override():
    # __no_footer__ → omit
    assert payload.resolve_author_footer({'__no_footer__': True}) == (True, None)
    assert payload.resolve_author_footer({'__skip_footer__': True}) == (True, None)
    # explicit footer='' → omit
    assert payload.resolve_author_footer({'footer': '   '}) == (True, None)
    # footer with text → author footer (takes priority)
    assert payload.resolve_author_footer(
        {'footer': 'Comparativa: A > B'}
    ) == (False, 'Comparativa: A > B')
    assert payload.resolve_author_footer(
        {'__footer__': 'Hecho.'}
    ) == (False, 'Hecho.')
    # no preference → generic footer
    assert payload.resolve_author_footer({'formatted_text': '<div/>'}) == (False, None)
    assert payload.resolve_author_footer(None) == (False, None)


def test_default_warm_footer_has_no_period_wording():
    html = payload.append_local_warm_footer('<div>x</div>')
    assert 'period' not in html.lower()


def test_append_local_warm_footer_has_no_year():
    html = payload.append_local_warm_footer('<div>chart</div>', 'Aquí lo tienes.')
    assert 'chart' in html
    assert 'o_ai_local_footer' in html
    assert 'Aquí lo tienes.' in html
    assert '2025' not in html and '2026' not in html
    # Idempotent
    html2 = payload.append_local_warm_footer(html, 'otro')
    assert html2.count('o_ai_local_footer') == 1


def test_strip_server_html_for_remote_keeps_html_marks_unshown():
    inner = {
        'data': [{'Empleado': 'Ana', 'Horas': '8h'}],
        'summary': '1 persona',
        'formatted_text': '<table><tr><td>Ana</td></tr></table>',
        '__fmt_type__': 'server_side_python',
        '__return_direct__': True,
    }
    outer = {'content': [{'type': 'text', 'text': json.dumps(inner)}]}
    cleaned = payload.strip_server_html_for_remote(outer)
    text = cleaned['content'][0]['text']
    got = json.loads(text)
    assert got['data'][0]['Empleado'] == 'Ana'
    assert got['formatted_text'].startswith('<table>')
    assert '__return_direct__' not in got
    assert got['remote_format'] is True
    assert got['data_rendered'] is False
    assert 'NOT shown' in got['note']


def test_strip_server_html_leaves_author_html():
    inner = {
        'formatted_text': '<div>skill</div>',
        '__fmt_type__': 'author_html',
    }
    assert payload.strip_server_html_for_remote(inner) is inner


def test_strip_server_html_keeps_tabular_author_html():
    inner = {
        'formatted_text': '<div class="o_ai_table_block"/>',
        '__fmt_type__': 'author_html',
        'data': [{'a': 1}],
    }
    cleaned = payload.strip_server_html_for_remote(inner)
    assert cleaned is not inner
    assert cleaned['formatted_text'].startswith('<div')
    assert cleaned['remote_format'] is True
    assert cleaned['data'] == [{'a': 1}]


def test_remote_format_handoff_payload_requires_rows():
    handoff = payload.remote_format_handoff_payload({
        'data': [{'a': 1}],
        'summary': 'ok',
        'formatted_text': '<table/>',
        '__fmt_type__': 'server_side_python',
    })
    assert handoff['remote_format'] is True
    assert handoff['data_rendered'] is False
    assert handoff['data'] == [{'a': 1}]
    assert handoff['formatted_text'] == '<table/>'
    assert 'Charts are allowed' in handoff['note']
    # Tabular author_html (skill presentation stamp) is owned in report mode
    author_handoff = payload.remote_format_handoff_payload({
        'formatted_text': '<div/>',
        '__fmt_type__': 'author_html',
        'data': [{'a': 1}],
    })
    assert author_handoff is not None
    assert author_handoff['data'] == [{'a': 1}]
    assert payload.remote_format_handoff_payload({'summary': 'solo texto'}) is None
    # Narrative contract keys travel with the handoff (report skeleton).
    outlined = payload.remote_format_handoff_payload({
        'tables': [{'title': 't', 'data': [{'a': 1}]}],
        'report_outline': ['## A', '## B'],
        'closing_required': 'Línea recomendada de actuación: …',
    })
    assert outlined['report_outline'] == ['## A', '## B']
    assert outlined['closing_required'].startswith('Línea recomendada')


def test_remote_owns_tabular_presentation_flag_isolation():
    server = {
        'data': [{'x': 1}],
        'formatted_text': '<table class="o_ai_data_table"/>',
        '__fmt_type__': 'server_side_python',
    }
    author_tabular = {
        'formatted_text': '<div class="o_ai_table_block" data-ai-dataset="[]">',
        '__fmt_type__': 'author_html',
        'data': [{'x': 1}],
    }
    author_pure = {
        'formatted_text': '<div>skill widget</div>',
        '__fmt_type__': 'author_html',
    }
    # OFF → never remote (local path must stay identical)
    assert payload.remote_owns_tabular_presentation(False, server) is False
    assert payload.remote_owns_tabular_presentation(False, author_tabular) is False
    assert payload.remote_owns_tabular_presentation(False, None) is False
    # ON → all tabular (incl. presentations stamped author_html); pure HTML local
    assert payload.remote_owns_tabular_presentation(True, server) is True
    assert payload.remote_owns_tabular_presentation(True, author_tabular) is True
    assert payload.remote_owns_tabular_presentation(True, author_pure) is False
    assert payload.remote_owns_tabular_presentation(True, {'data': [{'a': 1}]}) is True


def test_remote_format_handoff_includes_author_html_tables():
    author_tabular = {
        'formatted_text': '<table/>',
        '__fmt_type__': 'author_html',
        'data': [{'Indicador': 'MRR', 'Valor': 1}],
        'title': 'KPIs',
    }
    handoff = payload.remote_format_handoff_payload(author_tabular)
    assert handoff is not None
    assert handoff['remote_format'] is True
    assert handoff['data_rendered'] is False
    assert handoff['data'][0]['Indicador'] == 'MRR'
    assert handoff['formatted_text'] == '<table/>'
    assert payload.remote_format_handoff_payload({
        'formatted_text': '<div/>',
        '__fmt_type__': 'author_html',
    }) is None


def _fat_tabular_inner():
    return {
        'data': [
            {'Empleado': 'Ana-CELL-UNIQUE', 'id': i} for i in range(80)
        ],
        'formatted_text': '<table><tr><td>Ana-CELL-UNIQUE</td></tr></table>',
        '__fmt_type__': 'server_side_python',
        '__return_direct__': True,
        'summary': 'Staff',
    }


def test_tool_result_json_for_llm_local_stubs_cells():
    inner = _fat_tabular_inner()
    outer = {'content': [{'type': 'text', 'text': json.dumps(inner)}]}
    off_json = payload.tool_result_json_for_llm(outer, False)
    off = json.loads(off_json)
    stub = json.loads(off['content'][0]['text'])
    assert 'Ana-CELL-UNIQUE' not in off_json
    assert stub['rows'] == 80
    assert 'Empleado' in stub['columns']
    assert stub['previous_result'] is True
    assert stub['on_screen'] is True
    assert stub['data_rendered'] is True
    assert 'already shown' in stub['note']
    assert payload.local_owns_tabular_paint(False, inner) is True
    # Chat path: same payload still has the HTML (stub is only for the LLM).
    assert 'Ana-CELL-UNIQUE' in inner['formatted_text']


def test_local_stub_counts_every_table_without_cells():
    inner = {
        'summary': 'Two groups',
        'tables': [
            {'title': 'Above', 'data': [
                {'Cliente': 'Ana-CELL-UNIQUE', 'id': 1},
                {'Cliente': 'Total', '_tfoot': True},
            ]},
            {'title': 'Rest', 'data': [
                {'Cliente': 'B', 'id': 2}, {'Cliente': 'C', 'id': 3},
            ]},
        ],
        '__return_direct__': True,
    }
    stub_json = payload.tool_result_json_for_llm(inner, False)
    assert 'Ana-CELL-UNIQUE' not in stub_json
    stub = json.loads(stub_json)
    assert stub['tables'] == [
        {'title': 'Above', 'rows': 1}, {'title': 'Rest', 'rows': 2},
    ]
    assert stub['rows'] == 3


def test_tool_result_json_for_llm_free_keeps_cells():
    inner = _fat_tabular_inner()
    outer = {'content': [{'type': 'text', 'text': json.dumps(inner)}]}
    on_json = payload.tool_result_json_for_llm(outer, True)
    on_inner = json.loads(json.loads(on_json)['content'][0]['text'])
    assert 'Ana-CELL-UNIQUE' in on_json
    assert on_inner['data'][0]['Empleado'] == 'Ana-CELL-UNIQUE'
    assert 'formatted_text' in on_inner
    assert on_inner['remote_format'] is True
    assert on_inner['data_rendered'] is False
    assert '__return_direct__' not in on_inner
    assert payload.local_owns_tabular_paint(True, inner) is False


def test_tool_result_json_for_llm_local_force_retry_keeps_error():
    inner = {
        '__force_retry__': True,
        'error': 'NameError: boom-UNIQUE',
        'data': [{'Empleado': 'Ana-CELL-UNIQUE'}],
    }
    outer = {
        '__force_retry__': True,
        'content': [{'type': 'text', 'text': json.dumps(inner)}],
    }
    off_json = payload.tool_result_json_for_llm(outer, False)
    assert 'boom-UNIQUE' in off_json
    assert payload.local_owns_tabular_paint(
        False, inner, force_retry=True,
    ) is False


def test_local_owns_a_page_url_without_rows():
    inner = {
        'data': [],
        'page_url': '/chatboo/canvas/39?rev=1',
        'summary': 'Weekly forecast',
    }
    assert payload.local_owns_tabular_paint(False, inner) is True
    assert payload.local_owns_tabular_paint(True, inner) is False


def test_an_inspect_lookup_stays_off_the_bubble():
    """25S0: the area lookup asked inspect_result and still filled the bubble."""
    inner = {'data': [
        {'ref': 'ABC', 'group_id': 23, 'group_name': '[ABC] ABUS Comercial'},
        {'ref': 'ABT', 'group_id': 24, 'group_name': '[ABT] ABUS Instalaciones'},
    ]}
    assert payload.local_owns_tabular_paint(False, inner) is True
    assert payload.local_owns_tabular_paint(
        False, inner, inspect_only=True,
    ) is False
    seen = json.loads(payload.tool_result_json_for_llm(
        inner, False, shown_to_user=False,
    ))
    assert seen['data'][1]['ref'] == 'ABT'
    assert seen['__shown_to_user__'] is False


def test_an_inspect_call_that_changed_the_page_still_shows_it():
    inner = {
        'data': [{'area': 'ABC'}],
        'page_url': '/chatboo/canvas/61?rev=2',
    }
    assert payload.local_owns_tabular_paint(
        False, inner, inspect_only=True,
    ) is True


def test_engine_passes_the_model_choice_to_the_paint():
    src = engine_source()
    assert "tool_args.get('return_mode') == 'inspect_result'" in src
    assert 'inspect_only=_inspect_only' in src
    assert '_inspect_hidden = _inspect_only and not _direct' in src
    assert 'turn.last_tool_unmarked_probe or _inspect_hidden' in src


def test_a_page_laid_out_on_the_copy_reaches_the_wrapper():
    """IB1T: the page was built, the bubble still showed the table."""
    inner = {
        'data': [{'Vehicle': 'KANGOO 0000 BBB'}],
        'formatted_text': '<table><td>KANGOO 0000 BBB</td></table>',
        '__return_direct__': True,
    }
    outer = {'content': [{'type': 'text', 'text': json.dumps(inner)}]}
    copy = payload.unwrap_tool_payload(outer)
    copy['page_url'] = '/chatboo/canvas/48?rev=1'
    copy['formatted_text'] = '<div data-page-card>Open</div>'
    assert 'page_url' not in payload.unwrap_tool_payload(outer)
    assert payload.rewrap_tool_payload(outer, copy) is True
    again = payload.unwrap_tool_payload(outer)
    assert again['page_url'] == '/chatboo/canvas/48?rev=1'
    assert again['formatted_text'].startswith('<div data-page-card')
    plain = {'data': []}
    assert payload.rewrap_tool_payload(plain, plain) is True
    assert payload.rewrap_tool_payload({'x': 1}, {'y': 2}) is False


def test_engine_writes_a_waiting_page_back_into_the_result():

    src = engine_source()
    block = src.split('_had_page = has_page_url(turn._payload)', 1)[1].split('except Exception', 1)[0]
    assert 'fulfill_waiting_page(self.env, turn._payload)' in block
    assert 'rewrap_tool_payload(result, turn._payload)' in block
    assert block.index('fulfill_waiting_page') < block.index('rewrap_tool_payload')


def test_local_tabular_paint_html_stays_off_the_llm():
    from _load_addon import load_module

    render = load_module('relaxaicode_render', 'utils', 'relaxaicode_render.py')
    inner = {'data': [{'Empleado': 'Ana-CELL-UNIQUE'} for _ in range(6)]}
    assert payload.local_owns_tabular_paint(False, inner) is True
    assert render.maybe_attach_formatted_text(inner, summary='Staff', force=True)
    assert 'Ana-CELL-UNIQUE' in inner['formatted_text']
    stub_json = payload.tool_result_json_for_llm(inner, False)
    assert 'Ana-CELL-UNIQUE' not in stub_json


def test_compose_model_overflow_hint_honest():
    fat_html = '<table class="o_ai_data_table"><td>Ana</td></table>'
    out = payload.append_compose_model_overflow_hint(
        'All providers failed',
        compose='compose-model',
        sent_tabular=True,
    )
    assert '/compose-agent' in out
    assert 'The compose mode did not change' in out
    assert 'formatted_text' not in out
    assert fat_html not in out
    assert payload.append_compose_model_overflow_hint(
        'x', compose='compose-agent', sent_tabular=True,
    ) == 'x'
    assert payload.append_compose_model_overflow_hint(
        'x', compose='compose-model', sent_tabular=False,
    ) == 'x'


def test_engine_local_stub_and_free_fail_are_wired():

    src = engine_source()
    assert 'local_owns_tabular_paint' in src
    assert 'append_compose_model_overflow_hint' in src
    assert '_turn_sent_tabular_to_model' in src
    assert 'not remote_llm_format' in src


def test_remote_format_hint_allows_charts():
    hint = payload.REMOTE_FORMAT_SYSTEM_HINT
    assert 'Markdown' in hint
    assert 'Charts' in hint or 'DATA PLOTS' in hint
    assert 'Markdown only' not in hint
    assert 'press Gráfico' not in hint
    assert 'Charts are allowed' in payload._REMOTE_FORMAT_NOTE
    assert 'compose-model' in hint
    assert 'REMOTE LLM FORMATTING' not in hint
    assert 'DATA PLOTS' in hint
    assert 'data-ai-card' in hint
    assert 'native chart blocks only' not in hint
    assert 'structured rows' in hint
    assert 'kind clock' in hint
    assert 'NEVER invent figures' not in hint
    assert 'kind: "link"' in hint or "kind: 'link'" in hint or 'LINK CARD' in hint


def test_engine_export_gate_uses_original_utterance():

    src = engine_source()
    assert 'NEW REPORT this turn' in src
    assert 'turn_export_utterance' in src
    assert 'SESSION_FILE_REPORT_NOTE' in src
    assert 'requested_named_format(_orig)' in src
    assert 'requested_named_format(message)' not in src
    # Loop-local def → UnboundLocalError after a no-tool report (/financial-health).
    assert src.count('def _payload_for_screen(') == 1
    assert '\n    def _payload_for_screen(self' in src
    loop = src.split('while round_n < MAX_ROUNDS:', 1)[1]
    loop = loop.split('\n    def ', 1)[0]
    assert 'def _payload_for_screen(' not in loop
    after_loop = src.split('while round_n < MAX_ROUNDS:', 1)[1]
    assert '_payload_for_screen(' in after_loop.split('if not turn.export_attached:', 1)[1]
    wrap = src.split('Skill report: append bootstrap tables', 1)[1]
    assert '_markdownish_to_html' in wrap.split('/compose-agent', 1)[0]


def test_turn_wall_does_not_failover():

    src = engine_source()
    assert 'class TurnTimeExceeded' in src
    wall = src.split('LLM_AGENT_WALL_TIMEOUT:', 1)[1].split('round_n += 1', 1)[0]
    assert 'raise TurnTimeExceeded' in wall
    assert 'raise ProviderConnectionError' not in wall
    assert 'turn wall exceeded' in src
    assert 'not failing over' in src
