# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Users and provider roles travel between databases with what makes them work."""
import ast
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_BACKUP = (_ROOT / 'common' / 'utils' / 'config_backup.py').read_text(encoding='utf-8')
_USER = (_ROOT / 'common' / 'models' / 'mcp_user.py').read_text(encoding='utf-8')
_ROLE = (_ROOT / 'common' / 'models' / 'ai_provider_role.py').read_text(encoding='utf-8')
_STACKS = ('owl1', 'owl2', 'owl3')


def _body(src, name):
    return src.split('def %s' % name, 1)[1].split('\ndef ', 1)[0].split('\n    def ', 1)[0]


def _inverse_flags():
    """Boolean fields of ai.mcp.user that set a group when written."""
    tree = ast.parse(_USER)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
    flags = set()
    for node in cls.body:
        if not (isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)):
            continue
        call = node.value
        if getattr(call.func, 'attr', '') != 'Boolean':
            continue
        keys = {kw.arg for kw in call.keywords}
        if {'compute', 'inverse'} <= keys:
            flags.add(node.targets[0].id)
    return flags


def test_ai_permissions_are_fields_the_import_writes_back():
    flags = _inverse_flags()
    assert {'is_mcp_manager', 'is_ai_writer', 'is_ai_conversational'} <= flags
    export = _body(_USER, '_export_user_dict')
    assert 'export_record_dict(self' in export
    assert 'has_group' not in export
    assert "key_aliases={'is_ai_admin': 'is_mcp_manager'}" in _USER


def test_backup_and_bundle_carry_the_same_user_rows_as_the_list():
    export = _body(_BACKUP, 'export_selected_users')
    assert 'u._export_user_dict(include_secrets)' in export
    assert "mcp_api_key_state != 'generated'" not in export
    imp = _body(_BACKUP, '_import_users')
    assert '_import_vals_from_json_row(row)' in imp
    assert 'nothing restorable' not in imp
    assert 'Users.create' not in imp


def test_roles_list_export_names_who_holds_each_role():
    export = _body(_BACKUP, 'export_roles_with_holders')
    assert "row['providers'] = role.provider_ids.mapped('name')" in export
    assert 'export_roles_with_holders(roles)' in _body(_ROLE, 'action_export_roles')
    assert 'ensure_ai_admin(self.env)' in _body(_ROLE, 'action_export_roles')


def test_holders_are_set_from_each_provider_and_a_refusal_stays_in_its_row():
    imp = _body(_BACKUP, '_import_provider_roles')
    assert "if isinstance(row.get('providers'), list):" in imp
    assert '.create(' not in imp
    holders = _body(_BACKUP, '_set_role_holders')
    assert "provider.write({'role_ids': [command]})" in holders
    assert 'with env.cr.savepoint():' in holders
    assert '(4, role.id)' in holders and '(3, role.id)' in holders


def test_the_provider_backup_file_still_has_no_holders():
    """The bundle's provider_roles.json keeps its shape: holders ride on providers."""
    assert 'providers' not in _body(_BACKUP, '_role_row')


def test_roles_tools_are_wired_in_every_stack():
    wizard_init = (_ROOT / 'common' / 'wizard' / '__init__.py').read_text(encoding='utf-8')
    assert 'from . import ai_provider_role_tools_wizard' in wizard_init
    assert 'from . import import_provider_roles_wizard' in wizard_init
    acl = (_ROOT / 'common' / 'security' / 'ir.model.access.csv').read_text(encoding='utf-8')
    assert 'model_ai_provider_role_tools_wizard,group_ai_admin' in acl
    assert 'model_ai_import_provider_roles_wizard,group_ai_admin' in acl
    importer = (_ROOT / 'common' / 'wizard' / 'import_provider_roles_wizard.py').read_text(encoding='utf-8')
    assert 'ensure_ai_admin(self.env)' in importer
    manifests = [
        _ROOT / 'stacks' / 'owl1' / 'pns_ai_mcp' / '__manifest__.py',
        _ROOT / 'stacks' / 'owl1' / 'pns_ai_mcp' / '__manifest_o15__.py',
        _ROOT / 'stacks' / 'owl2' / 'pns_ai_mcp' / '__manifest__.py',
        _ROOT / 'stacks' / 'owl3' / 'pns_ai_mcp' / '__manifest__.py',
    ]
    for path in manifests:
        src = path.read_text(encoding='utf-8')
        assert "'wizard/ai_provider_role_tools_wizard_views.xml'" in src, path
        assert "'wizard/import_provider_roles_wizard_views.xml'" in src, path
    for stack in ('owl2', 'owl3'):
        addon = _ROOT / 'stacks' / stack / 'pns_ai_mcp'
        js = (addon / 'static' / 'src' / 'js' / 'ai_provider_role_action_buttons.js').read_text(encoding='utf-8')
        assert 'resModel === "ai.provider.role"' in js
        assert 'pns_ai_mcp.action_provider_role_tools_wizard' in js
        assert 'ai_provider_role_action_buttons.js' in (addon / '__manifest__.py').read_text(encoding='utf-8')
    owl1 = _ROOT / 'stacks' / 'owl1' / 'pns_ai_mcp'
    js = (owl1 / 'static' / 'src' / 'js' / 'ai_provider_role_tree_v14.js').read_text(encoding='utf-8')
    assert "this.modelName !== 'ai.provider.role'" in js
    assert 'ai_provider_role_tree_v14.js' in (owl1 / 'views' / 'assets.xml').read_text(encoding='utf-8')
    assert 'ai_provider_role_tree_v14.js' in (owl1 / '__manifest_o15__.py').read_text(encoding='utf-8')


def test_new_strings_are_in_every_spanish_catalog():
    for stack, name in (('owl1', 'es.po'), ('owl2', 'es_ES.po'), ('owl3', 'es_ES.po')):
        po = (_ROOT / 'stacks' / stack / 'pns_ai_mcp' / 'i18n' / name).read_text(encoding='utf-8')
        for msgid in (
            'msgid "%s provider role(s) exported."',
            'msgid "Provider Roles Tools"',
            'msgid "Import provider roles"',
            'msgid "Odoo user \'%s\' not found; skipped."',
        ):
            assert msgid in po, (stack, msgid)
