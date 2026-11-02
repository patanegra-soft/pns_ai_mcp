# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""A tool-call parameter tag glued after the script is not Python."""
from __future__ import annotations

import ast

from _load_addon import load_module

v_repair = load_module('validators_repair', 'controllers', 'validators_repair.py')


_SCRIPT = (
    "result = {}\n"
    "result['__title__'] = 'Rentabilidad (%d)' % year\n"
)


def test_trailing_parameter_tag_is_dropped():
    leaked = (
        _SCRIPT
        + '</parameter name="summary" string="true">'
        + 'Rentabilidad por grupo analítico 2025\n'
    )
    repaired, changed = v_repair.strip_leaked_tool_markup(leaked)
    assert changed
    ast.parse(repaired)
    assert 'parameter' not in repaired
    assert "result['__title__']" in repaired


def test_tag_glued_to_the_last_line_is_cut_when_the_prefix_parses():
    leaked = _SCRIPT.rstrip('\n') + '</parameter name="summary">titulo\n'
    repaired, changed = v_repair.strip_leaked_tool_markup(leaked)
    assert changed
    ast.parse(repaired)
    assert 'parameter' not in repaired


def test_parameter_word_inside_a_string_stays():
    code = "result = {'note': '</parameter name=\"x\">hi'}\n"
    repaired, changed = v_repair.strip_leaked_tool_markup(code)
    assert not changed
    assert repaired == code
