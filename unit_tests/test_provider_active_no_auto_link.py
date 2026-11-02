# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Provider archive + no auto-link-all failovers (source contracts)."""
from __future__ import annotations

from pathlib import Path
from _load_addon import engine_source

_ROOT = Path(__file__).resolve().parents[1]
_ENGINE = (_ROOT / 'common' / 'models' / 'ai_execution_engine.py').read_text(
    encoding='utf-8',
)
_PROVIDER = (_ROOT / 'common' / 'models' / 'ai_provider.py').read_text(
    encoding='utf-8',
)
_AGENT = (_ROOT / 'common' / 'models' / 'ai_agent.py').read_text(
    encoding='utf-8',
)


def _providers_for_agent_block() -> str:
    return _ENGINE.split('def get_providers_for_agent', 1)[1].split(
        '\n    def ', 1,
    )[0]


def test_ai_provider_has_active_field():
    assert 'active = fields.Boolean(' in _PROVIDER
    assert 'Prefer Archive over Delete' in _PROVIDER


def test_provider_views_have_archive_filters():
    for rel in (
        'stacks/owl1/pns_ai_mcp/views/ai_provider_views.xml',
        'stacks/owl2/pns_ai_mcp/views/ai_provider_views.xml',
    ):
        xml = (_ROOT / rel).read_text(encoding='utf-8')
        assert 'name="active"' in xml
        assert "domain=\"[('active', '=', True)]\"" in xml
        assert "domain=\"[('active', '=', False)]\"" in xml
        assert "'search_default_active': 1" in xml


def test_get_failovers_skips_archived_providers():
    block = _ENGINE.split('def get_failovers', 1)[1].split(
        '\n    def ', 1,
    )[0]
    assert 'provider_id.active' in block


def test_get_providers_for_agent_no_auto_create_all():
    block = _providers_for_agent_block()
    assert 'Link.sudo().create' not in block
    assert 'auto-created failover chain' not in block
    assert "('active', '=', True)" in block
    assert 'sudo().search' in block
    assert 'found.filtered(' in block
    assert 'Configure Agent' not in block
    assert 'no provider failovers configured' not in block
    assert 'No agent borrows another' in block or (
        'owns its own failover' in block
    )
    assert 'Secretary' not in block
    assert 'pns_secretary' not in block


def test_engine_does_not_couple_admin_to_chatboo():
    block = _providers_for_agent_block()
    assert 'CHATBOO_AGENT_CODE' not in block
    assert 'using Chatboo' not in block
    assert 'reusing Chatboo' not in block
    assert '_failovers_for_agent_code_optional' not in _ENGINE


def test_run_stream_failovers_stay_in_the_assigned_function():
    src = engine_source()
    block = src.split('# Resolve providers', 1)[1].split(
        'last_error = None', 1,
    )[0]
    assert 'need=' in block
    assert "get_failovers(agent_code)" not in block
    assert 'mapped(\'provider_id\')' not in block
    assert 'gpt-4o-mini' not in src.split('def llm_json_completion_result')[1].split(
        'def llm_json_completion(', 1,
    )[0]


def test_provider_resolve_failure_is_an_error_event_not_a_tuple_dump():
    src = engine_source()
    block = src.split('# Resolve providers', 1)[1].split(
        '# Build the provider cascade', 1,
    )[0]
    assert 'exception_user_text' in block
    assert "'event': 'error'" in block
    assert 'str(exc)' not in block
    assert '🛑' not in block


def test_admin_fossil_clear_does_not_name_chatboo():
    assert 'def _clear_admin_auto_link_all_fossil' in _AGENT
    assert '_align_admin_failovers_from_chatboo' not in _AGENT
    fossil = _AGENT.split(
        'def _clear_admin_auto_link_all_fossil', 1,
    )[1].split('\n    @api.model', 1)[0]
    assert 'CHATBOO' not in fossil
    assert 'chatboo' not in fossil.lower()
    assert 'admin_auto_link_fossil_cleared' in fossil
    assert 'ADMIN_AGENT_CODE' in fossil
