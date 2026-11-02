# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Pending cards are a read of ai.safe.operation, not a second queue."""
from _load_addon import addon_file


def test_pending_route_reads_model_helper():
    src = addon_file('controllers', 'verification_ui.py').read_text(encoding='utf-8')
    assert "/pns_ai_mcp/verification/pending" in src
    assert 'pending_card_payloads' in src
    assert 'auth=' in src


def test_model_helper_is_search_not_create():
    src = addon_file('models', 'safe_operation.py').read_text(encoding='utf-8')
    start = src.index('def pending_card_payloads')
    chunk = src[start:start + 800]
    assert 'create_verification' not in chunk
    assert "status', '=', 'pending'" in chunk
    assert 'self.env.uid' in chunk
