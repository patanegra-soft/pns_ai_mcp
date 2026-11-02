# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Methods that work in sudo are not callable over RPC.

Odoo exposes every model method whose name does not start with ``_``. These
ones write or read as the superuser for the engine, so they are private.
The two that an administrator uses check the group before writing.
"""
import ast
from pathlib import Path

_MODELS = Path(__file__).resolve().parents[1] / 'common' / 'models'

_PRIVATE = {
    'key_pin_block.py': ('is_blocked', 'note_failure', 'release_all'),
    'mcp_user.py': ('redeem_key_pin', 'consume_key_pin'),
    'fetch_cache.py': ('get_cached', 'store'),
    'api_result_cache.py': ('get_cached', 'store'),
    'url_whitelist.py': ('ensure_domain_whitelisted',),
    'ai_skill_param_cache.py': ('lookup_for_skill', 'remember_for_skill'),
    'ai_skill.py': ('lookup_param_cache', 'remember_param_cache'),
    'ai_log.py': ('create_log_entry',),
    'ai_change_journal.py': ('record_failed_plan',),
    'ai_execution_engine.py': ('choose',),
    'safe_operation.py': (
        'confirm_by_user',
        'resolve_confirm',
        'resolve_execute',
        'resolve_confirm_and_execute',
    ),
}


def _src(name):
    return (_MODELS / name).read_text(encoding='utf-8')


def _method(src, name):
    return src.split('    def %s(' % name, 1)[1].split('\n    def ', 1)[0]


def _function(src, name):
    return next(
        n for n in ast.walk(ast.parse(src))
        if isinstance(n, ast.FunctionDef) and n.name == name
    )


def test_engine_only_methods_are_private():
    for filename, names in _PRIVATE.items():
        src = _src(filename)
        for name in names:
            assert '    def %s(' % name not in src, (filename, name)
            assert '    def _%s(' % name in src, (filename, name)


def test_api_key_writes_check_the_admin_first():
    src = _src('mcp_user.py')
    for name in ('set_mcp_api_key', 'action_generate_mcp_api_key'):
        body = _function(src, name).body
        if ast.get_docstring(_function(src, name)) is not None:
            body = body[1:]
        assert "attr='_ensure_key_admin'" in ast.dump(body[0]), name
    guard = _method(src, '_ensure_key_admin')
    assert "has_group('pns_ai_mcp.group_ai_admin')" in guard
    assert 'raise AccessError(' in guard


def test_a_pin_without_an_address_still_counts():
    src = _src('key_pin_block.py')
    ns = {}
    tree = ast.parse(src)
    keep = [
        n for n in tree.body
        if (isinstance(n, ast.Assign) and n.targets[0].id == '_NO_IP')
        or (isinstance(n, ast.FunctionDef) and n.name == '_ip_key')
    ]
    exec(compile(ast.Module(body=keep, type_ignores=[]), 'key_pin_block', 'exec'), ns)
    assert ns['_ip_key']('') == ns['_ip_key'](None) == ns['_ip_key'](' ') != ''
    assert ns['_ip_key'](' 10.0.0.1 ') == '10.0.0.1'
    body = ast.dump(_function(src, '_is_blocked'))
    assert "id='_ip_key'" in body


def test_a_failed_plan_is_journaled_redacted():
    src = _src('ai_change_journal.py')
    body = _method(src, '_record_failed_plan')
    assert "'intended_values': redact_record(step.get('values') or {})" in body
