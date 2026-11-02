# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""A method split out of another must not keep a counter it left behind.

``x += 1`` on a name the function never binds raises UnboundLocalError at
run time. The tool loop caught it, so every good relaxaicode call came back
to the model as an error and the turn lost its rows and its download (P0ZP).
"""
from __future__ import annotations

import ast
from pathlib import Path

_COMMON = Path(__file__).resolve().parents[1] / 'common'


def _bound(fn):
    names = set()
    for n in ast.walk(fn):
        if isinstance(n, ast.arg):
            names.add(n.arg)
        elif isinstance(n, (ast.Global, ast.Nonlocal)):
            names |= set(n.names)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            names |= {(a.asname or a.name).split('.')[0] for a in n.names}
        elif isinstance(n, ast.ExceptHandler) and n.name:
            names.add(n.name)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n is not fn:
            names.add(n.name)
        else:
            targets = []
            if isinstance(n, ast.Assign):
                targets = n.targets
            elif isinstance(n, (ast.AnnAssign, ast.NamedExpr, ast.For, ast.comprehension)):
                targets = [n.target]
            elif isinstance(n, ast.With):
                targets = [i.optional_vars for i in n.items if i.optional_vars]
            for t in targets:
                names |= {m.id for m in ast.walk(t) if isinstance(m, ast.Name)}
    return names


def _functions(tree):
    out = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    for c in tree.body:
        if isinstance(c, ast.ClassDef):
            out += [n for n in c.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    return out


def test_no_counter_is_augmented_without_a_binding():
    bad = []
    for path in sorted(_COMMON.rglob('*.py')):
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for fn in _functions(tree):
            bound = _bound(fn)
            for n in ast.walk(fn):
                if (
                    isinstance(n, ast.AugAssign)
                    and isinstance(n.target, ast.Name)
                    and n.target.id not in bound
                ):
                    bad.append('%s:%d %s in %s' % (
                        path.relative_to(_COMMON), n.lineno, n.target.id, fn.name,
                    ))
    assert not bad, bad


def test_the_check_sees_a_left_behind_counter():
    tree = ast.parse(
        'class M:\n'
        '    def run(self):\n'
        '        hits = 0\n'
        '    def step(self):\n'
        '        hits += 1\n'
    )
    run, step = _functions(tree)
    assert 'hits' in _bound(run)
    assert 'hits' not in _bound(step)
