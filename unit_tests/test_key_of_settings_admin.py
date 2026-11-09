# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Every path that sets an MCP key asks whether the caller may set that one.

A Settings administrator's key is set only by the system, another Settings
administrator or that same person. The live checks are in
``common/tests/test_key_of_settings_admin.py``.
"""
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_USER = (_ROOT / 'common' / 'models' / 'mcp_user.py').read_text(encoding='utf-8')
_BACKUP = (_ROOT / 'common' / 'utils' / 'config_backup.py').read_text(encoding='utf-8')
_WIZARD = (_ROOT / 'common' / 'wizard' / 'import_users_wizard.py').read_text(encoding='utf-8')


def _body(src, name):
    return src.split('def %s' % name, 1)[1].split('\ndef ', 1)[0].split('\n    def ', 1)[0]


def test_key_admin_check_looks_at_whose_key_it_is():
    assert 'self._may_set_key_of(record.user_id)' in _body(_USER, '_ensure_key_admin')
    may = _body(_USER, '_may_set_key_of')
    assert "env.ref('base.group_system'" in may
    assert 'user.id == env.uid' in may
    assert 'env.su' in may


def test_generate_and_paste_go_through_the_check():
    assert 'self._ensure_key_admin()' in _body(_USER, 'action_generate_mcp_api_key')
    assert 'self._ensure_key_admin()' in _body(_USER, 'set_mcp_api_key')


def test_an_rpc_write_or_create_of_the_hash_is_checked():
    write = _body(_USER, 'write')
    assert "filtered_vals.get('mcp_api_key_hash') and not self.env.su" in write
    assert 'self._ensure_key_admin()' in write
    assert '_may_set_key_of(' in _body(_USER, 'create')


def test_both_imports_drop_the_key_and_keep_the_permissions():
    imp = _body(_BACKUP, '_import_users')
    assert "env['ai.mcp.user']._drop_key_unless_allowed(vals, user)" in imp
    assert "report['warnings'].append(key_warning)" in imp
    assert 'user_model._drop_key_unless_allowed(vals, odoo_user)' in _WIZARD
    drop = _body(_USER, '_drop_key_unless_allowed')
    assert "'mcp_api_key_hash', 'mcp_api_key_state', 'mcp_api_key_generated_date'" in drop
    assert 'is_ai_' not in drop


def test_the_messages_are_in_every_spanish_catalog():
    for stack, name in (('owl1', 'es.po'), ('owl2', 'es_ES.po'), ('owl3', 'es_ES.po')):
        po = (_ROOT / 'stacks' / stack / 'pns_ai_mcp' / 'i18n' / name).read_text(encoding='utf-8')
        assert '"Only a Settings administrator can set the API key of another Settings "' in po, stack
        assert '"%s is a Settings administrator: the API key was not imported (only a "' in po, stack


def test_read_sums_is_the_module_own():
    for path in (_ROOT / 'common').rglob('*.py'):
        src = path.read_text(encoding='utf-8')
        for line in src.splitlines():
            if 'pns_base' in line and 'import' in line:
                assert 'read_sums' not in line, path
    assert 'def read_sums(model, domain, field_names):' in (
        _ROOT / 'common' / 'utils' / 'compat.py'
    ).read_text(encoding='utf-8')
