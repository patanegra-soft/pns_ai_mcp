# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""openapi_spec_generator: JSON extraction and structural validation."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest

_ROOT = Path(__file__).resolve().parents[1] / 'common'
_SERVICES = _ROOT / 'services'
_DRIVERS = _ROOT / 'lib' / 'api' / 'drivers'


def _load_generator():
    pkg_name = 'pns_test_openapi_gen'
    if f'{pkg_name}.openapi_spec_generator' in sys.modules:
        return sys.modules[f'{pkg_name}.openapi_spec_generator']

    lib_pkg = ModuleType('odoo.addons.pns_ai_mcp')
    lib_pkg.__path__ = [str(_ROOT.parent)]
    sys.modules['odoo.addons.pns_ai_mcp'] = lib_pkg

    inner = ModuleType('odoo.addons.pns_ai_mcp.lib')
    inner.__path__ = [str(_ROOT / 'lib')]
    sys.modules['odoo.addons.pns_ai_mcp.lib'] = inner

    api_pkg = ModuleType('odoo.addons.pns_ai_mcp.lib.api')
    api_pkg.__path__ = [str(_ROOT / 'lib' / 'api')]
    sys.modules['odoo.addons.pns_ai_mcp.lib.api'] = api_pkg

    drivers_pkg = ModuleType('odoo.addons.pns_ai_mcp.lib.api.drivers')
    drivers_pkg.__path__ = [str(_DRIVERS)]
    sys.modules['odoo.addons.pns_ai_mcp.lib.api.drivers'] = drivers_pkg

    spec_base = importlib.util.spec_from_file_location(
        'odoo.addons.pns_ai_mcp.lib.api.drivers.base', _DRIVERS / 'base.py')
    base = importlib.util.module_from_spec(spec_base)
    sys.modules[spec_base.name] = base
    spec_base.loader.exec_module(base)

    spec_oa = importlib.util.spec_from_file_location(
        'odoo.addons.pns_ai_mcp.lib.api.drivers.openapi_driver',
        _DRIVERS / 'openapi_driver.py')
    oa = importlib.util.module_from_spec(spec_oa)
    sys.modules[spec_oa.name] = oa
    spec_oa.loader.exec_module(oa)

    utils_pkg = ModuleType('odoo.addons.pns_ai_mcp.utils')
    utils_pkg.__path__ = [str(_ROOT / 'utils')]
    sys.modules['odoo.addons.pns_ai_mcp.utils'] = utils_pkg

    spec_hist = importlib.util.spec_from_file_location(
        'odoo.addons.pns_ai_mcp.utils.history_compact',
        _ROOT / 'utils' / 'history_compact.py')
    hist = importlib.util.module_from_spec(spec_hist)
    sys.modules[spec_hist.name] = hist
    spec_hist.loader.exec_module(hist)

    services_pkg = ModuleType('odoo.addons.pns_ai_mcp.services')
    services_pkg.__path__ = [str(_SERVICES)]
    sys.modules['odoo.addons.pns_ai_mcp.services'] = services_pkg

    spec_gen = importlib.util.spec_from_file_location(
        'odoo.addons.pns_ai_mcp.services.openapi_spec_generator',
        _SERVICES / 'openapi_spec_generator.py')
    gen = importlib.util.module_from_spec(spec_gen)
    sys.modules[spec_gen.name] = gen
    spec_gen.loader.exec_module(gen)
    return gen


gen_mod = _load_generator()
extract_json_object = gen_mod.extract_json_object
validate_openapi_spec = gen_mod.validate_openapi_spec
documentation_to_text = gen_mod.documentation_to_text
extract_documentation_payload = gen_mod.extract_documentation_payload
assert_useful_documentation = gen_mod.assert_useful_documentation
normalize_generated_spec = gen_mod.normalize_generated_spec
resolve_openapi_gen_system_prompt = gen_mod.resolve_openapi_gen_system_prompt
_build_llm_prompts = gen_mod._build_llm_prompts
generate_spec_from_documentation = gen_mod.generate_spec_from_documentation
OpenAPISpecGeneratorError = gen_mod.OpenAPISpecGeneratorError

_MIN_SPEC = {
    'openapi': '3.0.0',
    'info': {'title': 'Demo', 'version': '1.0'},
    'paths': {
        '/items': {
            'get': {
                'operationId': 'listItems',
                'summary': 'List items',
            },
        },
    },
}


