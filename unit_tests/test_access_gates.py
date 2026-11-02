# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Doors that RPC or the engine could walk around (provider pick, write
env, supervised rows, maintenance methods, MCP without a user)."""
from __future__ import annotations

from pathlib import Path
from _load_addon import context_source, engine_source, safe_plan_source

_ROOT = Path(__file__).resolve().parents[1]
_COMMON = _ROOT / 'common'


def _src(*parts):
    return (_COMMON.joinpath(*parts)).read_text(encoding='utf-8')


def _block(src, head):
    return src.split(head, 1)[1].split('\n    def ', 1)[0]


def test_ui_provider_pick_only_narrows_the_agent_chain():
    body = _block(
        _src('models', 'ai_execution_engine.py'),
        'def get_providers_for_agent',
    )
    assert "browse(provider_id)" not in body
    assert 'chain.filtered(' in body
    assert body.index('_without_external_after_local') < body.index(
        'if provider_id:',
    )


def test_engine_controller_write_env_needs_ai_writer():
    src = engine_source()
    dummy = src.split('class DummyController', 1)[1].split(
        'def _log_mcp_operation', 1,
    )[0]
    assert 'GROUP_AI_WRITER' in dummy
    assert "operation_type == 'write'" in dummy
    assert 'return True, ""\n' in dummy
    assert 'raise AccessError' in dummy


def test_supervised_operation_takes_no_rpc_write():
    """PAAP I4: The owner cannot confirm their own plan by writing the row over RPC."""
    body = _block(_src('models', 'safe_operation.py'), 'def write(self, vals)')
    assert 'if not self.env.su and vals:' in body
    assert '_STATE_FIELDS' not in _src('models', 'safe_operation.py')


def test_maintenance_methods_are_not_public_rpc():
    ctx = context_source()
    assert 'def record_context_usage(' not in ctx
    assert 'def _record_context_usage(' in ctx


def test_mcp_without_user_never_becomes_superuser():
    main = _src('controllers', 'main.py')
    assert "getattr(request, 'mcp_user_id', SUPERUSER_ID)" not in main


def test_manifests_ask_only_for_imported_libraries():
    for stack in ('owl1', 'owl2'):
        manifest = (
            _ROOT / 'stacks' / stack / 'pns_ai_mcp' / '__manifest__.py'
        ).read_text(encoding='utf-8')
        assert "'httpx'" not in manifest
        assert "'pydantic'" not in manifest


def test_chat_card_routes_resolve_only_own_operations():
    body = _block(
        _src('controllers', 'verification_ui.py'),
        'def _get_owned_verification',
    )
    assert 'group_ai_admin' not in body
    assert 'verification.user_id.id != request.env.user.id' in body


def test_model_sees_only_tools_the_user_may_use():
    """PAAP I6: The model only sees the tools the bound user may use."""
    dec = _src('controllers', 'mcp_decorators.py')
    assert 'def tool_visible_to(' in dec
    assert "'groups': tuple(groups or ())" in dec
    plan = safe_plan_source()
    assert plan.count('groups=_PLAN_GROUPS') == 2
    engine = _block(engine_source(), 'def get_tools_schema')
    assert 'tool_visible_to(tool, user)' in engine
    main = _src('controllers', 'main.py')
    assert 'tool_visible_to(tool_data, mcp_user)' in main


def test_tool_visibility_rule():
    from _load_addon import load_module
    dec = load_module('mcp_decorators', 'controllers', 'mcp_decorators.py')

    class _User:
        def __init__(self, groups):
            self._groups = set(groups)

        def has_group(self, xmlid):
            return xmlid in self._groups

    plan_tool = {'groups': ('g.writer', 'g.url')}
    assert dec.tool_visible_to({'groups': ()}, _User([]))
    assert not dec.tool_visible_to(plan_tool, _User([]))
    assert dec.tool_visible_to(plan_tool, _User(['g.url']))
    # No per-agent tool filter: every agent is offered the same sack.
    assert not hasattr(dec, 'tool_offered_to_agent')


def test_readonly_html_widget_strips_active_content():
    for rel in (
        'owl1/pns_ai_mcp/static/src/js/pns_html_readonly_widget_v14.js',
        'owl2/pns_ai_mcp/static/src/js/pns_html_readonly_widget.js',
    ):
        js = (_ROOT / 'stacks' / rel).read_text(encoding='utf-8')
        assert 'withoutActiveContent(' in js
        assert "createElement('template')" in js or (
            'createElement("template")' in js
        )
        assert '.html(this.value' not in js
        assert 'innerHTML = this.props.record.data' not in js
