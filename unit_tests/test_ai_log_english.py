# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""ai.log writes English summaries; colliding labels stay unique (EN-only)."""
from __future__ import annotations

from pathlib import Path
from _load_addon import engine_source, relaxaicode_source, safe_plan_source

_ROOT = Path(__file__).resolve().parents[1]
_COMMON = _ROOT / 'common'


def _read(*parts):
    return (_ROOT.joinpath(*parts)).read_text(encoding='utf-8')


def test_log_summaries_are_english_literals():
    engine = engine_source()
    exec_eng = _read('common', 'models', 'ai_execution_engine.py')
    main = _read('common', 'controllers', 'main.py')
    relax = relaxaicode_source()
    log = _read('common', 'models', 'ai_log.py')

    assert 'llm_tool_request' not in engine
    assert 'llm_tool_request' not in log
    assert "result_summary='Turn completed · %s LLM round(s)' % round_n" in engine
    assert "result_summary=_('Turn completed" not in engine

    assert "'Round %s · %s messages · %s tools'" in exec_eng
    assert "_('Round %(t)s" not in exec_eng
    assert "(empty)" in exec_eng
    assert "(sin contenido)" not in exec_eng
    assert "'ORCH failover: %s failed" in exec_eng
    assert "_('ORCH failover:" not in exec_eng

    assert "Context fetched:" in main
    assert "Prompt not found:" in main
    assert "Contexto obtenido:" not in main
    assert "Prompt no encontrado:" not in main

    assert "Permission error: not in group_ai_writer for relaxaicode" in relax
    assert "Error de permisos:" not in relax

    assert "rec.flow_label = 'Turn completed'" in log
    assert 'agent_display' not in log
    assert 'origin_display' not in log
    assert 'agent_id' not in log
    assert 'agent_code' not in log
    assert "('secretary'" not in log
    assert 'resolve_log_agent' not in log


def test_log_origin_column_is_the_agent_name():
    engine = engine_source()
    exec_eng = _read('common', 'models', 'ai_execution_engine.py')
    logging_src = _read('common', 'utils', 'mcp_logging.py')
    safe = safe_plan_source()
    assert 'mcp_agent_code' in engine
    assert "setdefault('agent_code', self._agent_code)" in engine
    assert 'mcp_source_channel' in engine
    assert 'def _http_request' in engine
    assert 'def _bind_log_identity' in exec_eng
    assert 'def resolve_log_agent' not in logging_src
    assert 'def agent_log_label' not in logging_src
    assert 'def request_log_stamp' in logging_src
    fn = safe.split('def capture_safe_plan_log_context')[1].split('def request_safe_plan')[0]
    assert "if origin == 'internal' and turn_corr" not in fn
    assert "if not stamped and getattr(http_request, 'mcp_user_id', None)" in fn
    assert 'if stamped in doors:' in fn
    assert 'chatboo' not in fn
    exec_eng = _read('common', 'models', 'ai_execution_engine.py')
    bind = exec_eng.split('def _bind_log_identity')[1].split('def _get_agent')[0]
    assert 'request_log_stamp' in bind
    for stack in ('owl1', 'owl2'):
        views = _read('stacks', stack, 'pns_ai_mcp', 'views', 'ai_log_views.xml')
        assert 'agent_display' not in views
        assert 'origin_display' not in views
        assert 'string="Origin"' not in views
        assert 'string="Door"' not in views
        assert 'agent_id' not in views
        assert "group_by': 'origin'" not in views
        assert "group_by': 'client_display'" in views
        assert "name=\"src_mcp\" domain=\"[('origin', '=', 'mcp_client')]\"" in views
    log = _read('common', 'models', 'ai_log.py')
    assert 'Which door the request used' in log
    assert 'If no agent was bound, shows the door label' not in log
    assert 'Empty if no agent was bound.' not in log
    assert 'If the host sends no name, this copies the agent' not in log
    assert 'Empty if it said nothing.' in log


