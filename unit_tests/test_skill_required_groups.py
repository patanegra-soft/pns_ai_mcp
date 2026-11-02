# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Skills may require groups (PNS-66): hidden and unrunnable without one.

The check runs where skills are listed (list_for_agent) and where a slash
or an NL trigger resolves (engine).
"""
import ast
from pathlib import Path
from _load_addon import skill_source

_ROOT = Path(__file__).resolve().parents[1]
_SKILL = skill_source()
_ENGINE = (_ROOT / 'common' / 'utils' / 'engine_skills.py').read_text(encoding='utf-8')

def _load_method(name):
    tree = ast.parse(_SKILL)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            module = ast.Module(body=[node], type_ignores=[])
            ns = {}
            exec(compile(module, 'ai_skill.py', 'exec'), ns)
            return ns[name]
    raise AssertionError(name + ' missing')


class _Groups:
    def __init__(self, ids):
        self.ids = ids

    def __bool__(self):
        return bool(self.ids)


class _User:
    def __init__(self, group_ids):
        self.groups_id = _Groups(group_ids)


class _Env:
    def __init__(self, user):
        self.user = user


class _Skill:
    def __init__(self, group_ids, user):
        self.required_group_ids = _Groups(group_ids)
        self.env = _Env(user)

    def ensure_one(self):
        return True


def test_user_may_run():
    fn = _load_method('user_may_run')
    plain = _User([1, 2])
    admin = _User([1, 2, 99])
    assert fn(_Skill([], plain)) is True
    assert fn(_Skill([99], plain)) is False
    assert fn(_Skill([99], admin)) is True
    assert fn(_Skill([98, 99], admin)) is True


def test_field_and_filters_exist():
    assert "required_group_ids = fields.Many2many(" in _SKILL
    assert 's.user_may_run()' in _SKILL.split('def list_for_agent', 1)[1].split(
        'def user_can_author_skills', 1)[0]
    assert _ENGINE.count('s.user_may_run()') >= 2
    assert '_required_groups_from_meta' in _SKILL
    assert "'required_groups' in meta" in _SKILL
