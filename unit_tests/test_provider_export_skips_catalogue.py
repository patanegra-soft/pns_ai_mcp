# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Provider export names the chosen model. The catalogue stays out of the file."""
from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _src(*parts):
    return (_ROOT.joinpath(*parts)).read_text(encoding='utf-8')


def test_provider_file_export_does_not_list_the_catalogue():
    body = _src('common', 'models', 'ai_provider.py').split(
        'def _export_providers_file', 1,
    )[1].split('\n    def ', 1)[0]
    assert 'available_models' not in body
    assert "server_data['selected_model']" in body
    assert "server_data['failovers']" not in body
    assert "server_data['usage_days']" not in body


def test_config_backup_export_does_not_list_the_catalogue():
    src = _src('common', 'utils', 'config_backup.py')
    assert "[{'name': m.name} for m in p.available_model_ids]" not in src
    assert "d['selected_model']" in src
    export_providers = src.split('def _export_providers', 1)[1].split(
        'def _export_agents', 1,
    )[0]
    assert "d['usage_days']" not in export_providers
    assert "d['failovers']" not in export_providers


def test_provider_import_keeps_only_the_chosen_model():
    wizard = _src('common', 'wizard', 'import_servers_wizard.py')
    assert 'available_model_ids.unlink()' not in wizard
    assert 'def _import_failovers' not in wizard
    assert 'import_missing_days' not in wizard
    backup = _src('common', 'utils', 'config_backup.py').split(
        'def _import_providers', 1,
    )[1].split('\ndef ', 1)[0]
    assert "row.get('models')" not in backup
    assert "row.get('selected_model')" in backup
    assert 'import_missing_days' not in backup
