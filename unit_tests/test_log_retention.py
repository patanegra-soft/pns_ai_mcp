# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Activity log retention, test key hygiene and no disk deletes."""
from __future__ import annotations

import re
from pathlib import Path

from _load_addon import context_source

_ROOT = Path(__file__).resolve().parents[1]
_COMMON = _ROOT / 'common'


def _src(*parts):
    return _COMMON.joinpath(*parts).read_text(encoding='utf-8')


def test_log_user_survives_user_deletion_until_retention():
    src = _src('models', 'ai_log.py')
    field = src.split('user_id = fields.Many2one(', 1)[1].split(')', 1)[0]
    assert "ondelete='set null'" in field
    assert 'required=True' not in field


def test_log_retention_cron_on_both_stacks():
    for stack in ('owl1', 'owl2'):
        base = _ROOT / 'stacks' / stack / 'pns_ai_mcp'
        xml = (base / 'data' / 'ai_log_cron.xml').read_text(encoding='utf-8')
        assert 'model._cron_purge_old_logs()' in xml
        assert ('name="numbercall"' in xml) == (stack == 'owl1')
        manifest = (base / '__manifest__.py').read_text(encoding='utf-8')
        assert "'data/ai_log_cron.xml'" in manifest
    src = _src('models', 'ai_log.py')
    assert "LOG_RETENTION_PARAM = 'pns_ai_mcp.log_retention_days'" in src
    # Unset retention deletes nothing (PNS-87): no default days anywhere.
    assert 'DEFAULT_LOG_RETENTION_DAYS' not in src
    cron = src.split('def _cron_purge_old_logs', 1)[1].split('\n    @', 1)[0]
    assert 'if raw is None or raw is False' in cron


def test_update_drops_no_history():
    fossils = _src('utils', 'schema_fossils.py')
    assert "'ai_provider_usage_day'," not in fossils.split(
        'FOSSIL_TABLES', 1)[1].split(')', 1)[0]
    assert "('ai_log', 'agent_id')," not in fossils
    settings = _src('models', 'res_config_settings.py')
    assert 'log_retention_days = fields.Integer(' in settings
    assert "config_parameter='pns_ai_mcp.log_retention_days'" in settings


def test_ai_admin_cannot_edit_log_rows():
    csv = _src('security', 'ir.model.access.csv')
    row = next(
        line for line in csv.splitlines()
        if line.startswith('access_ai_log_admin,')
    )
    assert row.endswith(',1,0,0,1')


def test_http_test_key_is_random_and_restored():
    src = _src('tests', '_helpers.py')
    assert "'pns-http-test-%s' % env.cr.dbname" not in src
    assert 'secrets.token_urlsafe' in src
    assert 'def teardown_http_mcp_fixtures' in src
    assert 'teardown_http_mcp_fixtures(cls)' in _src('tests', 'test_mcp_http.py')


def test_zoneinfo_exists_without_python_zoneinfo():
    src = _src('controllers', 'context_builder.py')
    assert 'from dateutil import tz as _dateutil_tz' in src


def test_context_sync_never_deletes_files_on_disk():
    src = context_source()
    assert not re.search(r'shutil\.rmtree|os\.remove\(|os\.unlink\(', src)
