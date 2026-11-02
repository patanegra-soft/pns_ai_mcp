# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Carried domain packs: slashes never release them."""
from __future__ import annotations

from _load_addon import load_module

sd = load_module('slash_domain_codes', 'utils', 'slash_domain_codes.py')
fm = load_module('formatting_mode_policy', 'utils', 'formatting_mode_policy.py')


def test_parse_slash_bare_and_empty():
    assert sd.parse_slash_command('/') is None
    assert sd.parse_slash_command('') is None
    assert sd.parse_slash_command(None) is None
    assert sd.parse_slash_command('añade ytd') is None
    cmd, args = sd.parse_slash_command('/create-skill foo')
    assert cmd == 'create-skill'
    assert args == 'foo'


def test_mode_slashes_read_live_axis_commands():
    """Every key in AXIS_COMMANDS must not release. No copied name list."""
    assert fm.AXIS_COMMANDS, 'AXIS_COMMANDS vanished'
    for token in fm.AXIS_COMMANDS:
        assert sd.slash_releases_domain_codes(token) is False, token
        assert sd.slash_releases_domain_codes(
            token, skill_resolved=True,
        ) is False, token


def test_no_slash_releases_domain_codes():
    """Menu, CRUD, help, invoke: none wipe last_domain_codes."""
    for token in (
        'create-skill', 'delete-skill', 'rename-skill', 'edit-skill',
        'skills', 'help', '?', 'forecast', 'mode',
    ):
        assert sd.slash_releases_domain_codes(token) is False, token
        assert sd.slash_releases_domain_codes(
            token, skill_resolved=True,
        ) is False, token
    assert sd.slash_releases_domain_codes('') is False
    assert sd.slash_releases_domain_codes(None) is False
