# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""OpenAPI catalogue must follow spec_json (manual servers)."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

_DRIVERS = Path(__file__).resolve().parents[1] / 'common' / 'lib' / 'api' / 'drivers'


def _load_openapi_driver():
    pkg_name = 'pns_test_tools_sync_drivers'
    if pkg_name in sys.modules:
        return sys.modules[pkg_name + '.openapi_driver']
    pkg = type(sys)('ModuleType')
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

_SPEC_A = {
    'openapi': '3.0.0',
    'info': {'title': 'A', 'version': '1'},
    'paths': {
        '/teams/members': {
            'get': {'operationId': 'getTeamMembers', 'summary': 'Members'},
        },
    },
}
_SPEC_B = {
    'openapi': '3.0.0',
    'info': {'title': 'B', 'version': '1'},
    'paths': {
        '/teams/spend': {
            'get': {'operationId': 'getSpend', 'summary': 'Spend'},
        },
    },
}


def _tools_from_server(spec):
    server = SimpleNamespace(
        api_type='openapi',
        spec_manual=True,
        spec_json=json.dumps(spec),
        spec_url='',
        code='demo',
    )
    return OpenAPIDriver()._spec_to_tools(
        OpenAPIDriver()._resolve_spec(server, fetch=False))


def test_spec_change_changes_tool_names():
    assert [t['name'] for t in _tools_from_server(_SPEC_A)] == ['getTeamMembers']
    assert [t['name'] for t in _tools_from_server(_SPEC_B)] == ['getSpend']


def test_stale_tools_json_would_mismatch_spec():
    """Document the LWHC failure mode: old catalogue vs new spec."""
    stale_tools = [{'name': 'getTeamMembers'}, {'name': 'getSpend'}]
    live_tools = _tools_from_server(_SPEC_A)
    live_names = {t['name'] for t in live_tools}
    stale_names = {t['name'] for t in stale_tools}
    assert stale_names != live_names
    assert 'getSpend' in stale_names - live_names
