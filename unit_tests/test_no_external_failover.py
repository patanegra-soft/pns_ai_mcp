# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""A provider with the tick stops the chain. Nothing after it is tried."""
from __future__ import annotations

import ast
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_ENGINE = (_ROOT / 'common' / 'models' / 'ai_execution_engine.py').read_text(encoding='utf-8')


class _P:
    def __init__(self, pid, tick=False):
        self.id = pid
        self.no_external_failover = tick


class _Chain(list):
    def browse(self, ids):
        by_id = {p.id: p for p in self}
        return _Chain(by_id[i] for i in ids)


def _cut():
    tree = ast.parse(_ENGINE)
    fn = next(
        n for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == '_without_external_after_local'
    )
    fn.decorator_list = []
    ns = {}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), 'engine', 'exec'), ns)
    return lambda chain: [p.id for p in ns['_without_external_after_local'](None, chain)]


def test_nothing_after_the_tick_is_tried():
    chain = _Chain([_P(1, True), _P(2), _P(3, True), _P(4)])
    assert _cut()(chain) == [1]


def test_providers_before_the_tick_stay():
    chain = _Chain([_P(1), _P(2, True), _P(3)])
    assert _cut()(chain) == [1, 2]


def test_no_tick_keeps_the_whole_chain():
    chain = _Chain([_P(1), _P(2), _P(3)])
    assert _cut()(chain) == [1, 2, 3]


def test_chain_builder_applies_the_cut():
    body = _ENGINE.split('def get_providers_for_agent', 1)[1].split('\n    def ', 1)[0]
    assert 'self._without_external_after_local(' in body
