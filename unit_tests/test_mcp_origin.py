# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Origin check on /mcp (PNS-28).

No Origin (desktop clients) always passes. A browser Origin passes only
when it is the instance itself or listed by an admin. Responses echo the
caller's Origin instead of '*'.
"""
from pathlib import Path

from _load_addon import load_module

o = load_module('mcp_origin', 'utils', 'mcp_origin.py')
_MAIN = (Path(__file__).resolve().parents[1] / 'common' / 'controllers'
         / 'main.py').read_text(encoding='utf-8')


def test_no_origin_always_passes():
    assert o.origin_allowed(None, '', '')
    assert o.origin_allowed('', '', '')
    assert o.origin_allowed('   ', '', '')


def test_instance_origin_passes():
    assert o.origin_allowed(
        'https://odoo.example.com', '', 'https://odoo.example.com/some/path')
    assert o.origin_allowed(
        'https://odoo.example.com/', '', 'https://odoo.example.com')


def test_listed_origin_passes_others_do_not():
    allowed = 'https://app.example.com\nhttps://other.example.com, https://x.io'
    assert o.origin_allowed('https://app.example.com', allowed, '')
    assert o.origin_allowed('https://x.io/', allowed, '')
    assert not o.origin_allowed('https://evil.example.com', allowed, '')
    assert not o.origin_allowed('https://evil.example.com', '', '')
    assert not o.origin_allowed('null', '', 'https://odoo.example.com')


def test_controller_rejects_and_echoes():
    assert '_mcp_origin_ok' in _MAIN
    assert "'Origin not allowed'" in _MAIN
    assert "['Access-Control-Allow-Origin'] = '*'" not in _MAIN
    assert "['Access-Control-Allow-Origin'] = self._mcp_cors_origin()" in _MAIN
    # The four entry points check before doing any work.
    assert _MAIN.count('if not self._mcp_origin_ok():') >= 5
