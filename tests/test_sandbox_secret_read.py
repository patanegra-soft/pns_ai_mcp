# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""On the sandbox cursor an AI admin reads the provider, not its key."""

from odoo import api
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, tagged

from odoo.addons.pns_ai_mcp.utils.sandbox_secrets import SANDBOX_CURSOR_FLAG


@tagged('post_install', '-at_install', 'pns_ai_mcp')
class TestSandboxSecretRead(TransactionCase):

    def setUp(self):
        super().setUp()
        self.provider = self.env['ai.provider'].create({
            'name': 'Sandbox secret provider',
            'protocol': 'openai',
            'api_key': 'sk-sandbox-secret',
        })
        self.env['ir.config_parameter'].sudo().set_param(
            'pns_test.sandbox_token', 'tok-sandbox-secret')
        self.env['ir.config_parameter'].sudo().set_param(
            'pns_test.sandbox_label', 'visible')
        # Creating a user trips instance add-ons that derive data from the name.
        admin = self.env.ref('base.user_admin')
        for xmlid in ('base.group_system', 'pns_ai_mcp.group_ai_admin'):
            group = self.env.ref(xmlid)
            members = 'user_ids' if 'user_ids' in group._fields else 'users'
            group.write({members: [(4, admin.id)]})
        self.user_env = api.Environment(self.env.cr, admin.id, {})
        setattr(self.env.cr, SANDBOX_CURSOR_FLAG, True)
        self.addCleanup(delattr, self.env.cr, SANDBOX_CURSOR_FLAG)
        self._forget()

    def _forget(self):
        env = self.env
        if hasattr(env, 'invalidate_all'):
            env.invalidate_all()
        else:
            env['ai.provider'].invalidate_cache()

    def _provider(self):
        return self.user_env['ai.provider'].browse(self.provider.id)

    def test_row_reads_but_key_does_not(self):
        provider = self._provider()
        self.assertEqual(provider.name, 'Sandbox secret provider')
        with self.assertRaises(AccessError):
            provider.api_key
        self._forget()
        with self.assertRaises(AccessError):
            self._provider().read(['api_key'])
        self._forget()
        row = self._provider().read()[0]
        self.assertNotIn('api_key', row)
        self.assertEqual(row['name'], 'Sandbox secret provider')

    def test_key_is_not_a_search_oracle(self):
        Provider = self.user_env['ai.provider']
        with self.assertRaises(AccessError):
            Provider.search([('api_key', '=like', 'sk-%')])
        with self.assertRaises(AccessError):
            Provider.search([], order='api_key')

    def test_the_owner_reads_outside_the_sandbox(self):
        delattr(self.env.cr, SANDBOX_CURSOR_FLAG)
        self.addCleanup(setattr, self.env.cr, SANDBOX_CURSOR_FLAG, True)
        self._forget()
        self.assertEqual(self._provider().api_key, 'sk-sandbox-secret')

    def test_parameters_read_except_secret_keys(self):
        Param = self.user_env['ir.config_parameter']
        self.assertEqual(Param.get_param('pns_test.sandbox_label'), 'visible')
        with self.assertRaises(AccessError):
            Param.get_param('pns_test.sandbox_token')
        with self.assertRaises(AccessError):
            Param.get_param('database.secret')
        label = Param.search([('key', '=', 'pns_test.sandbox_label')])
        self.assertEqual(label.value, 'visible')
        self._forget()
        token = Param.search([('key', '=', 'pns_test.sandbox_token')])
        with self.assertRaises(AccessError):
            token.value
        with self.assertRaises(AccessError):
            Param.search([('value', '=like', 'tok-%')])
