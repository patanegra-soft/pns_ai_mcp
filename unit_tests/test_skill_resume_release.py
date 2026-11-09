# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""A skill waiting for arguments must not swallow the next question forever.

``/skill`` with no args paints the ask card and waits. If the next message
(no slash) fills none of its parameters, the engine releases the skill and
the message goes to the normal turn, instead of painting the card again.
"""
from pathlib import Path

_SRC = (
    Path(__file__).resolve().parents[1] / 'common' / 'utils' / 'agent_engine.py'
).read_text(encoding='utf-8')


def _slash_body():
    return _SRC.split('    def _run_slash_command(', 1)[1].split('\n    def ', 1)[0]


def test_resume_marks_the_command_as_resumed():
    head = _SRC.split('command = (prior_active_skill_code, reply)', 1)[1][:200]
    assert 'resumed = True' in head
    assert 'resumed=resumed' in _SRC


def test_unmapped_reply_releases_before_any_help_card():
    body = _slash_body()
    release = body.index("tool_name='skill_args_release'")
    card = body.index("norm_params.get('_skill_args_missing')")
    assert release < card
    branch = body[body.rindex('if (', 0, release):card]
    assert 'resumed' in branch
    assert "{'event': 'active_skill', 'code': None, 'params': {}}" in branch
    assert 'return False, message' in branch


def test_explicit_slash_still_paints_the_card():
    body = _slash_body()
    assert 'asking=bool(norm_params.get(\'_skill_args_missing\'))' in body
