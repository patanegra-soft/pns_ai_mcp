# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""The MCP API key travels in a header only. It is never read from the URL,
and no fragment of it is written to the log."""
from pathlib import Path

_COMMON = Path(__file__).resolve().parents[1] / 'common'


def test_no_api_key_from_url():
    src = (_COMMON / 'controllers' / 'main.py').read_text(encoding='utf-8')
    assert "params.get('api_key')" not in src
    assert 'params.get("api_key")' not in src
    assert "args.get('api_key')" not in src
    assert 'X-MCP-API-Key' in src


def test_no_key_fragment_in_log():
    src = (_COMMON / 'controllers' / 'main.py').read_text(encoding='utf-8')
    assert 'api_key[:' not in src


def test_http_test_helper_sends_no_key_in_url():
    src = (_COMMON / 'tests' / '_helpers.py').read_text(encoding='utf-8')
    body = src.split('def mcp_test_url', 1)[1].split('def ', 1)[0]
    assert 'urlencode' not in body
    headers = src.split('def mcp_test_headers', 1)[1].split('def ', 1)[0]
    assert "'X-MCP-API-Key': api_key" in headers
