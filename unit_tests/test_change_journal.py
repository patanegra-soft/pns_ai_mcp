# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""JSON contract of ai.change.journal — no Odoo runtime."""
from __future__ import annotations

import unittest

from _load_addon import load_module

mod = load_module('pns_ai_mcp_change_journal', 'utils', 'change_journal.py')


class TestChangeJournalContract(unittest.TestCase):

    def test_classify_technical_models(self):
        self.assertEqual(mod.classify_change_kind('ir.ui.view', 'write'), 'view_modifier')
        self.assertEqual(mod.classify_change_kind('ir.model.fields', 'write'), 'field_meta')
        self.assertEqual(mod.classify_change_kind('res.groups', 'write'), 'acl')
        self.assertEqual(mod.classify_change_kind('res.partner', 'create'), 'generic')
        self.assertEqual(mod.classify_change_kind('sale.order', 'action', 'sale.confirm'), 'trusted_action')
        self.assertEqual(mod.classify_change_kind('res.partner', 'field_required'), 'field_meta')
        self.assertIn('field_required', mod.MUTATING_OPS)

    def test_redact_sensitive_and_m2o(self):
        row = mod.redact_record({
            'id': 4,
            'name': 'Ada',
            'parent_id': (1, 'Company'),
            'password': 'secret',
            'smtp_pass': 'x',
        })
        self.assertEqual(row['parent_id'], 1)
        self.assertEqual(row['password'], '***')
        self.assertEqual(row['smtp_pass'], '***')
        self.assertEqual(row['name'], 'Ada')

    def test_payload_roundtrip(self):
        payload = mod.build_payload(
            'write', 'ir.ui.view', [42], ['arch_db'],
            [{'id': 42, 'arch_db': '<form/>'}],
            meta={'change_kind': 'view_modifier'},
        )
        text = mod.dumps_payload(payload)
        back = mod.loads_payload(text)
        self.assertEqual(back['schema_version'], 1)
        self.assertEqual(back['ids'], [42])
        self.assertEqual(back['records'][0]['id'], 42)

    def test_reversible_flags(self):
        before = {'records': [{'id': 1, 'name': 'old'}]}
        after = {'ids': [9]}
        ok, _reason = mod.initial_reversible('write', before, after)
        self.assertTrue(ok)
        ok, _reason = mod.initial_reversible('create', {}, after)
        self.assertTrue(ok)
        ok, _reason = mod.initial_reversible('unlink', before, {})
        self.assertFalse(ok)
        ok, _reason = mod.initial_reversible(
            'unlink', before, {'ids': [1], 'meta': {'quarantine': True}},
        )
        self.assertTrue(ok)
        ok, _reason = mod.initial_reversible('action', {}, {'meta': {}})
        self.assertFalse(ok)
        ok, _reason = mod.initial_reversible('field_required', {}, {})
        self.assertFalse(ok)

    def test_write_vals_from_before(self):
        mapping = mod.write_vals_from_before({
            'records': [
                {'id': 3, 'name': 'was', 'display_name': 'was', 'password': '***'},
            ],
        })
        self.assertEqual(mapping[3], {'name': 'was'})


if __name__ == '__main__':
    unittest.main()
