# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""List titles must not use overflow:hidden. That drops the sticky header."""
from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_list_titles_do_not_hide_overflow():
    for rel in (
        'stacks/owl1/pns_ai_mcp/static/src/css/pns_list.css',
        'stacks/owl2/pns_ai_mcp/static/src/css/pns_list.css',
    ):
        text = (_ROOT / rel).read_text(encoding='utf-8')
        head = text.split('.o_pns_list .o_list_table thead th')[1].split('}')[0]
        assert 'overflow: clip' in head
        assert 'overflow: hidden' not in head
