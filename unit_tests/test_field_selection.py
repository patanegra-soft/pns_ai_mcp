# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Resolver Selection: lista vs callable, sin runtime Odoo ni dominio."""
from __future__ import annotations

import unittest

from _load_addon import load_module

mod = load_module('pns_ai_mcp_field_selection', 'utils', 'field_selection.py')
resolve_field_selection = mod.resolve_field_selection
format_selection_iterable_hint = mod.format_selection_iterable_hint

_LIST = [('draft', 'Draft'), ('done', 'Done')]


class _Field(object):
    def __init__(self, selection, with_desc=True):
        self.selection = selection
        self.type = 'selection'
        if with_desc:
            self._description_selection = self._resolve

    def _resolve(self, env):
        sel = self.selection
        if callable(sel):
            return sel(None)
        return sel


class _Model(object):
    _name = 'dummy.model'

    def __init__(self, fields, field_get=None):
        self._fields = fields
        self._field_get = field_get

    def fields_get(self, allfields=None, attributes=None):
        if self._field_get is not None:
            return self._field_get
        out = {}
        for key in allfields or self._fields:
            field = self._fields.get(key)
            if field is None:
                continue
            sel = field.selection
            if callable(sel):
                sel = sel(None)
            out[key] = {'selection': sel}
        return out


class _Env(object):
    def __init__(self, models):
        self._models = models

    def __contains__(self, name):
        return name in self._models

    def __getitem__(self, name):
        return self._models[name]


class TestResolveFieldSelection(unittest.TestCase):
    def test_list_selection(self):
        model = _Model({'state': _Field(_LIST)})
        env = _Env({'dummy.model': model})
        self.assertEqual(
            resolve_field_selection(env, 'dummy.model', 'state'),
            _LIST,
        )

    def test_callable_selection(self):
        model = _Model({'state': _Field(lambda _rec: list(_LIST))})
        env = _Env({'dummy.model': model})
        self.assertEqual(
            resolve_field_selection(env, 'dummy.model', 'state'),
            _LIST,
        )

    def test_recordset_model_arg(self):
        model = _Model({'state': _Field(_LIST)})
        env = _Env({'dummy.model': model})
        self.assertEqual(
            resolve_field_selection(env, model, 'state'),
            _LIST,
        )

    def test_fields_get_fallback_without_description(self):
        field = _Field(lambda _rec: list(_LIST), with_desc=False)
        model = _Model({'state': field})
        env = _Env({'dummy.model': model})
        self.assertEqual(
            resolve_field_selection(env, 'dummy.model', 'state'),
            _LIST,
        )

    def test_unknown_model_is_keyerror(self):
        env = _Env({})
        with self.assertRaises(KeyError) as ctx:
            resolve_field_selection(env, 'missing.model', 'state')
        self.assertEqual(ctx.exception.args[0], 'missing.model')

    def test_unknown_field_is_valueerror(self):
        model = _Model({})
        env = _Env({'dummy.model': model})
        with self.assertRaises(ValueError):
            resolve_field_selection(env, 'dummy.model', 'nope')

    def test_callable_without_resolver_raises_typed_hint(self):
        field = _Field(lambda _rec: list(_LIST), with_desc=False)
        model = _Model({'state': field}, field_get={})
        env = _Env({'dummy.model': model})
        with self.assertRaises(TypeError) as ctx:
            resolve_field_selection(env, 'dummy.model', 'state')
        self.assertIn('field_selection', str(ctx.exception))


class TestSelectionIterableHint(unittest.TestCase):
    def test_function_not_iterable(self):
        hint = format_selection_iterable_hint(
            "'function' object is not iterable"
        )
        self.assertIsNotNone(hint)
        self.assertIn('field_selection(model, name)', hint)
        self.assertIn('list(field.selection)', hint)

    def test_unrelated_typeerror_untouched(self):
        self.assertIsNone(
            format_selection_iterable_hint("'NoneType' object is not iterable")
        )
        self.assertIsNone(format_selection_iterable_hint('bad operand type'))


if __name__ == '__main__':
    unittest.main()
