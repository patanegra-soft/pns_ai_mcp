# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""The MCP controller does not own the resource catalogue."""
from __future__ import annotations

from pathlib import Path


def test_main_does_not_import_resource_snapshot():
    main = (
        Path(__file__).resolve().parents[1]
        / 'common' / 'controllers' / 'main.py'
    ).read_text(encoding='utf-8')
    assert "env['pns_ai_mcp.mcp_resource']" not in main
