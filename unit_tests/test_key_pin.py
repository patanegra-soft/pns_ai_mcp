# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Temporary key PIN: digit shape and the per-IP budget."""
from __future__ import annotations

from pathlib import Path

from _load_addon import load_module

p = load_module('key_pin', 'utils', 'key_pin.py')
_ROOT = Path(__file__).resolve().parents[1]
_MCP_USER = (
    _ROOT / 'common' / 'models' / 'mcp_user.py'
).read_text(encoding='utf-8')


def test_pin_shaped_is_exact_digits():
    assert p.pin_shaped('12345678', 8)
    assert not p.pin_shaped('1234567', 8)
    assert not p.pin_shaped('12345678a', 8)
    assert not p.pin_shaped('abcdefgh', 8)


def test_one_past_the_budget_starts_the_block():
    assert not p.failure_starts_block(100, 100)
    assert p.failure_starts_block(101, 100)


def test_spaced_groups_are_the_same_pin():
    assert p.compact_pin('1234 5678', 8) == '12345678'
    assert p.compact_pin('12345678', 8) == '12345678'
    assert p.compact_pin('abcd-efgh-ijkl', 8) == 'abcd-efgh-ijkl'


def test_length_out_of_range_stays_eight():
    assert p.clamp_pin_length('') == 8
    assert p.clamp_pin_length(3) == 8
    assert p.clamp_pin_length(8) == 8
    assert p.clamp_pin_length(12) == 12


def test_pin_is_never_stored_on_the_user():
    """The PIN lives in the browser tab holding the key list, not in a field."""
    assert 'key_pin = fields.Char' not in _MCP_USER
    assert 'key_pin_html' not in _MCP_USER
    assert 'def _issue_key_pin' not in _MCP_USER
    assert 'def action_key_pin_regenerate' not in _MCP_USER
    assert "('key_pin', '=', raw)" not in _MCP_USER
    assert '_collect_pin(raw)' in _MCP_USER
    for stack in ('owl1', 'owl2'):
        views = (
            _ROOT / 'stacks' / stack / 'pns_ai_mcp' / 'views'
            / 'mcp_user_views.xml'
        ).read_text(encoding='utf-8')
        assert 'key_pin_html' not in views
        assert 'action_key_pin_regenerate' not in views
        assert 'clear_key_pin' not in views
