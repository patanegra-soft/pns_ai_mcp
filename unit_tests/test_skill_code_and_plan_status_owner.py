# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Saving a skill leaves nothing behind; safe_plan_status only sees and runs the caller's plan."""
from __future__ import annotations

from pathlib import Path

from _load_addon import load_module, runtime_source, safe_plan_source, skill_source

_ROOT = Path(__file__).resolve().parents[1]
_COMMON = _ROOT / 'common'
_SKILL = skill_source()
_RUNTIME = runtime_source()
_WIZARD = (_COMMON / 'wizard' / 'skill_capture_wizard.py').read_text(encoding='utf-8')
_PLAN = safe_plan_source()


def _validators():
    return load_module('validators', 'controllers', 'validators.py')


def _body(src, name):
    return src.split('def %s(' % name, 1)[1].split('\ndef ', 1)[0]


def test_a_skill_that_writes_is_marked_by_the_validator():
    _good, _err, writes = _validators().validate_relaxaicode_source_ast(
        "env['res.partner'].search([], limit=1).write({'name': 'x'})\n"
        "result = {'data': []}\n"
    )
    assert writes


def test_the_refusal_is_checked_on_save_and_on_every_run():
    refusal = _body(_RUNTIME, 'skill_code_refusal')
    assert 'validate_relaxaicode_source_ast' in refusal
    assert 'if writes:' in refusal
    boot = _body(_RUNTIME, 'bootstrap_skill_code_body')
    assert boot.index('skill_code_refusal') < boot.index('exec(')
    check = _SKILL.split('def _check_code_body_contract', 1)[1].split('\n    def ', 1)[0]
    assert 'skill_code_refusal' in check
    assert '_requires_write' not in check


def test_the_save_time_run_is_always_rolled_back():
    check = _SKILL.split('def _check_code_body_contract', 1)[1].split('\n    def _run_and_undo', 1)[0]
    assert 'self._run_and_undo(_smoke)' in check
    assert check.index('bootstrap_skill_code_body(') > check.index('def _smoke')
    assert 'skill_publish_check=True' in check
    publish = _body(_RUNTIME, 'check_skill_fast_path_publishable')
    assert 'skill_publish_check=True' in publish
    assert "vals['compose'] = fixed_compose" in _WIZARD
    assert check.index('check_skill_fast_path_publishable(') > check.index('def _smoke')
    undo = _SKILL.split('def _run_and_undo', 1)[1].split('\n    def ', 1)[0]
    assert 'savepoint()' in undo
    assert 'raise _RunUndone()' in undo
    assert '_run_and_undo(' in _WIZARD


def test_the_publish_check_does_not_create_a_pending_operation():
    check = _body(_RUNTIME, 'check_skill_fast_path_publishable')
    assert 'probe=True' in check
    fast = _body(_RUNTIME, 'try_skill_fast_path')
    assert fast.index('if probe:') < fast.index('request_safe_plan(')


def test_safe_plan_status_finds_and_runs_only_the_callers_plan():
    tool = _body(_PLAN, 'tool_safe_plan_status')
    assert "owned = [('user_id', '=', env.uid)]" in tool
    assert "[('verification_id', '=', verification_id)] + owned" in tool
    assert "env['ai.safe.operation'].browse(verif.id).execute_plan_now()" in tool
    assert 'verif.execute_plan_now()' not in tool
