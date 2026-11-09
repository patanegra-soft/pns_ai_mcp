# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Every engine setting the export writes, the import can put back.

The export takes every portable field of the module; the import only writes
fields that name their system parameter. A field without one comes back as
"Unknown setting … skipped" on the file the same instance just exported.
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = ROOT / 'common' / 'models' / 'res_config_settings.py'

# settings_io leaves these out of the export.
_NOT_EXPORTED = {'Many2one', 'One2many', 'Many2many', 'Binary', 'Html'}


def _settings_fields():
    tree = ast.parse(SETTINGS.read_text(encoding='utf-8'))
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for stmt in node.body:
            if not (isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Call)):
                continue
            func = stmt.value.func
            if not (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)
                    and func.value.id == 'fields'):
                continue
            kwargs = {k.arg for k in stmt.value.keywords}
            if func.attr in _NOT_EXPORTED or 'related' in kwargs:
                continue
            yield stmt.targets[0].id, kwargs


def test_every_exported_setting_names_its_parameter():
    found = list(_settings_fields())
    assert found
    missing = [name for name, kwargs in found if 'config_parameter' not in kwargs]
    assert missing == []
