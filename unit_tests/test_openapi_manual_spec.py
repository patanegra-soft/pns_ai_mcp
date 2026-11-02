# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""OpenAPI driver: spec_manual never re-fetches or depends on spec_url."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

_DRIVERS = (
    Path(__file__).resolve().parents[1] / 'common' / 'lib' / 'api' / 'drivers'
)

_MIN_SPEC = {
    'openapi': '3.0.0',
    'info': {'title': 'Legacy', 'version': '1.0'},
    'paths': {
        '/ping': {
            'get': {
                'operationId': 'ping',
                'summary': 'Ping',
            },
        },
    },
}


def _load_openapi_driver():
    """Load openapi_driver without pulling MCPClient / Odoo."""
    pkg_name = 'pns_test_api_drivers'
    if pkg_name in sys.modules:
        return sys.modules[pkg_name + '.openapi_driver']
    pkg = ModuleType(pkg_name)
    pkg.__path__ = [str(_DRIVERS)]
    sys.modules[pkg_name] = pkg

    spec_base = importlib.util.spec_from_file_location(
        pkg_name + '.base', _DRIVERS / 'base.py')
    base = importlib.util.module_from_spec(spec_base)
    sys.modules[pkg_name + '.base'] = base
    spec_base.loader.exec_module(base)

    spec_oa = importlib.util.spec_from_file_location(
        pkg_name + '.openapi_driver', _DRIVERS / 'openapi_driver.py')
    oa = importlib.util.module_from_spec(spec_oa)
    sys.modules[pkg_name + '.openapi_driver'] = oa
    spec_oa.loader.exec_module(oa)
    return oa


oa_mod = _load_openapi_driver()
OpenAPIDriver = oa_mod.OpenAPIDriver
APIDriverError = oa_mod.APIDriverError


def _manual_server(**kwargs):
    vals = dict(
        code='legacy',
        spec_manual=True,
        spec_json=json.dumps(_MIN_SPEC),
        spec_url='https://should-not-be-fetched.example/openapi.json',
        base_url='https://api.example.com',
        timeout=30,
        auth_type='none',
        auth_token='',
        auth_header_name='Authorization',
    )
    vals.update(kwargs)
    server = SimpleNamespace(**vals)
    server.sudo = lambda: server
    return server


def test_manual_discover_does_not_fetch(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError('spec_url must not be fetched when spec_manual')

    monkeypatch.setattr(oa_mod, '_request_public_http', boom)
    catalog = OpenAPIDriver().discover(_manual_server())
    names = [t['name'] for t in catalog['tools']]
    assert names == ['ping']
    assert catalog['spec']['info']['title'] == 'Legacy'


def test_manual_discover_empty_raises_without_fetch(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError('empty manual spec must not fall back to fetch')

    monkeypatch.setattr(oa_mod, '_request_public_http', boom)
    with pytest.raises(APIDriverError, match='No OpenAPI spec pasted'):
        OpenAPIDriver().discover(_manual_server(spec_json=''))


def test_manual_invalid_json_raises_without_fetch(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError('invalid JSON must not fall back to fetch')

    monkeypatch.setattr(oa_mod, '_request_public_http', boom)
    with pytest.raises(APIDriverError, match='not valid JSON'):
        OpenAPIDriver().discover(_manual_server(spec_json='{not json'))


def test_manual_test_connection_uses_pasted_spec(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError('test_connection must not fetch when spec_manual')

    monkeypatch.setattr(oa_mod, '_request_public_http', boom)
    summary = OpenAPIDriver().test_connection(_manual_server())
    assert 'manual spec' in summary
    assert 'Legacy' in summary


def test_remote_discover_still_fetches(monkeypatch):
    called = []

    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return _MIN_SPEC

    def fake_get(method, url, **_k):
        called.append(url)
        return _Resp()

    monkeypatch.setattr(oa_mod, '_request_public_http', fake_get)
    server = _manual_server(spec_manual=False, spec_json='')
    catalog = OpenAPIDriver().discover(server)
    assert called == [server.spec_url]
    assert catalog['tools'][0]['name'] == 'ping'


def test_api_key_header_from_openapi3():
    spec = dict(_MIN_SPEC)
    spec['components'] = {
        'securitySchemes': {
            'ApiKeyAuth': {'type': 'apiKey', 'in': 'header', 'name': 'apikey'},
        },
    }
    assert OpenAPIDriver.api_key_header_name(spec) == 'apikey'


def test_api_key_header_from_oas2():
    spec = dict(_MIN_SPEC)
    spec['securityDefinitions'] = {
        'api_key': {'type': 'apiKey', 'in': 'header', 'name': 'X-API-Key'},
    }
    assert OpenAPIDriver.api_key_header_name(spec) == 'X-API-Key'


def test_api_key_header_ambiguous_is_none():
    spec = dict(_MIN_SPEC)
    spec['components'] = {
        'securitySchemes': {
            'a': {'type': 'apiKey', 'in': 'header', 'name': 'A'},
            'b': {'type': 'apiKey', 'in': 'header', 'name': 'B'},
        },
    }
    assert OpenAPIDriver.api_key_header_name(spec) is None


def test_api_key_header_query_ignored():
    spec = dict(_MIN_SPEC)
    spec['components'] = {
        'securitySchemes': {
            'q': {'type': 'apiKey', 'in': 'query', 'name': 'key'},
        },
    }
    assert OpenAPIDriver.api_key_header_name(spec) is None
    assert OpenAPIDriver.api_key_header_names(spec) == []


def test_api_key_header_names_lists_all():
    spec = dict(_MIN_SPEC)
    spec['components'] = {
        'securitySchemes': {
            'a': {'type': 'apiKey', 'in': 'header', 'name': 'A'},
            'b': {'type': 'apiKey', 'in': 'header', 'name': 'B'},
        },
    }
    assert OpenAPIDriver.api_key_header_names(spec) == ['A', 'B']


def test_reads_only_follows_the_http_method(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError('reads_only must not fetch the spec')

    monkeypatch.setattr(oa_mod, '_request_public_http', boom)
    spec = json.loads(json.dumps(_MIN_SPEC))
    spec['paths']['/employees'] = {
        'post': {'operationId': 'createEmployee'},
    }
    server = _manual_server(spec_json=json.dumps(spec))
    driver = OpenAPIDriver()
    assert driver.reads_only(server, 'ping') is True
    assert driver.reads_only(server, 'createEmployee') is False
    assert driver.reads_only(server, 'notInSpec') is False
