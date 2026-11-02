# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Each SSE message checks the key again; idle sessions are dropped."""
from __future__ import annotations

from pathlib import Path

_COMMON = Path(__file__).resolve().parents[1] / 'common'
_MAIN = (_COMMON / 'controllers' / 'main.py').read_text(encoding='utf-8')
_STORE = (_COMMON / 'utils' / 'session_store.py').read_text(encoding='utf-8')


def _message_endpoint():
    start = _MAIN.index('def mcp_message_endpoint(self, agent_code=None')
    return _MAIN[start:_MAIN.index('\n    @http.route', start)]


def test_a_message_never_falls_back_to_the_superuser():
    body = _message_endpoint()
    assert 'SUPERUSER_ID)[' in body
    assert 'mcp_user_id or SUPERUSER_ID' not in body
    assert 'request.mcp_user_id = user.id' in body


def test_a_revoked_key_or_inactive_user_closes_the_session():
    body = _message_endpoint()
    check = body.index('hash_api_key(api_key)')
    assert 'not user.active' in body[check:]
    assert 'user.id != session.mcp_user_id' in body[check:]
    assert '_mcp_conversational_denied(user)' in body[check:]
    assert body.index('store.close(session_id)', check) < body.index('_handle_mcp_method')
    assert 'except Exception:\n            pass' not in body


def test_get_mcp_does_not_send_a_result_with_a_null_id():
    start = _MAIN.index('def mcp_endpoint_sse(self, agent_code=None')
    body = _MAIN[start:_MAIN.index('\n    @http.route', start)]
    assert 'status=405' in body
    assert '"id":null' not in body
    assert 'text/event-stream' not in body


def test_a_closed_session_ends_its_stream():
    start = _MAIN.index('def _sse_stream_generator')
    gen = _MAIN[start:_MAIN.index('\n    @http.route', start)]
    assert 'if store.get(session_id) is None:\n                        break' in gen


def test_idle_sessions_are_purged_by_last_activity():
    assert 'self.touched_at = self.created_at' in _STORE
    start = _STORE.index('def create')
    create = _STORE[start:_STORE.index('def get(', start)]
    assert 'self.cleanup_expired()' in create
    pending = _STORE[_STORE.index('def get_pending'):_STORE.index('def close')]
    assert 'session.touched_at = datetime.utcnow()' in pending
    cleanup = _STORE[_STORE.index('def cleanup_expired'):]
    assert 'session.touched_at' in cleanup
    assert 'session.created_at' not in cleanup