def test_the_log_shows_one_who_field():
    """Client is the only "who" on screen; the door stays behind it, unshown."""
    log = _read('common', 'models', 'ai_log.py')
    client = log.split('def _compute_client_display')[1].split('def ')[0]
    assert 'rec.client_label' in client
    assert "_fields['origin'].selection" in client
    field = log.split('client_display = fields.Char(')[1].split(')')[0]
    assert 'store=True' in field
    for stack in ('owl1', 'owl2'):
        views = _read('stacks', stack, 'pns_ai_mcp', 'views', 'ai_log_views.xml')
        trees = views.split('id="action_ai_log"', 1)[0]
        assert 'name="client_label" string="Client" readonly="1"' not in trees
        assert trees.count('name="client_display" string="Client"') == 2
        assert 'name="agent_id"' not in trees
        assert 'string="Door"' not in trees
        full = views.split('id="view_ai_log_tree"', 1)[1].split('id="action_ai_log"', 1)[0]
        assert 'name="origin" invisible="1"' in full
        form = views.split('id="view_ai_log_form"', 1)[1].split('id="view_ai_log_search"', 1)[0]
        assert 'name="client_display"' in form
        assert 'name="origin"' not in form
        search = views.split('id="view_ai_log_search"', 1)[1]
        assert 'name="client_display" string="Client"' in search
        assert 'name="origin" string=' not in search


def test_short_log_columns_take_their_width_from_the_arch():
    """Short columns are sized in the tree, in the list's own font."""
    for stack in ('owl1', 'owl2'):
        views = _read('stacks', stack, 'pns_ai_mcp', 'views', 'ai_log_views.xml')
        trees = views.split('id="action_ai_log"', 1)[0]
        assert trees.count('class="o_mcp_flow_icon_cell" width="16px"') == 2
        assert trees.count('name="turn" string="Turn" readonly="1" optional="show" width="52px"') == 2
        assert trees.count('name="turn_step" string="Step" readonly="1" optional="show" width="36px"') == 2
        assert trees.count('name="remote_ip" string="IP" readonly="1" optional="show" width="96px"') == 2
        assert 'name="cost_display" string="Cost" readonly="1" optional="show" width="60px"' in trees
        for name in ('request_size_bytes', 'response_size_bytes'):
            assert f'name="{name}" readonly="1" optional="show" width="56px"' in trees
        css = _read('stacks', stack, 'pns_ai_mcp', 'static', 'src', 'css', 'mcp_log_tree.css')
        assert 'size_bytes' not in css
        assert 'data-name="turn' not in css
        assert 'data-field="turn' not in css
        icon = css.split('td[data-field="flow_icon_html"] {', 1)[1].split('}', 1)[0]
        assert 'width' not in icon
    js = _read('stacks', 'owl1', 'pns_ai_mcp', 'static', 'src', 'js', 'mcp_log_tree_v14.js')
    freeze = js.split('_freezeColumnWidths: function', 1)[1].split('\n        },', 1)[0]
    assert "'o_mcp_log_tree'" in freeze
    assert 'column.attrs.width' in freeze
    assert "require('web.EditableListRenderer')" in js
    assert '_renderBodyCell' not in js


def test_log_summaries_are_english_literals_flow():
    log = _read('common', 'models', 'ai_log.py')
    assert "rec.flow_label = 'Turn completed'" in log
    assert "rec.flow_label = _('Turn completed')" not in log
    assert "rec.flow_label = 'LLM -> AI Engine (response)'" in log


