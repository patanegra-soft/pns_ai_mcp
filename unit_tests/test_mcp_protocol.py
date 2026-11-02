# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Unit tests for MCP dual-era protocol helpers."""
from _load_addon import load_module

_mcp_protocol = load_module('mcp_protocol', 'utils', 'mcp_protocol.py')

MCP_VERSION_2026_07_28 = _mcp_protocol.MCP_VERSION_2026_07_28
client_info_from_params = _mcp_protocol.client_info_from_params
detect_mcp_era = _mcp_protocol.detect_mcp_era
discover_result = _mcp_protocol.discover_result
header_protocol_mismatch = _mcp_protocol.header_protocol_mismatch
validate_modern_protocol_version = _mcp_protocol.validate_modern_protocol_version
wrap_modern_result = _mcp_protocol.wrap_modern_result


def test_detect_legacy_initialize():
    assert detect_mcp_era('initialize', {'protocolVersion': '2025-06-18'}) == 'legacy'


def test_detect_modern_meta():
    params = {
        '_meta': {
            'io.modelcontextprotocol/protocolVersion': MCP_VERSION_2026_07_28,
        },
    }
    assert detect_mcp_era('tools/list', params) == 'modern'


def test_detect_modern_header():
    headers = {'MCP-Protocol-Version': MCP_VERSION_2026_07_28}
    assert detect_mcp_era('tools/list', {}, headers) == 'modern'


def test_detect_legacy_tools_without_meta():
    assert detect_mcp_era('tools/call', {'name': 'get_context'}) == 'legacy'


def test_validate_modern_version_ok():
    assert validate_modern_protocol_version(MCP_VERSION_2026_07_28) is None


def test_validate_modern_version_unsupported():
    err = validate_modern_protocol_version('1900-01-01')
    assert err['code'] == -32022
    assert MCP_VERSION_2026_07_28 in err['data']['supported']


def test_header_mismatch():
    params = {'_meta': {'io.modelcontextprotocol/protocolVersion': MCP_VERSION_2026_07_28}}
    headers = {'MCP-Protocol-Version': '2025-06-18'}
    err = header_protocol_mismatch(headers, params)
    assert err and err['code'] == -32020


def test_client_info_from_params():
    params = {
        '_meta': {
            'io.modelcontextprotocol/clientInfo': {'name': 'Cursor', 'version': '1.0'},
        },
    }
    assert client_info_from_params(params)['name'] == 'Cursor'


def test_discover_result_shape():
    result = discover_result()
    assert result['resultType'] == 'complete'
    assert MCP_VERSION_2026_07_28 in result['supportedVersions']
    assert 'io.modelcontextprotocol/serverInfo' in result['_meta']
    assert 'resources' not in result['capabilities']


def test_wrap_modern_result():
    wrapped = wrap_modern_result({'tools': []}, method='tools/list')
    assert wrapped['resultType'] == 'complete'
    assert wrapped['ttlMs'] == 3600000
    assert 'io.modelcontextprotocol/serverInfo' in wrapped['_meta']


def test_get_context_stays_in_sack_hidden_from_mcp_list():
    """Chatboo sees the full registry; /mcp tools/list skips expose_mcp=False."""
    from _load_addon import addon_file

    dec = load_module('mcp_decorators_expose', 'controllers', 'mcp_decorators.py')

    @dec.mcp_tool(name='_ut_public', description='public', expose_mcp=True)
    def _public(controller, arguments):
        return {}

    @dec.mcp_tool(name='_ut_internal', description='internal', expose_mcp=False)
    def _internal(controller, arguments):
        return {}

    sack = dec.get_registered_tools()
    assert '_ut_public' in sack
    assert '_ut_internal' in sack
    assert sack['_ut_internal']['expose_mcp'] is False

    mcp_list = dec.list_registered_tools_for_mcp()
    assert '_ut_public' in mcp_list
    assert '_ut_internal' not in mcp_list

    src = addon_file('controllers', 'tools_context.py').read_text(encoding='utf-8')
    assert "name='get_context'" in src
    assert 'expose_mcp=False' in src
