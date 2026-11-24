# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Model discovery from the registry, without Odoo: any user, any series."""
from __future__ import annotations

import unittest

from _load_addon import load_module

mod = load_module('pns_ai_mcp_model_discovery', 'utils', 'model_discovery.py')
find_models = mod.find_models
model_module = mod.model_module
can_read_model = mod.can_read_model


class _Model18(object):
    """Odoo 18+: has_access."""

    def __init__(self, name, description, module, readable=True, abstract=False):
        self._name = name
        self._description = description
        self._original_module = module
        self._abstract = abstract
        self._readable = readable

    def has_access(self, operation):
        return self._readable


class _Model14(object):
    """Odoo 14–17: check_access_rights, no has_access."""

    def __init__(self, name, description, module, readable=True):
        self._name = name
        self._description = description
        self._original_module = module
        self._abstract = False
        self._readable = readable

    def check_access_rights(self, operation, raise_exception=True):
        return self._readable


class _ModuleRec(object):
    def __init__(self, shortdesc, summary, description):
        self.shortdesc = shortdesc
        self.summary = summary
        self.description = description

    def __bool__(self):
        return True


class _ModuleModel(object):
    def __init__(self, sheets):
        self._sheets = sheets
        self.sudo_called = False
        self.domains = []

    def sudo(self):
        self.sudo_called = True
        return self

    def search(self, domain, limit=None):
        self.domains.append(domain)
        name = dict((leaf[0], leaf[2]) for leaf in domain)['name']
        return self._sheets.get(name) or _Empty()


class _Empty(object):
    def __bool__(self):
        return False


class _User(object):
    def __init__(self, internal=True):
        self._internal = internal

    def has_group(self, xmlid):
        return self._internal and xmlid == 'base.group_user'


class _Env(object):
    def __init__(self, models, sheets=None, internal=True):
        self._models = dict((m._name, m) for m in models)
        self.modules = _ModuleModel(sheets or {})
        self.user = _User(internal)

    def __iter__(self):
        return iter(self._models)

    def __contains__(self, name):
        return name in self._models

    def __getitem__(self, name):
        if name == 'ir.module.module':
            return self.modules
        return self._models[name]


def _env(model_cls=_Model18, **kw):
    models = [
        model_cls('acme.invoice', 'ACME Invoice', 'acme_billing'),
        model_cls('acme.invoice.line', 'ACME Invoice Line', 'acme_billing'),
        model_cls('acme.secret', 'ACME Invoice Secret', 'acme_vault', readable=False),
        model_cls('res.partner', 'Contact', 'base'),
    ]
    if model_cls is _Model18:
        models.append(_Model18('acme.mixin', 'ACME Invoice Mixin', 'acme_billing', abstract=True))
    sheets = {
        'acme_billing': _ModuleRec('ACME Billing', 'Invoices for ACME', 'Long text ' * 10),
    }
    return _Env(models, sheets=sheets, **kw)


class TestCanRead(unittest.TestCase):

    def test_both_access_apis(self):
        self.assertTrue(can_read_model(_Model18('a.b', 'A', 'x')))
        self.assertFalse(can_read_model(_Model18('a.b', 'A', 'x', readable=False)))
        self.assertTrue(can_read_model(_Model14('a.b', 'A', 'x')))
        self.assertFalse(can_read_model(_Model14('a.b', 'A', 'x', readable=False)))


class TestFindModels(unittest.TestCase):

    def test_ranks_by_name_and_description(self):
        for cls in (_Model18, _Model14):
            rows = find_models(_env(cls), 'invoice')
            names = [r['model'] for r in rows]
            self.assertEqual(names[:2], ['acme.invoice', 'acme.invoice.line'])
            self.assertEqual(rows[0]['module'], 'acme_billing')
            self.assertEqual(rows[0]['name'], 'ACME Invoice')

    def test_skips_unreadable_and_abstract(self):
        names = [r['model'] for r in find_models(_env(), 'invoice')]
        self.assertNotIn('acme.secret', names)
        self.assertNotIn('acme.mixin', names)

    def test_description_word(self):
        names = [r['model'] for r in find_models(_env(), 'contact')]
        self.assertEqual(names, ['res.partner'])

    def test_close_name_when_no_word_hits(self):
        names = [r['model'] for r in find_models(_env(), 'res.partnr')]
        self.assertIn('res.partner', names)

    def test_empty_text_raises(self):
        with self.assertRaises(ValueError):
            find_models(_env(), '  ')

    def test_limit(self):
        self.assertEqual(len(find_models(_env(), 'acme', limit=1)), 1)


class TestModelModule(unittest.TestCase):

    def test_sheet_of_installed_module(self):
        env = _env(_Model14)
        row = model_module(env, 'acme.invoice')
        self.assertEqual(row['module'], 'acme_billing')
        self.assertEqual(row['module_name'], 'ACME Billing')
        self.assertEqual(row['summary'], 'Invoices for ACME')
        self.assertTrue(env.modules.sudo_called)
        self.assertIn(('state', '=', 'installed'), env.modules.domains[0])

    def test_description_is_capped(self):
        row = model_module(_env(), 'acme.invoice', max_chars=20)
        self.assertTrue(row['description'].endswith(' …'))
        self.assertLessEqual(len(row['description']), 22)

    def test_unreadable_model_is_none(self):
        self.assertIsNone(model_module(_env(), 'acme.secret'))

    def test_unknown_model_raises(self):
        with self.assertRaises(KeyError):
            model_module(_env(), 'no.such.model')

    def test_not_internal_user_gets_no_sheet(self):
        env = _env(internal=False)
        row = model_module(env, 'acme.invoice')
        self.assertEqual(row['module'], 'acme_billing')
        self.assertNotIn('summary', row)
        self.assertFalse(env.modules.sudo_called)

    def test_module_without_sheet(self):
        row = model_module(_env(), 'res.partner')
        self.assertEqual(row['module'], 'base')
        self.assertNotIn('summary', row)


if __name__ == '__main__':
    unittest.main()
