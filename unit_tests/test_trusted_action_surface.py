# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""ai.trusted.action dispatches to sudo methods: nothing of it is callable by RPC."""
from __future__ import annotations

import ast
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SRC = (_ROOT / 'common' / 'models' / 'ai_trusted_action.py').read_text(
    encoding='utf-8')


def _methods():
    tree = ast.parse(_SRC)
    cls = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef)
        and any(
            isinstance(stmt, ast.Assign)
            and any(getattr(t, 'id', None) == '_name' for t in stmt.targets)
            for stmt in node.body
        )
    )
    return {
        node.name: node for node in cls.body
        if isinstance(node, ast.FunctionDef)
    }


def test_no_public_method_reaches_the_dispatcher():
    methods = _methods()
    callers = {
        name for name, node in methods.items()
        if not name.startswith('_')
        and '_resolve_method' in ast.unparse(node)
    }
    assert not callers, callers


def test_apply_checks_the_group_where_the_work_is_done():
    body = ast.unparse(_methods()['_apply'])
    assert body.index('user_has_required_groups') < body.index('_resolve_method')
