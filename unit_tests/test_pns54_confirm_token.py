# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""PNS-54: confirm from the card token, not from a public RPC method."""
from pathlib import Path
from _load_addon import safe_plan_source

_ROOT = Path(__file__).resolve().parents[1]
_COMMON = _ROOT / 'common'
_OP = (_COMMON / 'models' / 'safe_operation.py').read_text(encoding='utf-8')
_UI = (_COMMON / 'controllers' / 'verification_ui.py').read_text(encoding='utf-8')
_RUN = (_COMMON / 'utils' / 'engine_tool_run.py').read_text(encoding='utf-8')
_PLAN = safe_plan_source()
_ENGINE = (_COMMON / 'utils' / 'agent_engine.py').read_text(encoding='utf-8')
_CONST = (_COMMON / 'constants.py').read_text(encoding='utf-8')
_SIDE = (_COMMON / 'controllers' / 'validators_base.py').read_text(encoding='utf-8')


def test_confirm_methods_are_private():
    for name in (
        'confirm_by_user',
        'resolve_confirm',
        'resolve_execute',
        'resolve_confirm_and_execute',
    ):
        assert '    def %s(' % name not in _OP, name
        assert '    def _%s(' % name in _OP, name
    assert '    def action_confirm_and_execute(' in _OP


def test_card_endpoints_require_the_token():
    assert 'def _gate_card_token' in _UI
    assert '_confirm_token_ok' in _UI
    assert 'need_wait=True' in _UI
    confirm = _UI.split('def confirm(')[1].split('def execute(')[0]
    execute = _UI.split('def execute(')[1].split('def cancel(')[0]
    assert "error': gated" in confirm
    assert "error': gated" in execute
    assert '_resolve_confirm' in confirm
    assert '_resolve_execute' in execute
    assert '_consume_confirm_token' in execute
    assert 'resolve_confirm(' not in confirm.replace('_resolve_confirm', '')


def test_card_payload_mints_a_token_and_peek_does_not():
    card = _OP.split('def card_payload')[1].split('def pending_card_payloads')[0]
    assert '_mint_confirm_token' in card
    assert "payload['confirm_token']" in card
    pend = _OP.split('def pending_card_payloads')[1].split('def action_export_operations')[0]
    assert 'mint_token=True' in pend
    assert 'mint_token=mint_token and op.verification_id not in held' in pend


def test_sse_card_gets_the_token_tool_json_does_not():
    after = _RUN.split('def _tool_loop_after_plan_request')[1].split(
        'def _tool_loop_after_plan_status',
    )[0]
    assert "event['confirm_token']" in after
    assert '_mint_card_token' in after
    mint = _RUN.split('def _mint_card_token')[1].split(
        'def _tool_loop_after_plan_request',
    )[0]
    assert '_mint_confirm_token' in mint
    assert "op.user_id.id != self.env.uid" in mint
    # The hash must be committed before the card can press Confirm.
    assert 'registry.cursor()' in mint
    assert 'ncr.commit()' in mint
    request = _PLAN.split('def request_safe_plan')[1].split(
        'def tool_safe_plan_request',
    )[0]
    assert "'confirm_token'" not in request
    assert '"confirm_token"' not in request
    fast = _ENGINE.split("if fast.get('verification_id'):")[1].split(
        '_pres_fp',
    )[0]
    assert "event['confirm_token']" in fast
    assert '_mint_card_token' in fast


def test_high_danger_wait_is_enforced_on_the_server():
    assert 'HIGH_CONFIRM_WAIT_SECONDS = 5' in _CONST
    assert '_confirm_wait_elapsed' in _OP
    assert 'HIGH_CONFIRM_WAIT_SECONDS' in _OP
    assert 'too_soon' in _UI


def test_sandbox_blocks_the_private_confirm_names():
    side = _SIDE.split('RELAXAICODE_SIDE_EFFECT_METHODS')[1].split('}', 1)[0]
    for name in (
        "'_confirm_by_user'",
        "'_resolve_confirm'",
        "'_resolve_execute'",
        "'_resolve_confirm_and_execute'",
        "'_mint_confirm_token'",
    ):
        assert name in side, name


def test_autorizaciones_button_stays_a_form_action():
    action = _OP.split('def action_confirm_and_execute')[1].split(
        'def action_execute_plan',
    )[0]
    assert '_resolve_confirm_and_execute' in action
    assert '_gate_card_token' not in action
