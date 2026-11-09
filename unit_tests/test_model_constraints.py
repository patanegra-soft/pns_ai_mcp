# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Odoo 19 ignores ``_sql_constraints``: each one also exists as ``models.Constraint``."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_MODELS = sorted((ROOT / 'common' / 'models').glob('*.py'))


def _is_19_gate(node):
    return (
        isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and getattr(node.test.left, 'id', None) == 'ODOO_VERSION'
        and isinstance(node.test.ops[0], ast.GtE)
        and ast.literal_eval(node.test.comparators[0]) == 19
    )


def _assigned(stmts, name=None):
    for stmt in stmts:
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name) and (name is None or target.id == name):
                    yield target.id, stmt.value


def _classes(path):
    tree = ast.parse(path.read_text(encoding='utf-8'), str(path))
    return [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]


@pytest.mark.parametrize('path', _MODELS, ids=lambda p: p.name)
def test_no_sql_constraints_outside_the_pre_19_branch(path):
    for cls in _classes(path):
        assert not list(_assigned(cls.body, '_sql_constraints')), cls.name


@pytest.mark.parametrize('path', _MODELS, ids=lambda p: p.name)
def test_both_branches_declare_the_same_constraints(path):
    for cls in _classes(path):
        for gate in (stmt for stmt in cls.body if _is_19_gate(stmt)):
            old = [
                tuple(ast.literal_eval(value))
                for _name, rows in _assigned(gate.orelse, '_sql_constraints')
                for value in rows.elts
            ]
            new = {
                name.lstrip('_'): tuple(ast.literal_eval(arg) for arg in value.args)
                for name, value in _assigned(gate.body)
                if isinstance(value, ast.Call)
                and getattr(value.func, 'attr', None) == 'Constraint'
            }
            if not old and not new:
                continue
            assert {name: (sql, msg) for name, sql, msg in old} == new, cls.name
