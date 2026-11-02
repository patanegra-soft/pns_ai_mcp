# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""What the engine writes to the model is English; the user's Locale comes from the packs."""
import ast
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SPANISH_LETTERS = set('áéíóúñÁÉÍÓÚÑ¿¡')


def _docstrings(tree):
    nodes = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    for node in ast.walk(tree):
        if isinstance(node, nodes) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                yield id(first.value)


def test_engine_prompts_are_english():
    found = []
    for path in sorted((_ROOT / 'common' / 'utils').glob('*engine*.py')):
        tree = ast.parse(path.read_text(encoding='utf-8'))
        docs = set(_docstrings(tree))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                    and id(node) not in docs and _SPANISH_LETTERS & set(node.value)):
                found.append('%s:%s %r' % (path.name, node.lineno, node.value[:60]))
    assert found == []
