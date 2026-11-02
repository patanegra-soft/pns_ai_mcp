# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Pure-Python tests (pytest, no Odoo runtime)."""
import re

from _load_addon import load_module

_mcp_correlation = load_module('mcp_correlation', 'utils', 'mcp_correlation.py')


def test_new_turn_id_format():
    tid = _mcp_correlation.new_turn_id()
    assert len(tid) == 4
    assert re.match(r'^[A-Z0-9]{4}$', tid)


def test_prefixed_turn_cannot_group_with_a_chatboo_chip():
    chip = _mcp_correlation.new_turn_id()
    walkie = _mcp_correlation.new_turn_id(prefix='S')
    assert re.match(r'^[A-Z0-9]{4}$', chip)
    assert re.match(r'^S[A-Z0-9]{4}$', walkie)
    assert len(walkie) != len(chip)
    dirty = _mcp_correlation.new_turn_id(prefix='s-')
    assert re.match(r'^S[A-Z0-9]{4}$', dirty)


def test_ensure_turn_uses_the_request_prefix():
    class _Req(object):
        pass

    req = _Req()
    req.mcp_turn = None
    req.mcp_turn_prefix = 'S'
    req.mcp_turn_step_counter = None
    tid = _mcp_correlation.ensure_turn(req)
    assert re.match(r'^S[A-Z0-9]{4}$', tid)
    assert req.mcp_turn == tid


def test_engine_and_a_job_thread_share_one_step_count():
    """A side call in a job thread (no request) steps between engine rows."""
    tid = _mcp_correlation.new_turn_id(prefix='T')
    _mcp_correlation.open_turn_steps(tid)
    assert _mcp_correlation.claim_turn_step(tid) == 1
    assert _mcp_correlation.claim_turn_step(tid, seed=lambda: 99) == 2
    assert _mcp_correlation.claim_turn_step(tid) == 3
    _mcp_correlation.open_turn_steps(tid)
    assert _mcp_correlation.claim_turn_step(tid) == 1


def test_unknown_turn_continues_after_the_stored_rows():
    tid = _mcp_correlation.new_turn_id(prefix='U')
    assert _mcp_correlation.claim_turn_step(tid, seed=lambda: 5) == 6
    assert _mcp_correlation.claim_turn_step(tid, seed=lambda: 5) == 7
    assert _mcp_correlation.claim_turn_step('') is None


def test_engine_steps_come_from_the_shared_count():
    from _load_addon import addon_file
    engine = addon_file('utils', 'agent_engine.py').read_text(encoding='utf-8')
    step = engine.split('def _next_step', 1)[1].split('\n    def ', 1)[0]
    assert 'claim_turn_step(self._turn_corr)' in step
    assert 'open_turn_steps(self._turn_corr)' in engine
    log = addon_file('models', 'ai_execution_engine.py').read_text(encoding='utf-8')
    resolve = log.split('def _resolve_log_threading', 1)[1].split('\n    def ', 1)[0]
    assert 'claim_turn_step(' in resolve
