# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Every AI export asks for secrets; a copy without them never blanks the destination."""
from __future__ import annotations

import ast
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SRC = (_ROOT / 'common' / 'utils' / 'config_backup.py').read_text(encoding='utf-8')
_SERVER = (_ROOT / 'common' / 'models' / 'external_server.py').read_text(encoding='utf-8')
_PROVIDER = (_ROOT / 'common' / 'models' / 'ai_provider.py').read_text(encoding='utf-8')
_SETTINGS = (_ROOT / 'common' / 'models' / 'res_config_settings.py').read_text(encoding='utf-8')


def _server_methods():
    tree = ast.parse(_SERVER)
    cls = next(
        n for n in tree.body
        if isinstance(n, ast.ClassDef)
        and any(isinstance(s, ast.Assign) and getattr(s.value, 'value', None) == 'ai.api.server'
                for s in n.body)
    )
    wanted = {'_json_to_fields', '_keep_secrets_on_import'}
    body = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in wanted]
    for fn in body:
        fn.decorator_list = []
    module = ast.Module(body=[ast.ClassDef(
        name='Server', bases=[], keywords=[], body=body, decorator_list=[],
    )], type_ignores=[])
    return ast.fix_missing_locations(module)


class _Stored:
    _pns_secret_fields = ('auth_token', 'command_args', 'env_vars', 'config_json')

    def __init__(self, values):
        self.values = values

    def __getitem__(self, key):
        return self if isinstance(key, slice) else self.values[key]

    def __bool__(self):
        return True

    def sudo(self):
        return self


def _keep(stored, vals):
    def keep_existing_secrets(record, vals):
        for name in record._pns_secret_fields:
            if name in vals and vals[name] in ('', '{}', False, None) and record[name] not in ('', '{}'):
                vals.pop(name)
        return vals

    ns = {'json': json, 'keep_existing_secrets': keep_existing_secrets}
    exec(compile(_server_methods(), 'external_server', 'exec'), ns)
    record = type('Record', (ns['Server'], _Stored), {})(stored.values)
    return record._keep_secrets_on_import(vals)


def test_server_declares_its_secrets():
    assert "_pns_secret_fields = ('auth_token', 'command_args', 'env_vars', 'config_json')" in _SERVER
    assert "_pns_secret_fields = ('api_key',)" in _PROVIDER


def test_old_copy_without_secrets_keeps_destination_token():
    stored = _Stored({'auth_token': 'T0K3N', 'env_vars': '{"K": "v"}', 'config_json': '{}'})
    vals = {
        'code': 'x', 'auth_token': '', 'env_vars': '{}',
        'config_json': json.dumps({'x': {
            'type': 'sse', 'url': 'https://example.com/sse',
            'auth': {'type': 'bearer', 'header': 'Authorization'},
        }}),
    }
    out = _keep(stored, vals)
    assert 'config_json' not in out
    assert 'auth_token' not in out
    assert 'env_vars' not in out
    assert out['url'] == 'https://example.com/sse'


def test_copy_with_secrets_overwrites():
    stored = _Stored({'auth_token': 'OLD', 'env_vars': '{}', 'config_json': '{}'})
    out = _keep(stored, {'code': 'x', 'auth_token': 'NEW', 'env_vars': '{"K": "v"}'})
    assert out['auth_token'] == 'NEW'
    assert out['env_vars'] == '{"K": "v"}'


def test_every_export_asks_first():
    for src, methods in (
        (_PROVIDER, ('_pns_export_all_providers', '_pns_export_selected_providers')),
        (_SERVER, ('_pns_export_all_servers', '_pns_export_selected_servers')),
        (_SETTINGS, ('_pns_export_ai_config',)),
    ):
        for method in methods:
            assert "'%s'" % method in src
            assert 'def %s(self, include_secrets=False):' % method in src
    assert "self.env['pns.export.secrets.wizard'].ask(" in _SETTINGS
    assert 'ai_config_export_secrets' not in _SETTINGS
    for stack in ('owl1', 'owl2'):
        view = (_ROOT / 'stacks' / stack / 'pns_ai_mcp' / 'views' / 'res_config_settings_views.xml').read_text(encoding='utf-8')
        assert 'ai_config_export_secrets' not in view


def test_a_model_with_secrets_asks_and_names_the_file():
    """Read from disk: whoever declares secrets and writes an export asks first."""
    seen = []
    for path in sorted((_ROOT / 'common' / 'models').glob('*.py')):
        src = path.read_text(encoding='utf-8')
        if '_pns_secret_fields = (' not in src or 'build_export_filename(' not in src:
            continue
        seen.append(path.stem)
        assert "self.env['pns.export.secrets.wizard'].ask(" in src, path.name
        assert 'secrets=include_secrets' in src, path.name
    assert {'ai_provider', 'external_server', 'mcp_user'} <= set(seen)


def test_user_key_hash_is_a_secret():
    """PAAP I10: Only the hash of the MCP key is stored, and it is a secret."""
    user = (_ROOT / 'common' / 'models' / 'mcp_user.py').read_text(encoding='utf-8')
    assert "_pns_secret_fields = ('mcp_api_key_hash',)" in user
    assert 'def export_selected_users(users, include_secrets=False):' in _SRC
    assert 'u._export_user_dict(include_secrets)' in _SRC
    assert '}, include_secrets=include_secrets)' in user
    assert 'del include_secrets' not in _SRC
    # Without the key, the import does not mark a user as having one.
    assert "vals.pop('mcp_api_key_state', None)" in user


def test_bundle_and_backup_names_say_secrets():
    bundle = (_ROOT / 'common' / 'utils' / 'artifact_bundle.py').read_text(encoding='utf-8')
    assert 'secrets=include_secrets' in bundle
    assert 'secrets=with_secrets' in _SETTINGS


def test_backup_defaults_to_no_secrets():
    """PAAP I10: Exports leave secrets out unless the human ticks them."""
    assert 'def export_config(env, include_secrets=False):' in _SRC
    assert 'def export_selected_servers(servers, include_secrets=False):' in _SRC
    assert 'def export_selected_providers(providers, include_secrets=False):' in _SRC
    assert 'existing.write(keep_existing_secrets(existing, vals))' in _SRC
    assert 'existing.write(existing._keep_secrets_on_import(vals))' in _SRC
    wizard = (_ROOT / 'common' / 'wizard' / 'import_external_servers_wizard.py').read_text(encoding='utf-8')
    assert 'existing.write(existing._keep_secrets_on_import(vals))' in wizard


def test_full_import_wires_skills_with_the_overwrite_choice():
    tree = ast.parse(_SRC)
    fn = next(
        n for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == '_wire_skill_relations'
    )
    assert 'replace_existing' in [a.arg for a in fn.args.args]
    assert 'def import_config(env, data, replace_existing=True, dry_run=False):' in _SRC
    assert 'replace = bool(replace_existing)' in _SRC
    wizard = (_ROOT / 'common' / 'wizard' / 'config_backup_wizard.py').read_text(encoding='utf-8')
    assert 'replace_existing=self.replace_existing' in wizard


def test_settings_follow_include_secrets():
    assert "'settings': _export_settings(env, include_secrets)" in _SRC
    assert 'include_secrets=include_secrets,' in _SRC.split('def _export_settings', 1)[1]
    bundle = (_ROOT / 'common' / 'utils' / 'artifact_bundle.py').read_text(encoding='utf-8')
    assert '_export_settings(env, include_secrets)' in bundle
