# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""PAAP write-auth invariants I1–I10: each one has a test that says so."""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_COMMON = _ROOT / 'common'
_TAG = re.compile(r'^PAAP I(\d+)\b')
# write-auth.md, spec 0.1: I1 … I10.
_INVARIANTS = set(range(1, 11))


def _tagged_tests():
    found = {}
    for folder in (_ROOT / 'unit_tests', _COMMON / 'tests'):
        for path in folder.glob('test_*.py'):
            tree = ast.parse(path.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if not isinstance(node, ast.FunctionDef) or not node.name.startswith('test'):
                    continue
                match = _TAG.match(ast.get_docstring(node) or '')
                if match:
                    found.setdefault(int(match.group(1)), []).append(
                        '%s::%s' % (path.name, node.name),
                    )
    return found


def test_paap_i5_the_pending_plan_keeps_no_confirmation_secret():
    """PAAP I5: no PIN or code to type; the pending row stores no confirmation secret."""
    model = (_COMMON / 'models' / 'safe_operation.py').read_text(encoding='utf-8')
    names = re.findall(r'^    (\w+) = fields\.', model, re.M)
    assert names
    assert not [n for n in names if re.search(r'pin|secret|password|passcode|otp', n)]
    for path in _COMMON.rglob('*.py'):
        assert 'PIN_EXPIRY_MINUTES' not in path.read_text(encoding='utf-8'), path


def test_every_invariant_has_a_tagged_test():
    found = _tagged_tests()
    assert set(found) == _INVARIANTS, sorted(_INVARIANTS - set(found))


def test_the_checklist_points_to_the_tags():
    path = _ROOT / 'docs' / 'paap_conformance_checklist.md'
    if not path.is_file():
        pytest.skip('internal docs are not in this tree')
    doc = path.read_text(encoding='utf-8')
    assert 'PAAP I' in doc
    assert 'test_paap_invariants.py' in doc
