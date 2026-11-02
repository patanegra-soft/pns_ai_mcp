# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Safe Plan: one row, one resolve path, hosts refresh from that row."""
from _load_addon import addon_file


def test_one_flight_commits_between_confirm_and_execute():
    src = addon_file('models', 'safe_operation.py').read_text(encoding='utf-8')
    method = src.split('def _resolve_confirm_and_execute')[1].split(
        'def _execute_plan_with_timeouts'
    )[0]
    assert method.count('self.env.cr.commit()') == 2
    assert method.index('_resolve_execute') < method.rindex('self.env.cr.commit()')
    assert 'invalidate_recordset_fields' in method
    assert '_resolve_execute' in method
    action = src.split('def action_confirm_and_execute')[1].split(
        'def action_execute_plan'
    )[0]
    assert '_resolve_confirm_and_execute' in action
    assert 'self._resolve_confirm(' not in action


def test_hosts_are_notified_from_the_row():
    src = addon_file('models', 'safe_operation.py').read_text(encoding='utf-8')
    assert 'def _notify_safe_plan_hosts' in src
    assert "'type': 'pns_safe_plan'" in src
    wrapper = src.split('def _notify_safe_plan_hosts(')[1].split(
        'def _notify_safe_plan_hosts_now'
    )[0]
    assert 'cr.savepoint()' in wrapper
    notify = src.split('def _notify_safe_plan_hosts_now')[1].split(
        'def _notify_reload'
    )[0]
    assert "'_sendone'" in notify
    assert "'sendone'" in notify


def test_apply_persists_executed_status():
    src = addon_file('models', 'safe_operation.py').read_text(encoding='utf-8')
    assert "('executed', 'Executed')" in src
    apply_sql = src.split('def execute_plan_now')[1].split(
        'def _heal_module_update_after_registry_reset'
    )[0]
    assert "status = 'executed'" in apply_sql
    assert "def _align_executed_status" in src
    assert "SET status = 'executed'" in src.split('def _align_executed_status')[1]


def test_autorizaciones_listens_for_the_row():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    owl1 = (
        root / 'stacks' / 'owl1' / 'pns_ai_mcp'
        / 'static' / 'src' / 'js' / 'safe_operation_tree_v14.js'
    ).read_text(encoding='utf-8')
    owl2 = (
        root / 'stacks' / 'owl2' / 'pns_ai_mcp'
        / 'static' / 'src' / 'js' / 'safe_operation_action_buttons.js'
    ).read_text(encoding='utf-8')
    views1 = (
        root / 'stacks' / 'owl1' / 'pns_ai_mcp'
        / 'views' / 'safe_operation_views.xml'
    ).read_text(encoding='utf-8')
    views2 = (
        root / 'stacks' / 'owl2' / 'pns_ai_mcp'
        / 'views' / 'safe_operation_views.xml'
    ).read_text(encoding='utf-8')
    assert "payload.type === 'pns_safe_plan'" in owl1
    assert "tag: 'reload'" in owl1
    assert 'subscribe("pns_safe_plan"' in owl2
    assert 'tag: "reload"' in owl2
    assert 'root.load' not in owl2
    assert "status == 'executed'" in views1
    assert "status == 'executed'" in views2
    assert "('status', '=', 'executed')" in views1
    assert "('status', '=', 'executed')" in views2


def test_ticked_rows_cancel_from_the_menu_the_list_always_shows():
    """Confirm fills the last column, so Cancel never reached the screen."""
    src = addon_file('models', 'safe_operation.py').read_text(encoding='utf-8')
    action = src.split('def action_cancel')[1].split('def _cancel_marked')[0]
    assert 'len(self) > 1' in action
    assert 'return self._cancel_marked()' in action
    marked = src.split('def _cancel_marked')[1].split('\n    # Throttle')[0]
    assert "rec.status == 'pending'" in marked
    assert 'cancel_by_user' in marked
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    for stack in ('owl1', 'owl2'):
        view = (
            root / 'stacks' / stack / 'pns_ai_mcp'
            / 'views' / 'safe_operation_views.xml'
        ).read_text(encoding='utf-8')
        tree = view.split('id="view_ai_safe_operation_tree"')[1].split('</tree>')[0]
        assert tree.index('name="action_cancel"') < tree.index('name="create_date"')
        assert 'action_server_safe_operation_cancel' in view
        assert 'records.action_cancel()' in view
        said = (
            root / 'stacks' / stack / 'pns_ai_mcp' / 'i18n'
            / ('es.po' if stack == 'owl1' else 'es_ES.po')
        ).read_text(encoding='utf-8')
        assert 'action_server_safe_operation_cancel' in said
        assert 'msgstr "Cancelar"' in said


def test_a_failed_write_is_not_reported_as_applying():
    """A duplicate key is over: the host must not promise it is under way."""
    src = addon_file('models', 'safe_operation.py').read_text(encoding='utf-8')
    method = src.split('def _resolve_execute')[1].split(
        'def _resolve_confirm_and_execute'
    )[0]
    hard = method.split("if out.get('status') == 'error':")[1].split(
        '# No tumbar'
    )[0]
    assert "'success': False" in hard
    assert "error=out.get('error')" in hard
    # The soft «applying…» stays for the busy claim, which is worth waiting for.
    assert "'async_execute': True" in method
