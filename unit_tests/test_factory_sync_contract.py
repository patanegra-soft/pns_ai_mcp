# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Factory sync: one worker, disk text, instance active, retire missing files."""
from pathlib import Path
from _load_addon import skill_source

_ROOT = Path(__file__).resolve().parents[1]
_HOOKS = (_ROOT / 'common' / 'hooks.py').read_text(encoding='utf-8')
_CTX = (_ROOT / 'common' / 'models' / 'ai_context_disk.py').read_text(encoding='utf-8')
_SKILL = skill_source()


def test_factory_sync_takes_an_advisory_lock_and_rechecks_the_stamp():
    body = _HOOKS.split('def maybe_sync_factory_knowledge', 1)[1].split(
        '\ndef ', 1)[0]
    assert 'pg_try_advisory_xact_lock' in body
    assert body.index('pg_try_advisory_xact_lock') < body.index(
        'factory_knowledge_stamp(env)')
    assert body.index('FACTORY_SYNC_LOCK_KEY') < body.index('sync_factory_knowledge')


def test_existing_factory_rows_keep_the_instance_active_flag():
    ctx_write = _CTX.split('write_vals = dict(vals)', 1)[1].split(
        'existing.with_context', 1)[0]
    assert "write_vals.pop('active', None)" in ctx_write
    skill_write = _SKILL.split(
        "if k not in ('show_in_slash', 'active')", 1)[0]
    assert "if k not in ('show_in_slash', 'active')" in _SKILL
    assert skill_write  # split found the marker


def test_retired_factory_contexts_unlink_only_after_a_real_scan():
    body = _CTX.split('def _unlink_retired_from_module', 1)[1].split(
        '\n    @api.model', 1)[0]
    assert "if not on_disk:" in body
    assert "('owner_id', '=', False)" in body
    assert "('rel_path', '!=', False)" in body
    import_tail = _CTX.split('if (\n            replace_existing', 1)[1].split(
        'return {', 1)[0]
    assert 'found_codes' in import_tail
    assert '_unlink_retired_from_module' in import_tail


def test_found_codes_include_a_file_even_when_the_pack_is_retired():
    walk = _CTX.split('found_codes.append(code)', 1)[1].split(
        'if is_system:', 1)[0]
    assert 'is_retired_self_pack_code' in walk
