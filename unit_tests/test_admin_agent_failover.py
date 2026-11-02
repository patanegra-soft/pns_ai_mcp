# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""AI Admin agent registry + short-JSON failover helper contracts."""
from __future__ import annotations

from pathlib import Path
from _load_addon import engine_source, skill_source

_ROOT = Path(__file__).resolve().parents[1]


def test_registry_has_admin_feature():
    from _load_addon import load_module
    reg = load_module('ai_agent_registry', 'utils', 'ai_agent_registry.py')
    assert reg.ADMIN_AGENT_CODE == 'pns_ai_admin'
    assert reg.FEATURE_AGENT_CODES == {'admin': 'pns_ai_admin'}
    assert reg.MCP_BARE_AGENT_CODE == 'pns_ai_mcp'


def test_ai_agent_data_seeds_admin_inference():
    xml = (_ROOT / 'common' / 'data' / 'ai_agent_data.xml').read_text(encoding='utf-8')
    assert 'id="ai_agent_admin"' in xml
    assert '<field name="code">pns_ai_admin</field>' in xml
    assert 'agent_type">inference</field>' in xml
    assert '<field name="code">pns_ai_mcp</field>' in xml


def test_detection_and_openapi_use_admin_not_mcp_endpoint():
    ext = (_ROOT / 'common' / 'models' / 'external_server.py').read_text(
        encoding='utf-8',
    )
    assert "consumer_key='admin'" in ext
    assert "get_providers_for_agent('pns_ai_mcp')" not in ext
    gen = (_ROOT / 'common' / 'services' / 'openapi_spec_generator.py').read_text(
        encoding='utf-8',
    )
    assert 'llm_json_completion_for_agent' in gen
    assert "consumer_key='admin'" in gen
    skill = skill_source()
    resolve_block = skill.split(
        'def _resolve_inference_provider', 1,
    )[1].split('\n    def ', 1)[0]
    assert "consumer_key='admin'" in resolve_block
    assert "need='conversation'" in resolve_block
    assert "consumer_key='chatboo'" not in resolve_block
    wiz = (_ROOT / 'common' / 'wizard' / 'skill_capture_wizard.py').read_text(
        encoding='utf-8',
    )
    wiz_block = wiz.split('def _resolve_param_provider', 1)[1].split(
        '\n    def ', 1,
    )[0]
    assert "consumer_key='admin'" in wiz_block
    assert "need='conversation'" in wiz_block


def test_llm_json_completion_for_agent_helper_present():
    src = engine_source()
    assert 'def llm_json_completion_for_agent' in src
    assert 'def resolve_providers_for_consumer' in src
    assert '_log_provider_failover' in src
    assert '_is_llm_json_context_overflow' in src
    assert "consumer_key='admin'" in src


def test_agent_engine_source_channel_is_per_host():
    src = engine_source()
    assert 'source_channel=None, client_label=None' in src
    assert 'agent_code=None' in src
    assert "setdefault('agent_code', self._agent_code)" in src
    assert 'turn_prefix=None' in src
    assert "setdefault('source_channel', self._source_channel)" in src
    assert "setdefault('source_channel', 'chatboo')" not in src
    assert "source_channel or 'chatboo'" not in src
    assert "or 'internal'" in src
    assert 'mcp_source_channel' in src
    assert 'def _http_request' in src
    assert 'ctx.get(\'mcp_turn\')' in src or 'ctx.get("mcp_turn")' in src
