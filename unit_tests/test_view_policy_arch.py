# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""View-inherit arch builder — no Odoo runtime."""
from __future__ import annotations

import unittest

from _load_addon import load_module

mod = load_module('pns_ai_mcp_view_policy_arch', 'utils', 'view_policy_arch.py')


class TestViewPolicyArch(unittest.TestCase):

    def test_required_xpath(self):
        arch = mod.build_modifier_arch('vat', 'required', True)
        self.assertIn("expr=\"//field[@name='vat']", arch)
        self.assertIn("not(@invisible='1')", arch)
        self.assertIn("hasclass('oe_read_only')", arch)
        self.assertIn('<attribute name="required">1</attribute>', arch)
        self.assertIn('position="attributes"', arch)

    def test_readonly_false(self):
        arch = mod.build_modifier_arch('comment', 'readonly', False)
        self.assertIn('<attribute name="readonly">0</attribute>', arch)
        self.assertIn("expr=\"//field[@name='comment']\"", arch)
        self.assertNotIn('oe_read_only', arch)

    def test_invisible(self):
        arch = mod.build_modifier_arch('email', 'invisible', True)
        self.assertIn('<attribute name="invisible">1</attribute>', arch)

    def test_domain_list_and_clear(self):
        arch = mod.build_modifier_arch(
            'parent_id', 'domain', [('is_company', '=', True)],
        )
        self.assertIn("name=\"domain\"", arch)
        self.assertIn('is_company', arch)
        cleared = mod.build_modifier_arch('parent_id', 'domain', False)
        self.assertIn('name="domain">[]</attribute>', cleared)

    def test_xml_escape_in_domain(self):
        arch = mod.build_modifier_arch(
            'name', 'domain', [('name', '=', 'A&B')],
        )
        self.assertIn('&amp;', arch)
        self.assertNotIn('A&B', arch)

    def test_arch_contains_field_exact(self):
        xml = '<form><field name="vat"/><field name="vat_label"/></form>'
        self.assertTrue(mod.arch_contains_field(xml, 'vat'))
        self.assertTrue(mod.arch_contains_field(xml, 'vat_label'))
        self.assertFalse(mod.arch_contains_field(xml, 'va'))
        self.assertFalse(mod.arch_contains_field(xml, 'missing'))
        # Policy inherit xpath is not a display.
        xpath_only = (
            '<data><xpath expr="//field[@name=\'vat\']" position="attributes">'
            '<attribute name="required">1</attribute></xpath></data>'
        )
        self.assertFalse(mod.arch_contains_field(xpath_only, 'vat'))

    def test_xmlid_stable(self):
        a = mod.policy_xmlid_name('res.partner', 'comment', 'required', 12)
        b = mod.policy_xmlid_name('res.partner', 'comment', 'required', 12)
        self.assertEqual(a, b)
        self.assertTrue(a.startswith('vp_res_partner_comment_required_12'))

    def test_uniform_required_xpath(self):
        arch = mod.build_modifier_arch('vat', 'required', True, uniform=True)
        self.assertIn("expr=\"//field[@name='vat']\"", arch)
        self.assertNotIn('oe_read_only', arch)

    def test_rejects_bad_field(self):
        with self.assertRaises(ValueError):
            mod.build_modifier_arch("vat']", 'required', True)
        with self.assertRaises(ValueError):
            mod.build_modifier_arch('vat', 'unknown', True)


if __name__ == '__main__':
    unittest.main()
