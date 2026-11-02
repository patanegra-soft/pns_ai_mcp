# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Tests: table anti-echo + AST-gated reuse."""
from __future__ import annotations

import html
import json
import unittest

from _load_addon import load_module

anti = load_module('pns_ai_mcp_response_anti_echo', 'utils', 'response_anti_echo.py')

fingerprint_dataset_payload = anti.fingerprint_dataset_payload
extract_dataset_fingerprints = anti.extract_dataset_fingerprints
fingerprints_from_history = anti.fingerprints_from_history
strip_echoed_table_blocks = anti.strip_echoed_table_blocks
code_references_reuse_names = anti.code_references_reuse_names


def _table_html(rows):
    payload = html.escape(json.dumps(rows, ensure_ascii=False), quote=True)
    return (
        f'<div class="o_ai_table_block" data-ai-dataset="{payload}">'
        f'<div class="table-responsive"><table><tr><td>x</td></tr></table></div>'
        f'</div>'
    )


class TestAntiEcho(unittest.TestCase):
    def test_strip_prior_dataset_keep_new(self):
        invoices = [
            {'id': 11611, 'Factura': 'FactC/2025/0918', '__model': 'account.move'},
        ]
        attendance = [
            {'Empleado': 'Ana', 'Entrada': '07:01', 'Salida': '15:00'},
        ]
        prior_html = _table_html(invoices)
        prior_fps = extract_dataset_fingerprints(prior_html)
        mixed = (
            'Attendance · hoy\n'
            + prior_html
            + '\nTienes razón.\n'
            + _table_html(attendance)
        )
        attendance_fp = fingerprint_dataset_payload(attendance)
        out = strip_echoed_table_blocks(
            mixed, prior_fps, allow_fingerprints={attendance_fp},
        )
        self.assertNotIn('FactC/2025/0918', out)
        self.assertIn('Empleado', out)
        self.assertIn('Attendance', out)

    def test_allow_regenerated_same_fingerprint(self):
        rows = [{'id': 1, 'name': 'Acme'}]
        block = _table_html(rows)
        fp = fingerprint_dataset_payload(rows)
        out = strip_echoed_table_blocks(
            block, {fp}, allow_fingerprints={fp},
        )
        self.assertIn('Acme', out)

    def test_history_fingerprints_assistant_only(self):
        rows = [{'id': 2, 'name': 'X'}]
        hist = [
            {'role': 'user', 'content': _table_html(rows)},
            {'role': 'assistant', 'content': _table_html(rows)},
        ]
        fps = fingerprints_from_history(hist)
        self.assertEqual(fps, {fingerprint_dataset_payload(rows)})

    def test_code_reuse_names_ignores_comments(self):
        self.assertFalse(code_references_reuse_names(
            '# no usar previous_result/raw_data de facturas\n'
            'result = {\'data\': attendance_today}\n'
        ))
        self.assertTrue(code_references_reuse_names(
            'result = {\'data\': sorted(raw_data, key=lambda r: r[\'name\'])}\n'
        ))
        self.assertTrue(code_references_reuse_names(
            'base = previous_result[\'data\'] if previous_result else []\n'
            'result = {\'data\': base}\n'
        ))


if __name__ == '__main__':
    unittest.main()
