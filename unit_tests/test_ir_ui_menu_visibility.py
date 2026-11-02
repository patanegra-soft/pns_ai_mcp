# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""AI Engine drawer follows IA groups, not the MCP API key carnet."""
from __future__ import annotations

from _load_addon import addon_file


def _src():
    return addon_file('models', 'ir_ui_menu.py').read_text(encoding='utf-8')


def test_carnet_does_not_inject_ai_engine_menus():
    src = _src()
    assert '_MCP_API_KEY_MENU_XMLIDS' not in src
    assert 'user_has_mcp_api_key' not in src
    assert "'pns_ai_mcp.menu_mcp_main'" not in src


def test_admin_still_hides_operator_menus():
    src = _src()
    assert 'menu_ai_log' in src
    assert 'group_ai_admin' in src
    assert '_OPERATOR_MENU_XMLIDS' in src


def test_changes_menu_hidden_from_non_admin():
    src = _src()
    assert 'menu_ai_change_journal' in src
    assert '_ADMIN_ONLY_MENU_XMLIDS' in src
