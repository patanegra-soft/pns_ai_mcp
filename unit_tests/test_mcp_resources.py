# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Our MCP server does not expose the optional resources primitive."""
from __future__ import annotations

from pathlib import Path

from _load_addon import load_module

_ROOT = Path(__file__).resolve().parents[1]


def test_server_does_not_advertise_resources():
    proto = load_module('pns_ai_mcp_mcp_protocol', 'utils', 'mcp_protocol.py')
    result = proto.discover_result()
    assert 'resources' not in result['capabilities']
    assert proto.MCP_LIST_METHODS == frozenset({'tools/list', 'prompts/list'})


def test_main_does_not_list_skills_as_prompts():
    main = (_ROOT / 'common' / 'controllers' / 'main.py').read_text(encoding='utf-8')
    assert 'skill.mcp_prompt_name()' not in main
    assert "prompt_name.startswith('skill.')" not in main


def test_main_has_no_resource_handlers():
    main = (_ROOT / 'common' / 'controllers' / 'main.py').read_text(encoding='utf-8')
    assert "method == 'resources/list'" not in main
    assert "method == 'resources/read'" not in main
    assert 'def _mcp_resources_list' not in main
    assert 'def _mcp_resources_read' not in main
    assert "'resources': {'listChanged': False}" not in main
    assert '"resources":{"listChanged":false}' not in main
    assert "env['pns_ai_mcp.mcp_resource']" not in main


def test_mcp_resources_module_removed():
    assert not (_ROOT / 'common' / 'utils' / 'mcp_resources.py').is_file()


def test_sandbox_exposes_memoryview():
    src = (
        _ROOT / 'common' / 'controllers' / 'context_builder.py'
    ).read_text(encoding='utf-8')
    assert "'memoryview'" in src
