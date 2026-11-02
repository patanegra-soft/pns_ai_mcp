# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Model name suggestions on a KeyError (from the registry, no domain words)."""
from __future__ import annotations

import unittest

from _load_addon import load_module

mod = load_module('pns_ai_mcp_model_name_suggest', 'utils', 'model_name_suggest.py')
suggest_model_names = mod.suggest_model_names
format_missing_model_hint = mod.format_missing_model_hint


class TestSuggestModelNames(unittest.TestCase):
    def test_mcp_log_suggests_ai_log_by_suffix(self):
        available = [
            'res.partner', 'account.move', 'ai.log', 'ai.agent', 'mail.message',
        ]
        out = suggest_model_names('mcp.log', available)
        self.assertIn('ai.log', out)
        self.assertEqual(out[0], 'ai.log')

    def test_close_match_typo(self):
        available = ['res.partner', 'res.users', 'product.product']
        out = suggest_model_names('res.partnr', available)
        self.assertIn('res.partner', out)

    def test_hint_mentions_suggested(self):
        text = format_missing_model_hint('mcp.log', ['ai.log'])
        self.assertIn("env['ai.log']", text)
        self.assertIn('SUGGESTED MODELS', text)

    def test_hint_without_suggestions_uses_ir_model_not_registry(self):
        text = format_missing_model_hint('no.such.model', [])
        self.assertIn("env['ir.model']", text)
        self.assertNotIn('env.registry', text)
        self.assertNotIn('sorted(env.registry)', text)


if __name__ == '__main__':
    unittest.main()