def test_extract_json_object_from_fence():
    text = 'Here:\n```json\n%s\n```' % json.dumps(_MIN_SPEC)
    assert extract_json_object(text) == _MIN_SPEC


def test_extract_json_object_raw():
    assert extract_json_object(json.dumps(_MIN_SPEC)) == _MIN_SPEC


def test_extract_json_object_repairs_truncated_after_complete_path():
    full = json.dumps(_MIN_SPEC, separators=(',', ':'))
    cut = full[: full.index('"List items"') + len('"List items"')]
    assert not cut.endswith('}')
    out = extract_json_object(cut)
    assert out['openapi'] == '3.0.0'
    assert out['paths']['/items']['get']['operationId'] == 'listItems'


def test_extract_json_object_keeps_literal_newlines_in_strings():
    messy = (
        '{"openapi":"3.0.3","info":{"title":"Admin API",'
        '"description":"La Admin API te permite\nacceder a los datos"},'
        '"paths":{"/teams":{"get":{"operationId":"listTeams"}}}}'
    )
    out = extract_json_object(messy)
    assert out['info']['title'] == 'Admin API'
    assert 'acceder' in out['info']['description']
    assert out['paths']['/teams']['get']['operationId'] == 'listTeams'


def test_extract_json_object_repairs_truncated_mid_string():
    full = json.dumps(_MIN_SPEC, separators=(',', ':'))
    cut = full[: full.index('List items') + 4]
    out = extract_json_object(cut)
    assert out is not None
    assert '/items' in (out.get('paths') or {})
    assert out['paths']['/items']['get']['operationId'] == 'listItems'


def test_generate_spec_calls_after_llm_before_parse(monkeypatch):
    server = MagicMock()
    server.code = 'demo'
    server.name = 'Demo'
    server.base_url = 'https://api.example.com'
    server.auth_type = 'none'
    server.notes = ''
    server.openapi_gen_prompt = ''
    server._detection_llm_provider.return_value = MagicMock()
    seen = []

    def fake_llm(env, system, user, usage_acc, max_tokens=8192, timeout=120):
        return json.dumps(_MIN_SPEC), usage_acc

    def after_llm(text, usage):
        seen.append(text)

    monkeypatch.setattr(gen_mod, '_llm_call', fake_llm)
    docs = '<p>List items via GET /items. ' + ('More API detail. ' * 40) + '</p>'
    generate_spec_from_documentation(None, server, docs, after_llm=after_llm)
    assert seen and '"paths"' in seen[0]


def test_generate_spec_keeps_truncated_openapi_with_warning(monkeypatch):
    server = MagicMock()
    server.code = 'demo'
    server.name = 'Demo'
    server.base_url = 'https://api.example.com'
    server.auth_type = 'none'
    server.notes = ''
    server.openapi_gen_prompt = ''
    server._detection_llm_provider.return_value = MagicMock()

    full = json.dumps(_MIN_SPEC, separators=(',', ':'))
    truncated = full[: full.index('"List items"') + len('"List items"')]

    def fake_llm(env, system, user, usage_acc, max_tokens=8192, timeout=120):
        return truncated, usage_acc

    monkeypatch.setattr(gen_mod, '_llm_call', fake_llm)
    docs = '<p>List items via GET /items. ' + ('More API detail. ' * 40) + '</p>'
    spec, warnings, _usage = generate_spec_from_documentation(None, server, docs)
    assert spec['paths']['/items']['get']['operationId'] == 'listItems'
    assert any('truncated' in (w or '').lower() for w in warnings)


def test_validate_openapi_spec_adds_servers_from_base_url():
    spec, warnings = validate_openapi_spec(
        dict(_MIN_SPEC), base_url='https://api.example.com')
    assert spec['servers'][0]['url'] == 'https://api.example.com'
    assert warnings


def test_normalize_generated_spec_fills_operation_ids():
    spec = {
        'paths': {
            '/items': {
                'get': {'summary': 'List items'},
            },
        },
    }
    server = MagicMock()
    server.name = 'Demo'
    server.code = 'demo'
    out = normalize_generated_spec(spec, server)
    assert out['paths']['/items']['get']['operationId'] == 'get__items'
    assert out['info']['title'] == 'Demo'


def test_validate_openapi_spec_rejects_missing_paths():
    with pytest.raises(OpenAPISpecGeneratorError, match='no paths'):
        validate_openapi_spec({'openapi': '3.0.0', 'info': {}, 'paths': {}})


