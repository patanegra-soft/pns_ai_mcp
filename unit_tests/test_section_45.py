# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""§4.5: reusable data is not system, confirm does not grow the list,
pictures need an explicit whitelist entry, /mcp write tools use is_write,
provider errors stay out of the chat, OpenAPI hops stay public."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from _load_addon import safe_plan_source

_ROOT = Path(__file__).resolve().parents[1]
_COMMON = _ROOT / 'common'
_MESSAGES = (_COMMON / 'utils' / 'engine_turn_messages.py').read_text(encoding='utf-8')
_PLAN = safe_plan_source()
_OP = (_COMMON / 'models' / 'safe_operation.py').read_text(encoding='utf-8')
_WL = (_COMMON / 'models' / 'url_whitelist.py').read_text(encoding='utf-8')
_MAIN = (_COMMON / 'controllers' / 'main.py').read_text(encoding='utf-8')
_CLOSE = (_COMMON / 'utils' / 'engine_turn_close.py').read_text(encoding='utf-8')
_LOOP = (_COMMON / 'utils' / 'engine_tool_loop.py').read_text(encoding='utf-8')
_OPENAPI = (_COMMON / 'lib' / 'api' / 'drivers' / 'openapi_driver.py').read_text(encoding='utf-8')
_GEN = (_COMMON / 'services' / 'openapi_spec_generator.py').read_text(encoding='utf-8')


def _safe():
    spec = importlib.util.spec_from_file_location(
        'fetch_url_safe_for_s45', _COMMON / 'utils' / 'fetch_url_safe.py',
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_reusable_data_is_delimited_user_data():
    hint = _MESSAGES.split('def _tool_loop_reuse_hint', 1)[1].split(
        'def _tool_loop_recall_images', 1,
    )[0]
    assert '"role": "system"' not in hint
    assert '"role": "user"' in hint
    assert '[REUSABLE DATA]' in hint
    assert '[REUSABLE QUERY]' in hint
    assert 'self._turn_untrusted = True' in hint


def test_confirming_open_fetch_does_not_grow_the_list():
    ensure = _PLAN.split('def _ensure_fetch_url_whitelist', 1)[1].split(
        '\ndef ', 1,
    )[0]
    assert 'is_url_access_open()' in ensure
    assert '_ensure_domain_whitelisted' not in ensure.split('is_url_access_open()', 1)[1].split(
        'entry = Whitelist', 1,
    )[0]
    maybe = _OP.split('def _maybe_auto_whitelist', 1)[1].split('\ndef ', 1)[0]
    open_block = maybe.split('is_url_access_open()', 1)[1].split(
        'if not self.env.user.has_group', 1,
    )[0]
    assert '_ensure_domain_whitelisted' not in open_block
    assert 'return' in open_block


def test_remote_image_needs_an_explicit_web_entry():
    body = _WL.split('def may_show_remote_image', 1)[1].split('\n    @api.model', 1)[0]
    assert 'is_domain_whitelisted(hostname, kind=\'web\')' in body
    assert 'is_url_access_open()' not in body


def test_tools_call_uses_is_write_not_a_name_list():
    call = _MAIN.split('def _mcp_tools_call', 1)[1].split(
        'def _mcp_', 1,
    )[0]
    assert 'write_tools' not in call
    assert 'confirm_write_operation' not in call
    assert 'get_tool_metadata(tool_name)' in call
    assert "tool_metadata.get('is_write')" in call


def test_provider_errors_do_not_name_the_endpoint():
    empty = _CLOSE.split('def _tool_loop_raise_empty', 1)[1].split(
        '\n    def ', 1,
    )[0]
    assert "config['endpoint']" in empty  # still logged
    assert '% (config[\'endpoint\']' not in empty
    assert 'The AI provider rejected the request' in empty
    raise_live = _LOOP.split('except ProviderConnectionError:', 1)[1].split(
        'return content_buffer', 1,
    )[0]
    assert 'The AI provider could not be reached.' in raise_live
    assert 'raise ProviderConnectionError(str(e))' not in raise_live


def test_openapi_uses_the_public_http_helper():
    assert 'request_public_http(' in _OPENAPI
    assert 'allow_redirects=True' not in _OPENAPI
    assert 'request_public_http(' in _GEN


class _Resp:
    def __init__(self, status=200, headers=None, body=b''):
        self.status_code = status
        self.headers = headers or {}
        self.is_redirect = 300 <= status < 400 and 'Location' in (headers or {})
        self._body = body

    def iter_content(self, chunk_size=65536):
        yield self._body

    def close(self):
        pass


def test_public_http_refuses_a_redirect_to_localhost(monkeypatch):
    safe = _safe()
    import requests
    calls = []

    def _req(method, url, **kwargs):
        calls.append(url)
        assert kwargs.get('allow_redirects') is False
        if 'ok.example' in url:
            return _Resp(302, {'Location': 'http://127.0.0.1/secret'})
        raise AssertionError('must not follow %s' % url)

    monkeypatch.setattr(requests, 'request', _req)
    monkeypatch.setattr(safe, 'non_public_host_error', lambda url: (
        'internal' if '127.0.0.1' in url else ''
    ))
    with pytest.raises(ValueError, match='internal'):
        safe.request_public_http('GET', 'https://ok.example/doc')
    assert calls == ['https://ok.example/doc']


def test_public_http_drops_auth_on_another_host(monkeypatch):
    safe = _safe()
    import requests
    seen = []

    def _req(method, url, **kwargs):
        seen.append((url, dict(kwargs.get('headers') or {})))
        if 'first.example' in url:
            return _Resp(302, {'Location': 'https://second.example/x'})
        return _Resp(200, {}, b'ok')

    monkeypatch.setattr(requests, 'request', _req)
    monkeypatch.setattr(safe, 'non_public_host_error', lambda url: '')
    resp = safe.request_public_http(
        'GET', 'https://first.example/a',
        headers={'Authorization': 'Bearer secret', 'Accept': 'text/plain'},
    )
    assert resp._content == b'ok'
    assert seen[0][1].get('Authorization') == 'Bearer secret'
    assert 'Authorization' not in seen[1][1]
    assert seen[1][1].get('Accept') == 'text/plain'
