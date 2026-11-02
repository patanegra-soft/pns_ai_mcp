# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""The engine has no business glossary for MCP tool loading."""
from __future__ import annotations

from _load_addon import load_module

mcp_utils = load_module(
    'mcp_utils', 'lib', 'llm', 'utils', 'mcp_utils.py',
)


def test_default_domain_keywords_are_empty():
    assert mcp_utils.DEFAULT_DOMAIN_TRIGGER_KEYWORDS == []


def test_empty_default_does_not_skip_tools():
    assert mcp_utils.should_load_mcp_tools(
        'hola, qué tiempo hace',
        [{'role': 'user', 'content': 'hola, qué tiempo hace'}],
    ) is True


def test_caller_keywords_still_gate():
    assert mcp_utils.should_load_mcp_tools(
        'hola',
        [{'role': 'user', 'content': 'hola'}],
        domain_keywords=['factura'],
    ) is False
    assert mcp_utils.should_load_mcp_tools(
        'ver factura 12',
        [{'role': 'user', 'content': 'ver factura 12'}],
        domain_keywords=['factura'],
    ) is True


def test_prior_tool_calls_load_tools():
    assert mcp_utils.should_load_mcp_tools(
        'sigue',
        [
            {'role': 'assistant', 'content': '', 'tool_calls': [{'id': '1'}]},
            {'role': 'user', 'content': 'sigue'},
        ],
        domain_keywords=['factura'],
    ) is True
