# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""A tool that raises leaves no half-done writes on the request cursor."""
from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_MAIN = (_ROOT / 'common' / 'controllers' / 'main.py').read_text(encoding='utf-8')
_ENGINE = (
    _ROOT / 'common' / 'utils' / 'engine_tool_run.py'
).read_text(encoding='utf-8')


def test_the_request_cursor_is_rolled_back_before_the_error_is_answered():
    call = _MAIN.index('result = tool_function(self, arguments)')
    handler = _MAIN.index('except Exception as e:', call)
    rollback = _MAIN.index('request.env.cr.rollback()', handler)
    assert rollback < _MAIN.index("'code': -32603", handler)
    assert "request.env['base'].invalidate_cache()" in _MAIN[rollback:rollback + 200]


def test_the_chat_engine_rolls_back_a_failed_tool():
    run = _ENGINE.split('def _tool_loop_run_tool', 1)[1].split('\n    def ', 1)[0]
    handler = run.index('except Exception as e:')
    drop = run.index('self._drop_failed_tool_writes()', handler)
    assert drop < run.index('json.dumps({"error": str(e)})', handler)
    helper = _ENGINE.split('def _drop_failed_tool_writes', 1)[1].split(
        '\n    def ', 1,
    )[0]
    # Engine shares Chatboo's turn cursor: a full rollback would undo
    # the session/job. Isolate the tool with a savepoint instead.
    assert 'self.env.cr.rollback()' not in helper
    assert 'turn.last_retry_error' in run
    isolated = _ENGINE.split('def _run_tool_in_savepoint', 1)[1].split(
        '\n    def ', 1,
    )[0]
    assert 'SAVEPOINT' in isolated
    assert 'ROLLBACK TO SAVEPOINT' in isolated
    assert 'TestCursor' in isolated
