# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""module.update runs as the real user and never takes the engine down with it."""
from __future__ import annotations

from pathlib import Path
from _load_addon import safe_plan_source

_ROOT = Path(__file__).resolve().parents[1]
_SRC = (_ROOT / 'common' / 'models' / 'ai_system_action.py').read_text(encoding='utf-8')
_PLAN = safe_plan_source()


def _method(name):
    start = _SRC.index('def %s(' % name)
    return _SRC[start:_SRC.index('\n    def ', start + 10)]


def test_no_handwritten_list_of_protected_modules():
    assert '_CORE_UNINSTALL_BLOCK' not in _SRC


def test_the_cascade_is_asked_to_odoo():
    body = _method('_uninstall_cascade')
    assert 'downstream_dependencies(' in body
    assert 'if _XMLID_MODULE in names:' in body


def test_apply_runs_the_button_as_the_real_user():
    body = _method('_apply_module_update')
    assert 'with_user(self.env.uid).browse(_mid)' in body
    assert "self.env['ir.module.module'].sudo().browse(_mid)" not in body
    assert body.index('_uninstall_cascade(') < body.index('method()')


def test_propose_and_execute_reject_a_mixed_module_update():
    validate = _PLAN[_PLAN.index('def validate_safe_plan'):_PLAN.index('def compute_danger_level')]
    execute = _PLAN[_PLAN.index('def execute_safe_plan'):_PLAN.index('def _journal_snapshot')]
    assert 'module_update_alone_error' in validate
    assert 'module_update_alone_error' in execute


def test_preview_names_what_else_goes():
    body = _method('_preview_module_update')
    assert '_uninstall_cascade(mod)' in body
    assert "'Also uninstalls: %s'" in body
