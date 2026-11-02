# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""OpenAPI driver: HTTP Basic auth header (username + empty password)."""
from __future__ import annotations

import base64
import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

_DRIVERS = (
    Path(__file__).resolve().parents[1] / 'common' / 'lib' / 'api' / 'drivers'
)


def _load_base():
    pkg_name = 'pns_test_api_drivers_basic'
    if pkg_name in sys.modules:
        return sys.modules[pkg_name + '.base']
    pkg = ModuleType(pkg_name)
    pkg.__path__ = [str(_DRIVERS)]
    sys.modules[pkg_name] = pkg
    spec = importlib.util.spec_from_file_location(
        pkg_name + '.base', _DRIVERS / 'base.py')
    base = importlib.util.module_from_spec(spec)
    sys.modules[pkg_name + '.base'] = base
    spec.loader.exec_module(base)
    return base


base_mod = _load_base()
build_auth_headers = base_mod.build_auth_headers


def _server(**kwargs):
    vals = dict(
        auth_type='basic',
        auth_token='crsr_test_key',
        auth_header_name='Authorization',
    )
    vals.update(kwargs)
    server = SimpleNamespace(**vals)
    server.sudo = lambda: server
    return server


def test_basic_auth_header_encodes_username_and_empty_password():
    headers = build_auth_headers(_server())
    expected = base64.b64encode(b'crsr_test_key:').decode('ascii')
    assert headers == {'Authorization': 'Basic %s' % expected}


def test_basic_auth_uses_per_call_token():
    headers = build_auth_headers(_server(), token='crsr_override')
    expected = base64.b64encode(b'crsr_override:').decode('ascii')
    assert headers == {'Authorization': 'Basic %s' % expected}


def test_basic_auth_empty_token_returns_no_header():
    assert build_auth_headers(_server(auth_token='')) == {}
