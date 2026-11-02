# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Safe defaults: import does not overwrite, duplicate carries no key."""
from pathlib import Path

_COMMON = Path(__file__).resolve().parents[1] / 'common'


def test_config_import_does_not_overwrite_by_default():
    src = (_COMMON / 'wizard' / 'config_backup_wizard.py').read_text(encoding='utf-8')
    field = src.split('replace_existing = fields.Boolean(', 1)[1].split(')', 1)[0]
    assert 'default=False' in field
    assert 'default=True' not in field
    assert 'def action_preview' in src
    assert 'dry_run=True' in src
    backup = (_COMMON / 'utils' / 'config_backup.py').read_text(encoding='utf-8')
    assert 'def _should_write' in backup
    assert 'if not dry:' in backup or 'if not dry_run:' in backup


def test_should_write_counts_without_writing_on_preview():
    import ast

    src = (_COMMON / 'utils' / 'config_backup.py').read_text(encoding='utf-8')
    tree = ast.parse(src)
    ns = {}
    for name in ('_mark', '_should_write'):
        fn = next(
            n for n in tree.body
            if isinstance(n, ast.FunctionDef) and n.name == name
        )
        fn.decorator_list = []
        exec(compile(ast.Module(body=[fn], type_ignores=[]), name, 'exec'), ns)
    sec = {
        'created': 0, 'updated': 0, 'skipped': 0,
        'created_names': [], 'updated_names': [], 'skipped_names': [],
    }
    assert ns['_should_write'](sec, False, False, 'NewCo', True) is False
    assert sec['created'] == 1 and sec['created_names'] == ['NewCo']
    assert ns['_should_write'](sec, True, False, 'OldCo', True) is False
    assert sec['skipped'] == 1 and sec['skipped_names'] == ['OldCo']
    assert ns['_should_write'](sec, True, True, 'OldCo', True) is False
    assert sec['updated'] == 1
    assert ns['_should_write'](sec, False, False, 'Live', False) is True


def test_json_import_wizards_review_before_write():
    wizards = Path(__file__).resolve().parents[1] / 'common' / 'wizard'
    upload_forms = (
        'import_users_wizard_views.xml',
        'import_agents_wizard_views.xml',
        'import_servers_wizard_views.xml',
        'import_external_servers_wizard_views.xml',
        'import_whitelist_wizard_views.xml',
        'skill_import_wizard_views.xml',
        'context_import_wizard_views.xml',
        'bundle_import_wizard_views.xml',
        'artifact_bundle_wizard_views.xml',
        'agent_skill_import_wizard_views.xml',
        'agent_context_import_wizard_views.xml',
        'config_backup_wizard_views.xml',
    )
    for name in upload_forms:
        src = (wizards / name).read_text(encoding='utf-8')
        assert 'name="action_preview"' in src, name
        assert 'string="Review"' in src, name


def test_json_import_lists_the_names_in_the_breakdown():
    wizards = _COMMON / 'wizard'
    for name in (
        'import_servers_wizard.py',
        'import_agents_wizard.py',
        'import_users_wizard.py',
        'import_external_servers_wizard.py',
        'import_whitelist_wizard.py',
    ):
        src = (wizards / name).read_text(encoding='utf-8')
        assert 'created_names=' in src, name
        assert 'updated_names=' in src, name
        assert 'skipped_names=' in src, name
        assert '_name_bucket_detail' not in src, name


def test_provider_api_key_is_not_copied():
    src = (_COMMON / 'models' / 'ai_provider.py').read_text(encoding='utf-8')
    field = src.split('    api_key = fields.Char(', 1)[1].split(')', 1)[0]
    assert 'copy=False' in field


def test_a_provider_twin_gets_its_own_model_row_and_name():
    """The chosen model lives in one provider's catalogue; the twin needs its own."""
    src = (_COMMON / 'models' / 'ai_provider.py').read_text(encoding='utf-8')
    copy = src.split('    def copy(self, default=None):', 1)[1].split('\n    def ', 1)[0]
    assert "vals['model_id'] = False" in copy
    assert "rec.model_id.copy({'provider_id': twin.id})" in copy
    assert "_('%s (copy)') % rec.name" in copy
    # Several at once (O19 list), not ensure_one.
    assert 'ensure_one' not in copy
    dup = src.split('    def action_duplicate(self):', 1)[1].split('\n    def ', 1)[0]
    assert 'ensure_ai_admin(self.env)' in dup
    stacks = _COMMON.parent / 'stacks'
    owl1 = (stacks / 'owl1' / 'pns_ai_mcp' / 'views' / 'ai_menus.xml').read_text(encoding='utf-8')
    assert 'action = records.action_duplicate()' in owl1
    owl2 = (stacks / 'owl2' / 'pns_ai_mcp' / 'views' / 'ai_menus.xml').read_text(encoding='utf-8')
    assert 'action_duplicate' not in owl2
