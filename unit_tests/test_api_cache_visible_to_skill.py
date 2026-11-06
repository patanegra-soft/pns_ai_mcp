# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""A skill reads the api_call cache from box A, so the row must be committed.

Box A is a read-only cursor of its own: it does not see what the turn's cursor
has not committed. If the row lived only there, a multi-round skill would not
find its own calls and ask for them again until the rounds ran out.
"""
from __future__ import annotations

import ast

from _load_addon import addon_file


def _method(name):
    tree = ast.parse(addon_file('models', 'api_result_cache.py').read_text(encoding='utf-8'))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(name)


def test_store_writes_on_its_own_committed_cursor():
    store = _method('_store')
    withs = [n for n in ast.walk(store) if isinstance(n, ast.With)]
    assert any('registry.cursor()' in ast.unparse(item.context_expr) for w in withs for item in w.items)
    for call in ast.walk(store):
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) and call.func.attr in ('create', 'write'):
            assert any(call in ast.walk(w) for w in withs), ast.unparse(call)


def test_skill_box_is_a_cursor_of_its_own():
    src = addon_file('utils', 'skill_runtime.py').read_text(encoding='utf-8')
    assert 'open_readonly_env(env)' in src
