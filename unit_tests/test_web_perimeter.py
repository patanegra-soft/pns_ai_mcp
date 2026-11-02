# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Web perimeter: what RPC can reach and what a turn can set off.

A method without a leading underscore is reachable through call_kw. The
ones below run as the system, write logs or spend a provider: they stay
private. Plans run with the rights of whoever asked for them.
"""
import re
from pathlib import Path
from types import SimpleNamespace

from common.utils.fetch_url_safe import non_public_peer_error

_ROOT = Path(__file__).resolve().parents[1]


def _src(*parts):
    return (_ROOT.joinpath(*parts)).read_text(encoding='utf-8')


def test_system_doors_are_private():
    public = {
        ('common', 'models', 'ai_context_disk.py'): ('unlink_retired_from_module',),
        ('common', 'models', 'ai_skill_disk.py'): ('unlink_retired_from_module',),
        ('common', 'models', 'key_pin_desk.py'): (
            'collect', 'collect_pin', 'touch', 'close', 'supply'),
        ('common', 'models', 'ai_execution_engine.py'): (
            'resolve_provider', 'log_role_without_provider', 'log_provider_failover',
            'log_provider_llm_request', 'log_provider_llm_response',
            'log_llm_inference', 'log_provider_inference'),
        ('common', 'models', 'ai_skill_authoring.py'): (
            'author_param_schema', 'author_param_help', 'rewrite_code_for_params'),
        ('common', 'models', 'safe_operation.py'): ('cleanup_stuck_state',),
        ('common', 'models', 'api_result_cache.py'): ('gc_expired',),
        ('common', 'models', 'fetch_cache.py'): ('gc_expired',),
        ('common', 'models', 'mcp_user.py'): (
            'register_mcp_client', 'get_last_mcp_client_label'),
    }
    for parts, names in public.items():
        src = _src(*parts)
        for name in names:
            assert not re.search(r'\n    def %s\(' % name, src), (parts[-1], name)
    engine = _src('common', 'models', 'ai_execution_engine.py')
    assert 'def _chat_completion(self, agent_code' in engine
    assert 'def chat_completion(self, agent_code' not in engine


def test_crons_call_the_private_cleaners():
    for stack in ('owl1', 'owl2'):
        for name in ('fetch_cache_cron.xml', 'api_result_cache_cron.xml'):
            xml = _src('stacks', stack, 'pns_ai_mcp', 'data', name)
            assert 'model._gc_expired()' in xml


def test_safe_operation_rows_are_opened_and_run_by_the_system():
    src = _src('common', 'models', 'safe_operation.py')
    assert "'Only the system can open a supervised operation.'" in src
    assert 'self.env(user=self.user_id.id) if self.user_id else self.env' in src
    assert 'or SUPERUSER_ID' not in src


def test_system_action_writes_as_the_real_user():
    src = _src('common', 'models', 'ai_system_action.py')
    assert 'user_add_group(user.with_user(self.env.uid), grp)' in src
    assert 'user_remove_group(user.with_user(self.env.uid), grp)' in src
    assert src.count('self._require_settings()') == 3


def test_safe_choice_is_read_only_for_users():
    csv = _src('common', 'security', 'ir.model.access.csv')
    assert 'model_ai_safe_choice,base.group_user,1,0,0,0' in csv


def test_skill_param_cache_follows_its_skill():
    xml = _src('common', 'security', 'security.xml')
    assert 'ai_skill_param_cache_user_rule' in xml
    assert "('skill_id.owner_id', '=', user.id)" in xml


def test_server_command_args_are_admin_secrets():
    src = _src('common', 'models', 'external_server.py')
    assert "_pns_secret_fields = ('auth_token', 'command_args', 'env_vars', 'config_json')" in src


def test_sandbox_cannot_send_mail_or_run_actions():
    src = _src('common', 'controllers', 'validators_base.py')
    block = src.split('RELAXAICODE_SIDE_EFFECT_METHODS = frozenset({', 1)[1].split('})', 1)[0]
    for name in ('send_email', 'send', 'send_mail', 'run', 'method_direct_trigger'):
        assert "'%s'," % name in block


def test_publish_check_runs_as_an_untrusted_turn():
    src = _src('common', 'utils', 'skill_runtime.py')
    assert 'skill_publish_check=True, pns_ai_untrusted_turn=True' in src


def _resp(peer):
    sock = SimpleNamespace(getpeername=lambda: (peer, 443))
    return SimpleNamespace(raw=SimpleNamespace(_connection=SimpleNamespace(sock=sock)))


def test_peer_ip_is_checked_after_connecting(monkeypatch):
    monkeypatch.delenv('HTTPS_PROXY', raising=False)
    monkeypatch.delenv('https_proxy', raising=False)
    url = 'https://example.com/x'
    assert non_public_peer_error(_resp('93.184.216.34'), url) == ''
    assert 'internal' in non_public_peer_error(_resp('127.0.0.1'), url)
    assert 'internal' in non_public_peer_error(_resp('169.254.169.254'), url)
    assert 'internal' in non_public_peer_error(_resp('::ffff:10.0.0.1'), url)
    assert non_public_peer_error(SimpleNamespace(raw=None), url) == ''
