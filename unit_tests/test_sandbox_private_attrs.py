# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Private attributes are off limits to the sandbox (PNS-07).

Several private methods open their own cursor and commit, so the READ ONLY
cursor of a sandbox run does not hold them. Instead of naming them one by
one, every ``_name`` is closed but read-only model metadata. The same rule
runs at review (AST) and at execution (``guarded_getattr``).
"""
from __future__ import annotations

import pytest

from _load_addon import load_module

v = load_module('validators', 'controllers', 'validators.py')
v_base = load_module('validators_base', 'controllers', 'validators_base.py')
cb = load_module('context_builder', 'controllers', 'context_builder.py')

_BLOCKED_SNIPPETS = [
    "result = env['ai.safe.operation']._claim_execute(1)",
    "result = env['ai.safe.operation'].browse(1)._execute_plan_with_timeouts()",
    "result = env['ai.provider'].browse(1)._api_key_for_inference()",
    "result = getattr(env['res.partner'].browse(1), '_claim_execute')",
    "result = getattr(env['res.partner'].browse(1), '_exe' + 'cute_plan_with_timeouts')",
    "from operator import methodcaller\nresult = methodcaller('_execute_plan_with_timeouts')(env['ai.safe.operation'])",
    "result = '{0._execute_plan_with_timeouts}'.format(env['ai.safe.operation'])",
    "result = env['res.partner'].browse(1)._cr",
]

_ALLOWED_SNIPPETS = [
    "result = env['res.partner']._name",
    "result = sorted(env['res.partner']._fields)",
    "result = type({'a': 1}).__name__",
    "result = env['res.partner'].search([], limit=1).name",
]


@pytest.mark.parametrize('code', _BLOCKED_SNIPPETS)
def test_review_rejects_private_attributes(code):
    good, err, _write = v.validate_relaxaicode_source_ast(code + "\n")
    assert not good, code
    assert 'PRIVATE_ATTR' in err or 'PRIVILEGE' in err, err


@pytest.mark.parametrize('code', _ALLOWED_SNIPPETS)
def test_review_allows_metadata_and_public_names(code):
    good, err, _write = v.validate_relaxaicode_source_ast(code + "\n")
    assert good, err


def test_run_rejects_private_attributes():
    class _Thing(object):
        _name = 'res.partner'
        _fields = {}

        def _execute_plan_with_timeouts(self):
            return 'ran'

    thing = _Thing()
    assert cb.guarded_getattr(thing, '_name') == 'res.partner'
    assert cb.guarded_getattr(thing, '_fields') == {}
    with pytest.raises(AttributeError):
        cb.guarded_getattr(thing, '_execute_plan_with_timeouts')
    with pytest.raises(AttributeError):
        cb.guarded_getattr(thing, '_exe' + 'cute_plan_with_timeouts')
    with pytest.raises(AttributeError):
        cb.guarded_attrgetter('_execute_plan_with_timeouts')
    with pytest.raises(AttributeError):
        cb.guarded_methodcaller('_claim_execute')


def test_every_private_name_is_blocked_but_the_exceptions():
    for name in ('_claim_execute', '_register_hook', '_compute_x', '_x'):
        assert v_base.blocked_private_attr(name), name
    for name in v_base.RELAXAICODE_PRIVATE_ATTR_EXCEPTIONS:
        assert not v_base.blocked_private_attr(name), name
    assert not v_base.blocked_private_attr('name')
    assert not v_base.blocked_private_attr('api_key')
