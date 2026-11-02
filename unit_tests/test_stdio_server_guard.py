# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""A stdio server is set up by a Settings admin and never hangs or leaks the host env."""
from __future__ import annotations

from pathlib import Path

_COMMON = Path(__file__).resolve().parents[1] / 'common'
_CLIENT = (_COMMON / 'utils' / 'mcp_client.py').read_text(encoding='utf-8')
_DRIVER = (_COMMON / 'lib' / 'api' / 'drivers' / 'mcp_driver.py').read_text(encoding='utf-8')
_SERVER = (_COMMON / 'models' / 'external_server.py').read_text(encoding='utf-8')


def _between(src, start, end):
    i = src.index(start)
    return src[i:src.index(end, i + len(start))]


def test_the_child_gets_a_small_environment():
    start = _between(_CLIENT, 'def _stdio_start', 'def _stdio_stderr_tail')
    assert 'dict(os.environ)' not in start
    assert 'for k in _STDIO_INHERITED_ENV if k in os.environ' in start
    assert 'stderr=self._stderr' in start
    assert 'stderr=subprocess.PIPE' not in _CLIENT


def test_reads_time_out_and_notifications_do_not_wait():
    send = _between(_CLIENT, 'def _stdio_send', 'def _send')
    assert "if 'id' not in payload:" in send
    assert send.index("if 'id' not in payload:") < send.index('self._stdio_readline()')
    assert '.readline()' not in send
    read = _between(_CLIENT, 'def _stdio_readline', 'def _stdio_send')
    assert 'sel.select(left)' in read


def test_the_driver_always_closes_the_client():
    assert _DRIVER.count('finally:\n            client.close()') == 3


def test_only_settings_admins_set_the_command():
    check = _between(_SERVER, 'def _check_may_set_stdio_command', 'def write')
    assert "has_group('base.group_system')" in check
    assert "'[]', '{}'" in check
    create = _between(_SERVER, 'def create', 'def _check_may_set_stdio_command')
    assert 'self._check_may_set_stdio_command(vals)' in create
    write = _between(_SERVER, '    def write(self, vals):', 'super().write(vals)')
    assert 'self._check_may_set_stdio_command(vals)' in write


def test_discover_and_test_need_an_ai_admin():
    for name in ('def action_discover_tools', 'def action_test_connection'):
        body = _between(_SERVER, name, '\n    def ')
        assert 'ensure_ai_admin(self.env)' in body
