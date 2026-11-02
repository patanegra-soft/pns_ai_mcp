# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Chatboo must never dump ERROR (-32603) / Details JSON on ACL denials."""
from __future__ import annotations

from _load_addon import load_module

ux = load_module('error_ux', 'utils', 'error_ux.py')

_RAW = (
    "ERROR (-32603): Error executing code: Por restricciones de seguridad "
    "no tienes permiso para acceder a los informes de 'Cuenta' "
    "(account.account).\n"
    "Ponte en contacto con tu administrador para pedirle acceso si es "
    "necesario.\n"
    'Details: {\n  "error_type": "AccessError"\n}'
)


def test_relaxaicode_asks_for_the_join_hint():
    from _load_addon import relaxaicode_source
    src = relaxaicode_source()
    assert 'format_join_sequence_hint' in src


def test_join_of_row_dicts_hints_to_return_rows():
    hint = ux.format_join_sequence_hint(
        'sequence item 0: expected str instance, dict found'
    )
    assert hint is not None
    assert 'str.join needs strings' in hint
    assert "{'data': rows}" in hint
    assert ux.format_join_sequence_hint('bad operand type') is None


def test_bool_membership_hint_says_empty_text_is_false():
    hint = ux.format_bool_membership_hint(
        "argument of type 'bool' is not iterable"
    )
    assert hint is not None
    assert "(value or '')" in hint
    assert ux.format_bool_membership_hint('other') is None


def test_int_id_hint_says_the_value_is_already_the_id():
    hint = ux.format_int_id_hint("'int' object has no attribute 'id'")
    assert hint is not None
    assert 'already the id' in hint
    assert ux.format_int_id_hint('other') is None


def test_strips_jsonrpc_and_details():
    cleaned = ux.strip_tool_error_wrappers(_RAW)
    assert 'ERROR' not in cleaned
    assert 'Details' not in cleaned
    assert 'error_type' not in cleaned
    assert 'Cuenta' in cleaned
    assert 'administrador' in cleaned


def test_detects_permission_denial():
    msg, is_perm = ux.humanize_exhausted_tool_error(_RAW)
    assert is_perm
    assert msg.startswith('Por restricciones')
    assert '(-32603)' not in msg


def test_catalogue_reject_nudges_get_context_not_python_retry():
    raw = (
        'ERROR (-32602): AST Validation Error: [PROHIBITED:CONTEXT_CATALOGUE] '
        'RelaxAICode cannot inspect ai.context (knowledge catalogue).'
    )
    assert ux.is_catalogue_inspect_reject(raw)
    nudge = ux.retry_nudge_after_tool_error(raw)
    assert 'get_context' in nudge
    assert 'Do NOT call relaxaicode' in nudge
    assert 'already injected' in nudge
    assert 'corrected arguments/code' not in nudge
    default = ux.retry_nudge_after_tool_error('name "foo" is not defined')
    assert 'corrected arguments/code' in default


def test_skill_catalogue_reject_nudges_prose_not_get_context():
    raw = (
        'ERROR (-32602): AST Validation Error: [PROHIBITED:SKILL_CATALOGUE] '
        'RelaxAICode cannot inspect ai.skill (slash catalogue).'
    )
    assert ux.is_catalogue_inspect_reject(raw)
    nudge = ux.retry_nudge_after_tool_error(raw)
    assert 'get_context' not in nudge
    assert 'Do NOT call relaxaicode' in nudge
    assert 'slash' in nudge.lower()
    assert 'copy another skill' in nudge
    assert 'corrected arguments/code' not in nudge


def test_action_catalogue_reject_nudges_ask_not_get_context():
    raw = (
        'ERROR (-32602): AST Validation Error: [PROHIBITED:ACTION_CATALOGUE] '
        'RelaxAICode cannot inspect ai.trusted.action (action catalogue).'
    )
    assert ux.is_catalogue_inspect_reject(raw)
    nudge = ux.retry_nudge_after_tool_error(raw)
    assert 'get_context' not in nudge
    assert 'Do NOT call relaxaicode' in nudge
    assert 'safe_plan_request' in nudge
    assert 'ask ONE short sentence' in nudge
    assert 'corrected arguments/code' not in nudge
    assert ux.inspect_spin_nudge(1) == ''
    assert 'you already inspected' in ux.inspect_spin_nudge(2)


def test_non_permission_still_strips_wrappers():
    raw = (
        'ERROR (-32603): Error executing code: name "foo" is not defined\n'
        'Details: {\n  "error_type": "NameError"\n}'
    )
    msg, is_perm = ux.humanize_exhausted_tool_error(raw)
    assert not is_perm
    assert msg == 'name "foo" is not defined'


def test_groupby_computed_field_retries_and_stays_off_the_bubble():
    raw = (
        "ERROR (-32603): Error executing code: Fields in 'groupby' must be "
        "database-persisted fields (no computed fields)\n"
        'Details: {"error_type": "ValueError"}'
    )
    assert ux.is_groupby_computed_field_error(raw)
    hint = ux.groupby_stored_field_retry_hint()
    assert 'store=True' in hint
    assert ux.retry_nudge_after_tool_error(raw) == hint
    msg, is_perm = ux.humanize_exhausted_tool_error(raw)
    assert msg is None
    assert not is_perm
    msg_hint, _perm = ux.humanize_exhausted_tool_error(hint)
    assert msg_hint is None


def test_redirect_warning_keeps_the_sentence_not_the_tuple():
    class RedirectWarning(Exception):
        def __init__(self, message, action, button, extra=None):
            super(RedirectWarning, self).__init__(message, action, button)
            self.args = (message, action, button, extra)

    msg = (
        "Agent 'pns_secretary' has no provider failovers configured, "
        "and 2 active providers exist.\n\n"
        "Open AI → Agents, edit the agent, and assign providers "
        "in priority order."
    )
    exc = RedirectWarning(msg, 1520, 'Configure Agent', None)
    out = ux.exception_user_text(exc)
    assert out == msg
    assert '1520' not in out
    assert 'Configure Agent' not in out
    assert 'None' not in out
    dumped = str(exc)
    assert '1520' in dumped
    assert 'Configure Agent' in dumped
