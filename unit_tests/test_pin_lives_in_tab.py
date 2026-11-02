# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Temporary PIN: minted by the tab holding the keys, never stored server-side.

The desk tab generates one PIN per key when the list is loaded, answers PIN
asks from its own map, and drops a PIN when the server says it was spent.
The server only matches the supplied key to a user by its hash.
"""
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_MCP_USER = (_ROOT / 'common' / 'models' / 'mcp_user.py').read_text(encoding='utf-8')
_DESK = (_ROOT / 'common' / 'models' / 'key_pin_desk.py').read_text(encoding='utf-8')
_FOSSILS = (_ROOT / 'common' / 'utils' / 'schema_fossils.py').read_text(encoding='utf-8')
_OWL2 = (_ROOT / 'stacks' / 'owl2' / 'pns_ai_mcp' / 'static' / 'src' / 'js'
         / 'key_pin_desk.js').read_text(encoding='utf-8')
_OWL1 = (_ROOT / 'stacks' / 'owl1' / 'pns_ai_mcp' / 'static' / 'src' / 'js'
         / 'key_pin_desk_v14.js').read_text(encoding='utf-8')
_TREE1 = (_ROOT / 'stacks' / 'owl1' / 'pns_ai_mcp' / 'static' / 'src' / 'js'
          / 'mcp_user_tree_v14.js').read_text(encoding='utf-8')


def test_redeem_asks_the_tab_and_matches_by_hash():
    assert '_collect_pin(raw)' in _MCP_USER
    assert "('mcp_api_key_hash', '=', hash_api_key(got))" in _MCP_USER
    assert "('key_pin', '=', raw)" not in _MCP_USER


def test_ask_carries_pin_and_counts_refusals():
    assert 'pin = fields.Char' in _DESK
    assert 'refused = fields.Integer' in _DESK
    assert 'def _collect_pin' in _DESK
    assert "'refused': (ask.refused or 0) + 1" in _DESK
    assert 'def _notify_pin_spent' in _DESK
    assert "'pin_length': pin_length(self.env)" in _DESK
    # A key that arrives after the wait has nowhere to land.
    assert 'if final:' in _DESK


def test_both_tabs_mint_and_drop_pins():
    for js in (_OWL1, _OWL2):
        assert 'pns.key.pin.pins' in js
        assert 'ensurePins' in js
        assert 'dropPin' in js
        assert 'sessionStorage.removeItem(PINS)' in js
    assert 'isPinButton' not in _TREE1


def test_leftover_pin_columns_are_dropped():
    for column in ('key_pin', 'key_pin_used', 'key_pin_killed'):
        assert "('ai_mcp_user', '%s')," % column in _FOSSILS


def test_pin_desk_boots_only_for_ai_admin():
    http = (_ROOT / 'common' / 'models' / 'ir_http.py').read_text(encoding='utf-8')
    assert "info['pns_is_ai_admin']" in http
    assert "group_ai_admin" in http
    for js in (_OWL1, _OWL2):
        assert 'pns_is_ai_admin' in js
        assert 'function bindDeskClicks' in js or 'function bindDeskClicks()' in js
