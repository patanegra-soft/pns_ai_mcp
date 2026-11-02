# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Write-ack copy follows the caller env, not the public HTTP request."""
from _load_addon import addon_file, safe_plan_source


def test_ack_translates_with_env():
    src = safe_plan_source()
    assert 'def _ack_tr' in src
    assert 'def _ack_lang' in src
    helper = src.split('def _ack_tr')[1].split('\ndef ')[0]
    assert '_get_source' in helper
    assert "'code'" in helper
    builder = src.split('def build_user_ack_message')[1].split('def _ack_field_lookup')[0]
    assert 'env=None' in builder
    assert '_ack_tr(env,' in builder
    assert "env=env" in src.split('def attach_verification_chat_hints')[1].split(
        'def _ack_field_lookup'
    )[0] or 'env=env,' in src.split('ack = build_user_ack_message')[1].split(')')[0]


def test_confirm_paths_pass_env():
    src = addon_file('models', 'safe_operation.py').read_text(encoding='utf-8')
    confirm = src.split('def _resolve_confirm')[1].split('def _resolve_execute')[0]
    assert confirm.rstrip().endswith('env=self.env,\n        )') or 'env=self.env' in confirm.split(
        'needs_execute'
    )[1]
    execute = src.split('def _resolve_execute')[1].split('def _resolve_confirm_and_execute')[0]
    assert '_ack_tr(self.env' in execute
    assert 'env=self.env' in execute
