# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Where an agent finds a role: its chain, then everyone, then the fallback."""
from __future__ import annotations

import textwrap
from pathlib import Path

from _load_addon import load_module

_ROOT = Path(__file__).resolve().parents[1]
fit = load_module('provider_fit', 'utils', 'provider_fit.py')


class _Set(list):
    def filtered(self, pred):
        return _Set(p for p in self if pred(p))

    def mapped(self, name):
        return _Set(getattr(p, name) for p in self)

    def browse(self, ids):
        by_id = {p.id: p for p in _ALL}
        return _Set(by_id[i] for i in ids)

    def sudo(self):
        return self

    def search(self, domain, order=None):
        return _Set(_ALL)


class _Provider:
    no_external_failover = False

    def __init__(self, pid, *codes):
        self.id = pid
        self.provider_id = self
        self.flags = {code: True for code in codes}

    def _fit_flags(self):
        return self.flags

    def _fits(self, need):
        return fit.provider_fits(self.flags, need)

    def spend_cap_reached(self):
        return False

    def __repr__(self):
        return 'P%s' % self.id


class _NoRole:
    code = None


class _Role:
    def __init__(self, code, fallback=None):
        self.code = code
        self.use_fallback = code not in _FALLBACK_OFF
        self.fallback_id = _Role(fallback) if fallback else _NoRole()


_FALLBACK_OFF = set()


_FALLBACKS = {'parser': 'conversation'}
_ALL = _Set()


class _Roles:
    def _by_code(self, code):
        return _Role(code, _FALLBACKS.get(code))


class _Env(dict):
    def ref(self, *a, **k):
        return None


class _Engine:
    def __init__(self, chain):
        self.chain = _Set(chain)
        self.env = _Env({'ai.provider': _Set(), 'ai.provider.role': _Roles()})

    def get_failovers(self, agent_code):
        return self.chain

    def _without_capped(self, providers):
        return providers

    def _without_external_after_local(self, providers):
        return providers

    def _specialists_first(self, providers, need):
        if not need or need == 'conversation':
            return providers
        return _Set(sorted(
            providers,
            key=lambda p: (0 if fit.is_specialist(p.flags, need) else 1,
                           providers.index(p)),
        ))


def _door():
    src = (_ROOT / 'common' / 'models' / 'ai_execution_engine.py').read_text(
        encoding='utf-8',
    )
    body = src.split('    def get_providers_for_agent', 1)[1].split(
        '\n    @api.model', 1,
    )[0]
    scope = {
        '_': lambda s: s,
        'UserError': Exception,
        'RedirectWarning': Exception,
        '_logger': type('L', (), {'info': staticmethod(lambda *a, **k: None)})(),
    }
    exec(textwrap.dedent('    def get_providers_for_agent' + body), scope)
    return scope['get_providers_for_agent']


def _ask(chain, everyone, need):
    _ALL[:] = everyone
    return list(_door()(_Engine(chain), 'chat', need=need))


def test_the_chain_holds_the_role_and_the_one_role_provider_goes_first():
    both = _Provider(1, 'conversation', 'parser')
    only = _Provider(2, 'parser')
    outside = _Provider(3, 'parser')
    assert _ask([both, only], [both, only, outside], 'parser') == [only, both]


def test_the_chain_lacks_the_role_so_every_active_provider_is_asked():
    chat = _Provider(1, 'conversation')
    both = _Provider(2, 'conversation', 'parser')
    only = _Provider(3, 'parser')
    assert _ask([chat], [chat, both, only], 'parser') == [only, both]


def test_nobody_holds_the_role_so_its_fallback_answers_from_the_chain():
    chat = _Provider(1, 'conversation')
    plain = _Provider(2)
    other = _Provider(3, 'conversation')
    assert _ask([chat, plain], [chat, plain, other], 'parser') == [chat, plain]


def test_a_database_that_turns_the_fallback_off_gets_nobody():
    chat = _Provider(1, 'conversation')
    _FALLBACK_OFF.add('parser')
    try:
        assert _ask([chat], [chat], 'parser') == []
    finally:
        _FALLBACK_OFF.discard('parser')
    assert _ask([chat], [chat], 'parser') == [chat]


def test_a_role_without_fallback_gives_nobody():
    chat = _Provider(1, 'conversation')
    assert _ask([chat], [chat], 'decision') == []
    assert _ask([chat], [chat], 'vision') == []


def test_no_chain_means_every_active_provider_and_the_same_fallback():
    chat = _Provider(1, 'conversation')
    only = _Provider(2, 'parser')
    assert _ask([], [chat, only], 'parser') == [only]
    assert _ask([], [chat], 'parser') == [chat]


def test_a_module_role_is_found_like_the_engine_ones():
    reader = _Provider(4, 'barcode')
    chat = _Provider(1, 'conversation')
    assert _ask([chat], [chat, reader], 'barcode') == [reader]
    assert _ask([chat], [chat, reader], None) == [chat]
