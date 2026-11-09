# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Odoo 14 runs on Python 3.7: what the newer interpreters accept and 3.7 does not."""
from __future__ import annotations

import ast
import importlib.util
import re
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_SHIPPED = [
    p for p in sorted((ROOT / 'common').rglob('*.py')) + sorted((ROOT / 'stacks').rglob('*.py'))
    if '__pycache__' not in p.parts
]
_BUILTIN_GENERIC = re.compile(r'(->|:)\s*(tuple|list|dict|set|frozenset|type)\[')


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize('path', _SHIPPED, ids=lambda p: str(p.relative_to(ROOT)))
def test_parses_as_python37(path):
    ast.parse(path.read_text(encoding='utf-8'), str(path), feature_version=(3, 7))


@pytest.mark.parametrize('path', _SHIPPED, ids=lambda p: str(p.relative_to(ROOT)))
def test_no_builtin_generic_annotation_without_future_import(path):
    """``-> tuple[bool, str]`` is evaluated at import time and fails before 3.9."""
    src = path.read_text(encoding='utf-8')
    if 'from __future__ import annotations' in src:
        return
    assert not _BUILTIN_GENERIC.search(src)


@pytest.mark.parametrize('path', _SHIPPED, ids=lambda p: str(p.relative_to(ROOT)))
def test_no_bare_38_ast_helpers(path):
    src = path.read_text(encoding='utf-8')
    assert 'ast.get_source_segment(' not in src


def _old_node(kind, **fields):
    """The literal nodes Python 3.7 builds: Str(s), Num(n), NameConstant(value), Bytes(s)."""
    cls = type(kind, (ast.expr,), {'_fields': tuple(fields)})
    node = cls()
    for key, value in fields.items():
        setattr(node, key, value)
    return node


@pytest.mark.parametrize('node, value', [
    (_old_node('Str', s='a'), 'a'),
    (_old_node('Num', n=3), 3),
    (_old_node('NameConstant', value=None), None),
    (_old_node('NameConstant', value=True), True),
    (_old_node('Bytes', s=b'x'), b'x'),
    (ast.Constant(value='a'), 'a'),
])
def test_ast_literal_reads_37_and_38_nodes(node, value):
    validators_base = _load('pns_validators_base_37', 'common/controllers/validators_base.py')
    assert validators_base.ast_literal(node) == (True, value)


def test_ast_literal_rejects_a_name():
    validators_base = _load('pns_validators_base_37', 'common/controllers/validators_base.py')
    assert validators_base.ast_literal(ast.Name(id='x', ctx=ast.Load())) == (False, None)


@pytest.mark.parametrize('path', _SHIPPED, ids=lambda p: str(p.relative_to(ROOT)))
def test_no_literal_check_against_constant_alone(path):
    """``isinstance(node, ast.Constant)`` is False for every literal on 3.7."""
    src = path.read_text(encoding='utf-8')
    assert not re.search(r',\s*ast\.Constant\s*\)', src)


@pytest.mark.parametrize('path', _SHIPPED, ids=lambda p: str(p.relative_to(ROOT)))
def test_no_37_literal_class_by_attribute(path):
    """``ast.Str`` / ``ast.Num``… are gone in 3.14; tell them apart by type name."""
    src = path.read_text(encoding='utf-8')
    assert not re.search(r'\bast\.(Str|Num|Bytes|NameConstant)\b', src)


def test_recipe_keeps_none_in_pasted_rows():
    recipe = _load('pns_recipe_37', 'common/utils/relaxaicode_recipe.py')
    node = ast.parse("[None, 1, {None: 2, 'a': None}]", mode='eval').body
    assert recipe._try_eval_data_node(node) == [None, 1, {None: 2, 'a': None}]
    node = ast.parse("[None, x]", mode='eval').body
    assert recipe._try_eval_data_node(node) is None


def test_recipe_coercion_without_get_source_segment(monkeypatch):
    recipe = _load('pns_recipe_37', 'common/utils/relaxaicode_recipe.py')
    monkeypatch.delattr(ast, 'get_source_segment', raising=False)
    code = (
        "def ventas(date_from, date_to):\n"
        "    return date_from.isoformat()\n\n"
        "result = ventas('2026-01-01', '2026-01-31')\n"
    )
    out, changed = recipe.ensure_date_param_coercion(code)
    assert changed
    assert recipe.ensure_date_param_coercion(out) == (out, False)
    import datetime
    scope = {'date': datetime.date, 'datetime': datetime.datetime, 'types': types}
    exec(out, scope)
    assert scope['result'] == '2026-01-01'
