# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""A plain internal user discovers models and modules in every series.

From Odoo 17 that user cannot read ir.model; in Odoo 14 not ir.module.module.
The answer must be the same in both.
"""

from odoo.tests import TransactionCase, tagged

from odoo.addons.pns_ai_mcp.controllers.context_builder import GuardedSandboxEnv
from odoo.addons.pns_ai_mcp.tests._helpers import create_test_user
from odoo.addons.pns_ai_mcp.utils.model_discovery import find_models, model_module


@tagged('post_install', '-at_install', 'pns_ai_mcp')
class TestModelDiscoveryLive(TransactionCase):

    def setUp(self):
        super().setUp()
        user = create_test_user(self.env, prefix='pns_discovery')
        self.assertFalse(user.has_group('base.group_system'))
        self.uenv = self.env(user=user)

    def test_find_models_without_ir_model(self):
        rows = find_models(self.uenv, 'partner')
        by_model = dict((r['model'], r) for r in rows)
        self.assertIn('res.partner', by_model)
        self.assertEqual(by_model['res.partner']['module'], 'base')

    def test_model_module_reads_the_module_sheet(self):
        row = model_module(self.uenv, 'res.partner')
        self.assertEqual(row['module'], 'base')
        self.assertTrue(row['module_name'])
        for key in ('module_name', 'summary', 'description'):
            self.assertIsInstance(row[key], str)

    def test_unreadable_model_stays_out(self):
        self.assertIsNone(model_module(self.uenv, 'ir.config_parameter'))
        names = [r['model'] for r in find_models(self.uenv, 'config parameter', limit=50)]
        self.assertNotIn('ir.config_parameter', names)

    def test_sandbox_env_lists_model_names(self):
        names = list(GuardedSandboxEnv(self.uenv))
        self.assertIn('res.partner', names)
        self.assertEqual(len(GuardedSandboxEnv(self.uenv)), len(names))
