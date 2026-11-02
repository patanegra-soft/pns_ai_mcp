# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""skill_code_body_path: .md stem first, then {code}.py fallback."""
from __future__ import annotations

from pathlib import Path

from _load_addon import load_module

skill_files = load_module('skill_files', 'utils', 'skill_files.py')


def test_prefers_markdown_stem_over_slash_code(tmp_path: Path):
    md_stem = 'custom_tenant_topic_check'
    (tmp_path / ('%s.py' % md_stem)).write_text('# body\n', encoding='utf-8')
    path = skill_files.skill_code_body_path(
        str(tmp_path), '%s.md' % md_stem, 'hr_check', 'hr-check',
    )
    assert path.endswith('%s.py' % md_stem)


def test_falls_back_to_command_py_when_stem_missing(tmp_path: Path):
    (tmp_path / 'hr-check.py').write_text('# legacy\n', encoding='utf-8')
    path = skill_files.skill_code_body_path(
        str(tmp_path), 'custom_tenant_topic_check.md', 'hr_check', 'hr-check',
    )
    assert path.endswith('hr-check.py')


def test_split_identity_snake_file_kebab_skill():
    code, command = skill_files.split_skill_identity(
        'sys_info.md', {'skill': 'sys-info'},
    )
    assert code == 'sys_info'
    assert command == 'sys-info'


def test_split_identity_legacy_kebab_filename():
    code, command = skill_files.split_skill_identity(
        'sys-info.md', {'skill': 'sys-info'},
    )
    assert code == 'sys_info'
    assert command == 'sys-info'


def test_split_identity_single_token():
    code, command = skill_files.split_skill_identity(
        'billing.md', {'skill': 'billing'},
    )
    assert code == 'billing'
    assert command == ''


def test_factory_row_on_disk_matches_stale_rel_by_command():
    rels = {'skills/custom/custom_acme_flota.md'}
    codes = {'custom_acme_flota'}
    cmds = {'acme-flota'}
    assert skill_files.factory_row_on_disk(
        '', 'acme_custom_flota', 'acme-flota', rels, codes, cmds,
    )
    assert skill_files.factory_row_on_disk(
        'skills/custom/custom_acme_flota.md', 'x', 'y', rels, codes, cmds,
    )
    assert not skill_files.factory_row_on_disk(
        '', 'other', 'other-slash', rels, codes, cmds,
    )