def test_log_labels_are_unique_english():
    model = _read('common', 'models', 'ai_log.py')
    assert "string='Log user'" in model
    assert "string='LLM model'" in model
    assert "string='Turn'" in model
    assert "string='Step'" in model
    assert "('write', 'Supervised')" in model
    assert "'Safe Plan'" not in model

    for stack in ('owl1', 'owl2'):
        views = _read('stacks', stack, 'pns_ai_mcp', 'views', 'ai_log_views.xml')
        assert 'string="Log user"' in views
        assert 'string="LLM model"' in views
        assert 'string="Turn"' in views
        assert 'string="Step"' in views
        assert 'string="Supervised"' in views
        assert 'string="Write Only"' not in views
        assert 'name="cost_display"' in views
        assert 'string="Cost (USD)"' in views
        tree = views.split('id="view_ai_log_tree"', 1)[1].split('id="action_ai_log"', 1)[0]
        assert tree.find('name="cost_display"') < tree.find('name="cost_usd"')
        assert 'name="user_prompt" string="User Prompt" readonly="1" optional="show"' in tree
        assert tree.find('name="user_prompt"') < tree.find('name="prompt_data_compressed"')
        form = views.split('id="view_ai_log_form"', 1)[1]
        assert 'name="cost_display"' in form.split('id="view_ai_log_search"', 1)[0]

    owl1_js = _read(
        'stacks', 'owl1', 'pns_ai_mcp', 'static', 'src', 'js',
        'mcp_log_tree_v14.js',
    )
    assert "core._t(\"Tools\")" not in owl1_js
    assert "> Tools" in owl1_js or "Tools" in owl1_js

    owl2_js = _read(
        'stacks', 'owl2', 'pns_ai_mcp', 'static', 'src', 'js',
        'mcp_log_action_buttons.js',
    )
    assert '_t("Tools")' not in owl2_js
    assert 'return "Tools"' in owl2_js


def test_po_keeps_log_result_in_english():
    for rel in (
        ('stacks', 'owl1', 'pns_ai_mcp', 'i18n', 'es.po'),
        ('stacks', 'owl2', 'pns_ai_mcp', 'i18n', 'es_ES.po'),
    ):
        po = _read(*rel)
        assert 'msgid "LLM requested tool: %(t)s"' not in po
        assert 'msgid "Turn completed · %(n)s LLM round(s)"' not in po
        assert 'msgid "Round %(t)s · %(m)s messages · %(k)s tools"' not in po
        assert 'msgstr "Resultado"\n\n#. module: pns_ai_mcp\n#: model:ir.model.fields,field_description:pns_ai_mcp.field_ai_log__result_data' not in po
        # The Result entry used by ai.log must stay English.
        assert (
            'field_ai_log__result_data\n'
            '#: model_terms:ir.ui.view,arch_db:pns_ai_mcp.view_ai_log_form\n'
            '#: model_terms:ir.ui.view,arch_db:pns_ai_mcp.view_ai_log_tree\n'
            'msgid "Result"\n'
            'msgstr "Result"'
        ) in po
        assert (
            'field_ai_log__cost_display\n'
            '#: model:ir.model.fields,field_description:pns_ai_mcp.field_ai_provider_usage_day__cost\n'
            '#: model_terms:ir.ui.view,arch_db:pns_ai_mcp.view_ai_log_form\n'
            '#: model_terms:ir.ui.view,arch_db:pns_ai_mcp.view_ai_log_tree\n'
            'msgid "Cost"\n'
            'msgstr "Cost"'
        ) in po


_EXEMPT_PO_MARKERS = (
    'view_mcp_log', 'action_mcp_log', 'log_delete_menu', 'log_tools_wizard',
    'ai_log', 'export_logs', 'clear_history',
)


def test_po_keeps_exempt_ai_log_ui_in_english():
    import re
    for rel in (
        ('stacks', 'owl1', 'pns_ai_mcp', 'i18n', 'es.po'),
        ('stacks', 'owl2', 'pns_ai_mcp', 'i18n', 'es_ES.po'),
    ):
        po = _read(*rel)
        blocks = re.split(r'\n\n(?=#\. module)', po)
        for block in blocks:
            if not any(m in block for m in _EXEMPT_PO_MARKERS):
                continue
            m_id = re.search(r'^msgid "(.*)"\n', block, re.M)
            m_st = re.search(r'^msgstr "(.*)"\n', block, re.M)
            if not m_id or not m_st:
                continue
            mid, mst = m_id.group(1), m_st.group(1)
            if mid and mst != mid:
                raise AssertionError(
                    'exempt ai.log PO entry must stay English: %r -> %r in %s'
                    % (mid, mst, rel[-1])
                )
