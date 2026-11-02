# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""The AI never reads a credential: temporary PIN, MCP key handoff.

The sandbox runs as the asking user. For an AI admin that user may read
``ai.mcp.user``, so the PIN digits would be one ``search`` away. These models
are closed at review (AST) and at run (``GuardedSandboxEnv``), and so is any
model of this addon with a relation that leads to one of them. A row that only
carries a secret column (a provider key) stays open; the column is shut on its
own (``test_sandbox_secret_columns.py``).
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from _load_addon import load_module

v_checks = load_module('validators_checks', 'controllers', 'validators_checks.py')
v_base = load_module('validators_base', 'controllers', 'validators_base.py')
cb = load_module('context_builder', 'controllers', 'context_builder.py')

_COMMON = Path(__file__).resolve().parents[1] / 'common'
_CLOSED = v_base.RELAXAICODE_CREDENTIAL_MODELS
_CLOSED_ALL = _CLOSED | {
    v_base.RELAXAICODE_FORBIDDEN_API_SERVER_MODEL,
    v_base.RELAXAICODE_FORBIDDEN_CONTEXT_MODEL,
    v_base.RELAXAICODE_FORBIDDEN_SKILL_MODEL,
}
_RELATIONS = ('Many2one', 'One2many', 'Many2many')


def test_review_rejects_every_credential_model():
    for model in sorted(_CLOSED):
        tree = ast.parse("result = env['%s'].search([]).mapped('key_pin')" % model)
        err = v_checks._detect_external_api_bypass_from_ast(tree)
        assert err and 'CREDENTIALS' in err, model


def test_run_rejects_every_credential_model():
    class _Env(object):
        def __getitem__(self, model):
            return model

    wrapped = cb.GuardedSandboxEnv(_Env())
    assert wrapped['res.partner'] == 'res.partner'
    for model in sorted(_CLOSED):
        with pytest.raises(KeyError):
            wrapped[model]
        with pytest.raises(KeyError):
            wrapped.get(model)


def _model_names(cls):
    """The model a class registers: ``_name``, else a plain ``_inherit``."""
    name = inherit = None
    for stmt in cls.body:
        if not isinstance(stmt, ast.Assign):
            continue
        target = stmt.targets[0]
        if not isinstance(target, ast.Name):
            continue
        if target.id == '_name':
            name = ast.literal_eval(stmt.value)
        elif target.id == '_inherit':
            inherit = ast.literal_eval(stmt.value)
    if name:
        return [name] if isinstance(name, str) else list(name)
    if isinstance(inherit, str):
        return [inherit]
    return []


def _comodel(call):
    for kw in call.keywords:
        if kw.arg == 'comodel_name':
            return ast.literal_eval(kw.value)
    if call.args:
        try:
            return ast.literal_eval(call.args[0])
        except ValueError:
            return None
    return None


def _relations_into_closed():
    found = []
    for path in sorted(_COMMON.rglob('*.py')):
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
            owners = _model_names(cls)
            for call in (n for n in ast.walk(cls) if isinstance(n, ast.Call)):
                func = call.func
                if not (isinstance(func, ast.Attribute) and func.attr in _RELATIONS):
                    continue
                if _comodel(call) in _CLOSED:
                    found.append((path.name, owners))
    return found


def test_no_open_model_leads_to_a_credential():
    found = _relations_into_closed()
    assert found
    for filename, owners in found:
        assert owners and set(owners) <= _CLOSED_ALL, (filename, owners)
