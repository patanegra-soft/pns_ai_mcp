# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Closing the key desk is a state change: it requires the CSRF token.

Both tab scripts send the token in the beacon URL (a beacon cannot set
headers), and the Odoo 14 desk token comes from crypto, not from the clock.
"""
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_CTRL = (_ROOT / 'common' / 'controllers' / 'key_pin.py').read_text(encoding='utf-8')
_OWL2 = (_ROOT / 'stacks' / 'owl2' / 'pns_ai_mcp' / 'static' / 'src' / 'js'
         / 'key_pin_desk.js').read_text(encoding='utf-8')
_OWL1 = (_ROOT / 'stacks' / 'owl1' / 'pns_ai_mcp' / 'static' / 'src' / 'js'
         / 'key_pin_desk_v14.js').read_text(encoding='utf-8')


def test_stop_route_requires_csrf():
    assert 'csrf=False' not in _CTRL
    assert "'/pns_ai_mcp/key_pin/stop'" in _CTRL


def test_both_tabs_send_the_csrf_token():
    for js in (_OWL1, _OWL2):
        assert '/pns_ai_mcp/key_pin/stop?csrf_token=' in js
        assert 'odoo.csrf_token' in js
        assert 'sendBeacon(\n                "/pns_ai_mcp/key_pin/stop"' not in js
        assert "sendBeacon(\n            '/pns_ai_mcp/key_pin/stop'" not in js


def test_owl1_desk_token_uses_crypto():
    assert 'function deskToken()' in _OWL1
    assert 'crypto.getRandomValues' in _OWL1
    assert 'value = String(Date.now())' not in _OWL1
