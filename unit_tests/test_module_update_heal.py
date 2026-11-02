# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Unit tests for module.update step fingerprint and skip rules."""

from __future__ import annotations

import unittest

from _load_addon import load_module

mod = load_module(
    'pns_ai_mcp_module_update_heal', 'utils', 'module_update_heal.py',
)


class TestModuleUpdateHeal(unittest.TestCase):

    def test_fingerprint_stable(self):
        a = [{'op': 'action', 'action_code': 'module.update',
              'args': {'module': 'pns_ribbon', 'operation': 'uninstall'}}]
        b = [{'args': {'operation': 'uninstall', 'module': 'pns_ribbon'},
              'action_code': 'module.update', 'op': 'action'}]
        self.assertEqual(mod.steps_fingerprint(a), mod.steps_fingerprint(b))

    def test_parse_and_match_state(self):
        steps = [{'op': 'action', 'action_code': 'module.update',
                  'args': {'module': 'pns_ribbon', 'operation': 'uninstall'}}]
        name, op, _ids = mod.module_update_args_from_steps(steps)
        self.assertEqual(name, 'pns_ribbon')
        self.assertEqual(op, 'uninstall')
        self.assertTrue(mod.module_state_matches('uninstall', 'uninstalled'))
        self.assertFalse(mod.module_state_matches('uninstall', 'installed'))
        self.assertTrue(mod.module_state_matches('install', 'installed'))
        self.assertFalse(mod.module_state_matches('install', 'installed', loaded=False))
        self.assertTrue(mod.module_state_matches('install', 'installed', loaded=True))
        self.assertFalse(mod.should_skip_module_op('install', 'uninstalled', loaded=False))
        self.assertFalse(mod.should_skip_module_op('install', 'installed', loaded=False))
        self.assertTrue(mod.should_skip_module_op('install', 'installed', loaded=True))

    def test_button_and_ids_aliases(self):
        steps = [{'op': 'action', 'action_code': 'module.update',
                  'args': {'module_ids': [2618],
                           'button': 'button_immediate_install'}}]
        name, op, ids = mod.module_update_args_from_steps(steps)
        self.assertIsNone(name)
        self.assertEqual(op, 'install')
        self.assertEqual(ids, [2618])
        self.assertTrue(mod.plan_has_module_update(steps))
        self.assertEqual(
            mod.operation_from_args({'button': 'button_immediate_uninstall'}),
            'uninstall',
        )
        self.assertEqual(
            mod.module_name_from_args({'module': 'pns_ribbon', 'module_ids': [1]}),
            'pns_ribbon',
        )

    def test_module_update_must_be_the_only_step(self):
        alone = [{'op': 'action', 'action_code': 'module.update',
                  'args': {'module': 'pns_ribbon', 'operation': 'install'}}]
        self.assertIsNone(mod.module_update_alone_error(alone))
        mixed = alone + [{'op': 'write', 'model': 'res.partner',
                          'ids': [1], 'values': {'name': 'x'}}]
        self.assertIn('only, once', mod.module_update_alone_error(mixed))
        two = alone + [{'op': 'action', 'action_code': 'module.update',
                        'args': {'module': 'mail', 'operation': 'upgrade'}}]
        self.assertIn('only, once', mod.module_update_alone_error(two))
        self.assertIsNone(mod.module_update_alone_error([
            {'op': 'write', 'model': 'res.partner', 'ids': [1],
             'values': {'name': 'x'}},
        ]))

    def test_ignores_other_actions(self):
        name, op, ids = mod.module_update_args_from_steps([{
            'op': 'action', 'action_code': 'view.set_field_required',
            'args': {'model': 'res.partner', 'field': 'comment'},
        }])
        self.assertIsNone(name)
        self.assertIsNone(op)
        self.assertEqual(ids, [])


if __name__ == '__main__':
    unittest.main()
