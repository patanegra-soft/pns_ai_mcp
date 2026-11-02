# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""prompts/list has one system_prompt: the compiled bundle, not the core row."""
from __future__ import annotations

from pathlib import Path

_COMMON = Path(__file__).resolve().parents[1] / 'common'
_LIST = (_COMMON / 'models' / 'ai_context_composition.py').read_text(encoding='utf-8')
_MAIN = (_COMMON / 'controllers' / 'main.py').read_text(encoding='utf-8')


def test_listable_catalogue_skips_the_compiled_bundle_name():
    body = _LIST.split('def get_listable_for_mcp', 1)[1].split('\n    @api.model', 1)[0]
    assert "if base == 'system_prompt':" in body
    assert 'continue' in body


def test_prompts_list_does_not_append_a_second_system_prompt():
    body = _MAIN.split('def _mcp_prompts_list', 1)[1].split('\n    def _mcp_prompts_get', 1)[0]
    assert "'name': 'system_prompt'" in body
    assert "if name == 'system_prompt':" in body
    assert body.count("'name': 'system_prompt'") == 1
