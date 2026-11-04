# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""An AI export says what it is, not which version it has."""
from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_EXPORTS = (
    _ROOT / 'common' / 'utils' / 'config_backup.py',
    _ROOT / 'common' / 'utils' / 'artifact_bundle.py',
)
# Internal rescue tool; publish.exclude leaves tools/ out of the published tree.
_RESCUE = _ROOT / 'tools' / 'export_ai_config.py'
_EXAMPLES = _ROOT / 'common' / 'static' / 'examples' / 'providers'


def test_exports_write_what_and_no_version():
    paths = list(_EXPORTS) + ([_RESCUE] if _RESCUE.exists() else [])
    for path in paths:
        src = path.read_text(encoding='utf-8')
        assert "'what':" in src, path.name
        assert 'schema_version' not in src, path.name


def test_old_bundle_type_still_names_the_bundle():
    src = (_EXPORTS[1]).read_text(encoding='utf-8')
    assert "manifest.get('what') or manifest.get('type')" in src


def test_provider_examples_are_backups_without_keys():
    files = sorted(_EXAMPLES.glob('*.json'))
    assert files
    for path in files:
        data = json.loads(path.read_text(encoding='utf-8'))
        assert data['what'] == 'pns.ai.config.backup', path.name
        assert data['providers'], path.name
        for row in data['providers']:
            assert row['name'], path.name
            assert 'api_key' not in row, path.name
            assert isinstance(row['roles'], list), path.name
