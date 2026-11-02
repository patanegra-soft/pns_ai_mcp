# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Odoo's own export never carries a declared secret, not even through a relation."""
from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

_SRC = (
    Path(__file__).resolve().parents[1] / 'common' / 'models' / 'secret_native_export.py'
).read_text(encoding='utf-8')


def _names_a_secret():
    tree = ast.parse(_SRC)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'names_a_secret')
    scope = {}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), 'secret_native_export', 'exec'), scope)
    return scope['names_a_secret']


class _Model:
    def __init__(self, env, fields, secrets=()):
        self.env = env
        self._fields = fields
        self._pns_secret_fields = secrets


def _field(comodel=None):
    return SimpleNamespace(relational=bool(comodel), comodel_name=comodel)


def _env():
    env = {}
    env['ai.provider'] = _Model(env, {'name': _field(), 'api_key': _field()}, ('api_key',))
    env['ai.agent'] = _Model(env, {'name': _field(), 'provider_id': _field('ai.provider')})
    return env


def test_a_declared_secret_is_named_directly_or_through_a_relation():
    names_a_secret = _names_a_secret()
    env = _env()
    assert names_a_secret(env['ai.provider'], 'api_key')
    assert names_a_secret(env['ai.agent'], 'provider_id/api_key')
    assert not names_a_secret(env['ai.provider'], 'name')
    assert not names_a_secret(env['ai.agent'], 'provider_id/name')
    assert not names_a_secret(env['ai.agent'], 'provider_id/.id')
    assert not names_a_secret(env['ai.agent'], 'id')
    assert not names_a_secret(env['ai.agent'], '')


def test_the_column_comes_out_empty():
    assert "_inherit = 'base'" in _SRC
    assert 'def export_data(self, fields_to_export):' in _SRC
    assert "row[i] = ''" in _SRC
    init = (Path(__file__).resolve().parents[1] / 'common' / 'models' / '__init__.py').read_text(
        encoding='utf-8')
    assert 'from . import secret_native_export' in init
