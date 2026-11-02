# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Sandbox-module sync: opt-in collection, engine keys win, no addon names."""
from __future__ import annotations

import inspect
import logging

from _load_addon import load_module

cb = load_module('context_builder', 'controllers', 'context_builder.py')
sh = load_module('sandbox_helpers', 'utils', 'sandbox_helpers.py')


class _Rec(object):
    def sudo(self):
        return self


class _ProviderA(_Rec):
    _sandbox_helper_provider = True

    def sandbox_helpers(self):
        return {'alpha': lambda: 'a', 'shared': lambda: 'from-a'}


class _ProviderB(_Rec):
    _sandbox_helper_provider = True

    def sandbox_helpers(self):
        return {'shared': lambda: 'from-b', 'beta': lambda: 'b'}


class _Silent(_Rec):
    def sandbox_helpers(self):
        return {'sneaky': lambda: 1}


class _Broken(_Rec):
    _sandbox_helper_provider = True

    def sandbox_helpers(self):
        raise RuntimeError('nope')


class _FakeEnv(object):
    def __init__(self, classes):
        self.registry = dict(classes)
        self._inst = {name: cls() for name, cls in classes.items()}

    def __getitem__(self, name):
        return self._inst[name]


def test_build_safe_context_does_not_name_geo_service():
    src = inspect.getsource(cb.build_safe_context)
    assert 'geo.service' not in src
    assert 'collect_sandbox_helpers' in src
    assert 'search_by_affinity' in src


def test_absent_provider_publishes_nothing():
    env = _FakeEnv({'res.partner': _Silent})
    got = sh.collect_sandbox_helpers(env)
    assert got == {}
    assert 'geocode' not in got
    assert 'sneaky' not in got


def test_opt_in_is_collected():
    env = _FakeEnv({'demo.helper': _ProviderA})
    got = sh.collect_sandbox_helpers(env)
    assert set(got) == {'alpha', 'shared'}
    assert got['alpha']() == 'a'


def test_engine_keys_win():
    env = _FakeEnv({'demo.helper': _ProviderA})
    got = sh.collect_sandbox_helpers(env, occupied={'alpha', 'env'})
    assert 'alpha' not in got
    assert 'shared' in got


def test_first_provider_wins_collision(caplog):
    env = _FakeEnv({
        'mod.b': _ProviderB,
        'mod.a': _ProviderA,
    })
    with caplog.at_level(logging.WARNING):
        got = sh.collect_sandbox_helpers(env)
    assert got['shared']() == 'from-a'
    assert got['alpha']() == 'a'
    assert got['beta']() == 'b'
    assert any('shared' in rec.message for rec in caplog.records)


def test_broken_provider_is_skipped():
    env = _FakeEnv({
        'mod.broken': _Broken,
        'mod.ok': _ProviderA,
    })
    got = sh.collect_sandbox_helpers(env)
    assert set(got) == {'alpha', 'shared'}
