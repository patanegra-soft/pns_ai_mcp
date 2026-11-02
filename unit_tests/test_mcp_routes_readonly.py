# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Odoo 19 opens auth='none' routes on a read-only cursor unless told otherwise.

A POST on /mcp writes (log, last client, safe operations). On a read-only
cursor Odoo replays the whole request on a read/write one, so anything done
before the first write (an outbound HTTP call) would run twice.
"""

import re
from pathlib import Path

MAIN = Path(__file__).resolve().parents[1] / 'common' / 'controllers' / 'main.py'
ROUTE = re.compile(r'@http\.route\((.*?)\)\s*\n', re.S)


def test_writing_auth_none_routes_ask_for_a_read_write_cursor():
    routes = [m.group(1) for m in ROUTE.finditer(MAIN.read_text(encoding='utf-8'))]
    writing = [r for r in routes if "auth='none'" in r and "'POST'" in r]
    assert writing
    missing = [r for r in writing if 'readonly=False' not in r]
    assert not missing, missing
