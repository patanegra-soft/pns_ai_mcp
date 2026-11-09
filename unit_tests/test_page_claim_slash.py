# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""The name of a slash command is not a word of the sentence.

``/dashboard`` once turned into a page because the early domain match read
``dashboard`` from the command itself. Only what follows the command is scored.
"""
from pathlib import Path

from _load_addon import load_module

es = load_module('engine_skills', 'utils', 'engine_skills.py')

_SRC = (
    Path(__file__).resolve().parents[1] / 'common' / 'utils' / 'engine_presentation.py'
).read_text(encoding='utf-8')


def _claim_body():
    return _SRC.split('    def _claim_page_turn(', 1)[1].split('\n    def ', 1)[0]


def test_claim_scores_the_arguments_not_the_command():
    body = _claim_body()
    assert 'self._parse_slash_command(message)' in body
    assert 'command[1] if command else' in body
    call = body.split('match_domains(', 1)[1][:80]
    assert call.lstrip().startswith('sentence,')


def test_slash_split_leaves_only_the_arguments():
    parse = es.SkillsMixin._parse_slash_command
    assert parse('/dashboard') == ('dashboard', '')
    assert parse('/dashboard on a page') == ('dashboard', 'on a page')
    assert parse('a sales dashboard') is None
