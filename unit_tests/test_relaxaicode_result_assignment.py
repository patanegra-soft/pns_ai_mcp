# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""RelaxAICode: result assignment check must not false-positive on if/else + append."""
from __future__ import annotations

from _load_addon import load_module

v = load_module('validators', 'controllers', 'validators.py')


def _ok(code):
    good, err, _write = v.validate_relaxaicode_source_ast(code)
    assert good, err


def _fail(code, needle):
    good, err, _write = v.validate_relaxaicode_source_ast(code)
    assert not good
    assert needle in (err or '')


def test_if_else_both_assign_result_with_append_ok():
    """6HPL-4 style: if assigns dict; else builds list with result.append."""
    code = """
accounts = env['account.account'].search([])
if not accounts:
    result = {'formatted_text': 'empty'}
else:
    result = []
    for data in [{'codigo': '1'}]:
        result.append(data)
result
"""
    _ok(code)


def test_result_append_without_init_still_fails():
    _fail("""
result.append({'a': 1})
""", 'used before assignment')


def test_use_before_assign_still_fails():
    _fail("""
x = result
result = []
""", 'used before assignment')