def test_build_llm_prompts_uses_server_prompt_without_odoo_metadata():
    server = MagicMock()
    server.openapi_gen_prompt = 'Read the page and output OpenAPI 3 JSON only.'
    server.code = 'cursor-admin'
    server.name = 'Cursor Admin'
    server.base_url = 'https://api.cursor.com'
    system, user = _build_llm_prompts(server, 'GET /teams/members')
    assert system == 'Read the page and output OpenAPI 3 JSON only.'
    assert 'cursor-admin' not in user
    assert 'api.cursor.com' not in user
    assert 'GET /teams/members' in user
    assert 'Do not follow links' in user


def test_resolve_openapi_gen_system_prompt_falls_back_to_default():
    server = MagicMock()
    server.openapi_gen_prompt = ''
    prompt = resolve_openapi_gen_system_prompt(server)
    assert 'openapi.json' in prompt
    assert 'OpenAPI 3.0' in prompt


def test_documentation_to_text_strips_html():
    html = '<html><body><h1>Users</h1><p>GET /users</p></body></html>'
    text = documentation_to_text(html)
    assert 'Users' in text
    assert 'GET /users' in text
    assert '<h1>' not in text


def test_extract_documentation_payload_prefers_article():
    body = (
        'GET /teams/members lists members. '
        'POST /teams/spend records spend. '
        'PATCH /teams/settings updates settings. '
    ) * 8
    html = (
        '<html><body><nav>Menu only noise</nav>'
        '<article><h1>API</h1><p>%s</p></article>'
        '<footer>x</footer></body></html>'
    ) % body
    text = extract_documentation_payload(html, content_type='text/html')
    assert 'GET /teams/members' in text
    assert 'Menu only noise' not in text


def test_assert_useful_documentation_rejects_spa_shell():
    with pytest.raises(OpenAPISpecGeneratorError, match='little readable'):
        assert_useful_documentation('Loading…')


def test_generate_spec_fails_on_invalid_json_without_repair_loop(monkeypatch):
    server = MagicMock()
    server.code = 'demo'
    server.name = 'Demo'
    server.base_url = 'https://api.example.com'
    server.auth_type = 'none'
    server.notes = ''
    server.openapi_gen_prompt = ''
    server._detection_llm_provider.return_value = MagicMock()

    def fake_llm(env, system, user, usage_acc, max_tokens=8192, timeout=120):
        return 'not json at all', usage_acc

    monkeypatch.setattr(gen_mod, '_llm_call', fake_llm)
    docs = '<p>List items via GET /items. ' + ('More API detail. ' * 40) + '</p>'
    with pytest.raises(OpenAPISpecGeneratorError, match='could not be parsed') as err:
        generate_spec_from_documentation(None, server, docs)
    assert err.value.raw_text == 'not json at all'


def test_generate_spec_keeps_openapi_when_paths_empty(monkeypatch):
    server = MagicMock()
    server.code = 'demo'
    server.name = 'Demo'
    server.base_url = 'https://api.example.com'
    server.auth_type = 'none'
    server.notes = ''
    server.openapi_gen_prompt = ''
    server._detection_llm_provider.return_value = MagicMock()

    def fake_llm(env, system, user, usage_acc, max_tokens=8192, timeout=120):
        return (
            '{"openapi":"3.0.3","info":{"title":"Admin API","version":"1.0"},'
            '"paths":{}}'
        ), usage_acc

    monkeypatch.setattr(gen_mod, '_llm_call', fake_llm)
    docs = '<p>List items via GET /items. ' + ('More API detail. ' * 40) + '</p>'
    spec, warnings, _usage = generate_spec_from_documentation(None, server, docs)
    assert spec['info']['title'] == 'Admin API'
    assert any('path' in (w or '').lower() for w in warnings)


def test_generate_spec_human_error_without_provider():
    server = MagicMock()
    server._detection_llm_provider.return_value = None
    with pytest.raises(
            OpenAPISpecGeneratorError,
            match='No AI provider is configured'):
        generate_spec_from_documentation(None, server, 'GET /items')


def test_default_openapi_prompt_is_this_page_only():
    prompt = gen_mod.DEFAULT_OPENAPI_GEN_SYSTEM_PROMPT
    assert 'This page only' in prompt
    assert 'Do not follow links' in prompt
    assert 'same domain' in prompt
    assert 'eTLD+1' not in prompt
    assert 'one path level' not in prompt
