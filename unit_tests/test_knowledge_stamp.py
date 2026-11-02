# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Factory stamp is modules with ai/, not a fixed name list."""
from __future__ import annotations

from _load_addon import load_module

stamp = load_module('knowledge_stamp', 'utils', 'knowledge_stamp.py')


def test_format_stamp_sorts_and_joins():
    got = stamp.format_factory_knowledge_stamp([
        ('pns_geo', '1.0.119'),
        ('pns_ai_mcp', '3.1.422'),
    ])
    assert got == 'pns_ai_mcp:3.1.422|pns_geo:1.0.119'


def test_module_has_ai_knowledge(tmp_path):
    bare = tmp_path / 'bare'
    bare.mkdir()
    assert not stamp.module_has_ai_knowledge(str(bare))
    ctx = tmp_path / 'with_ai' / 'ai' / 'contexts'
    ctx.mkdir(parents=True)
    assert stamp.module_has_ai_knowledge(str(tmp_path / 'with_ai'))


def test_hooks_has_no_fixed_stamp_list():
    from _load_addon import addon_file

    src = addon_file('hooks.py').read_text(encoding='utf-8')
    assert '_FACTORY_STAMP_MODULES' not in src
    assert 'module_has_ai_knowledge' in src
