# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Safe Plan unlink sits in the trash when the model can archive."""
from pathlib import Path

from _load_addon import load_module, safe_plan_source

_ROOT = Path(__file__).resolve().parents[1]
mod = load_module('pns_ai_mcp_change_journal', 'utils', 'change_journal.py')


def test_trash_days_default_and_zero():
    assert mod.DEFAULT_TRASH_DAYS == 30
    assert mod.ICP_TRASH_DAYS == 'pns_ai_mcp.journal_trash_days'
    assert mod.trash_days_from_param(None) == 30
    assert mod.trash_days_from_param('') == 30
    assert mod.trash_days_from_param('0') == 0
    assert mod.trash_days_from_param(-4) == 30
    assert mod.trash_days_from_param('7') == 7


def test_trash_cron_on_both_stacks():
    for stack in ('owl1', 'owl2'):
        base = _ROOT / 'stacks' / stack / 'pns_ai_mcp'
        xml = (base / 'data' / 'journal_trash_cron.xml').read_text(encoding='utf-8')
        assert 'model._cron_empty_journal_trash()' in xml
        assert ('name="numbercall"' in xml) == (stack == 'owl1')
        manifest = (base / '__manifest__.py').read_text(encoding='utf-8')
        assert "'data/journal_trash_cron.xml'" in manifest


def test_plan_archives_when_the_model_has_active():
    plan = safe_plan_source().split('def execute_safe_plan(')[1]
    unlink = plan.split("elif op == 'unlink':")[1].split('return results')[0]
    assert 'model_can_archive(model)' in unlink
    assert "recs.write({'active': False})" in unlink
    assert 'quarantine' in unlink
    journal = (
        _ROOT / 'common' / 'models' / 'ai_change_journal.py'
    ).read_text(encoding='utf-8')
    assert "self.op == 'unlink' and (after.get('meta') or {}).get('quarantine')" in journal
    assert 'def _cron_empty_journal_trash' in journal
    settings = (
        _ROOT / 'common' / 'models' / 'res_config_settings.py'
    ).read_text(encoding='utf-8')
    assert 'journal_trash_days = fields.Integer(' in settings
    assert "config_parameter='pns_ai_mcp.journal_trash_days'" in settings
    assert 'def action_empty_journal_trash' in settings
