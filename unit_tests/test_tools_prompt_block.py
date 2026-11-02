# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Prompt block: usage_guide in, inactive servers out. No vendor names."""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from common.lib.api.tools_prompt_block import (
    format_tool_arg_token,
    format_tools_prompt_block,
)


_TOOL = {
    'name': 'list_items',
    'description': 'List items',
    'inputSchema': {
        'type': 'object',
        'properties': {'body': {'type': 'object'}},
    },
}

_TOOL_NESTED = {
    'name': 'post__list',
    'description': 'List with nested body',
    'inputSchema': {
        'type': 'object',
        'required': ['body'],
        'properties': {
            'body': {
                'type': 'object',
                'required': ['data'],
                'properties': {
                    'data': {'type': 'object'},
                },
            },
        },
    },
}


def test_inactive_server_omitted():
    block = format_tools_prompt_block([
        {
            'code': 'srv_live',
            'name': 'Live API',
            'usage_guide': 'Call list_items with a body object.',
            'tools': [_TOOL],
            'active': True,
        },
        {
            'code': 'srv_archive',
            'name': 'Archived clone',
            'usage_guide': 'Do not use this copy.',
            'tools': [_TOOL],
            'active': False,
        },
    ])
    assert 'srv_live' in block
    assert 'Call list_items with a body object.' in block
    assert 'list_items(body)' in block
    assert 'srv_archive' not in block
    assert 'Archived clone' not in block
    assert 'active_test=False' in block
    assert 'usage_guide' in block
    assert 'match a listed row by code or name' in block
    assert 'do not invent a shorter code' in block
    assert 'Relaxaicode on ai.api.server is rejected' in block
    assert 'discovery_target_kind=api_server' in block
    assert 'propose create on ai.context' in block


def test_usage_guide_without_tools_still_listed():
    block = format_tools_prompt_block([{
        'code': 'srv_notes',
        'name': 'Notes only',
        'usage_guide': 'Use sibling srv_live instead.',
        'tools': [],
        'active': True,
    }])
    assert 'srv_notes' in block
    assert 'Use sibling srv_live instead.' in block


def test_empty_when_only_inactive():
    assert format_tools_prompt_block([{
        'code': 'srv_dead',
        'name': 'Dead',
        'usage_guide': 'gone',
        'tools': [_TOOL],
        'active': False,
    }]) == ''


def test_nested_required_in_signature():
    assert format_tool_arg_token(
        'body',
        {'type': 'object', 'required': ['data'], 'properties': {'data': {}}},
    ) == 'body{data}'
    assert format_tool_arg_token('limit', {'type': 'integer'}) == 'limit'
    block = format_tools_prompt_block([{
        'code': 'srv_live',
        'name': 'Live API',
        'usage_guide': '',
        'tools': [_TOOL_NESTED],
        'active': True,
    }])
    assert 'post__list(body{data})' in block
