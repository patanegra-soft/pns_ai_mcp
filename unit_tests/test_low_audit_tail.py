# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Source checks for the remaining low audit items that live in this module."""
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _text(*parts):
    return (_ROOT.joinpath(*parts)).read_text(encoding='utf-8')


def test_shown_fields_do_not_reuse_the_stored_labels():
    src = _text('common', 'models', 'ai_agent.py')
    assert "string='Contexts on the form'" in src
    assert "string='Skills on the form'" in src
    assert src.count("string='Contexts'") == 1
    assert src.count("string='Skills'") == 1


def test_fx_failure_is_cached_for_a_short_window():
    src = _text('common', 'models', 'ai_fx_source.py')
    assert '_FAIL_CACHE_MINUTES = 15' in src
    assert 'retry_after' in src
    assert '_failure_still_fresh' in src


def test_mcp_key_write_clears_the_menu_cache():
    src = _text('common', 'models', 'mcp_user.py')
    assert 'def _forget_app_menu_cache' in src
    assert "clear_caches()" in src
    assert src.count('_forget_app_menu_cache()') >= 2


def test_factory_agent_drops_the_old_acl_security_token_once():
    src = _text('common', 'models', 'ai_agent.py')
    assert 'def _drop_acl_security_factory_fossil' in src
    assert "'%s.fossil_acl_security_agent' % agent.code" in src
    assert "('origin', '=', 'module')" in src.split(
        'def _drop_acl_security_factory_fossil', 1)[1].split('\n    @', 1)[0]


def test_settings_menu_matches_who_can_open_it():
    for stack in ('owl1', 'owl2'):
        src = _text(
            'stacks', stack, 'pns_ai_mcp', 'views',
            'res_config_settings_views.xml',
        )
        assert 'id="menu_mcp_settings"' in src
        assert 'groups="base.group_system"' in src


def test_skill_zip_actions_are_not_bound_twice():
    for stack in ('owl1', 'owl2'):
        menus = _text('stacks', stack, 'pns_ai_mcp', 'views', 'ai_menus.xml')
        start = menus.index('id="action_server_export_selected_skills"')
        chunk = menus[start:start + 500]
        assert 'binding_model_id" eval="False"' in chunk
