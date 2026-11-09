# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""AI companies: what the screen ticks, or else the user's default one."""
from __future__ import annotations

from _load_addon import addon_file, load_module

oc = load_module('one_company', 'utils', 'one_company.py')


class _Companies(list):
    @property
    def id(self):
        return self[0].id

    @property
    def ids(self):
        return [c.id for c in self]

    @property
    def active(self):
        return bool(self) and self[0].active

    def filtered(self, name):
        return _Companies(c for c in self if getattr(c, name))

    def __getitem__(self, key):
        got = list.__getitem__(self, key)
        return _Companies(got) if isinstance(key, slice) else got


class _Company:
    def __init__(self, cid, active=True):
        self.id = cid
        self.active = active


class _User:
    def __init__(self, default, companies):
        self.company_id = _Companies([default]) if default else _Companies()
        self.company_ids = _Companies(companies)


class _Env:
    def __init__(self, user, archivable=True, context=None):
        self.user = user
        self.context = context or {}
        fields = {'active': object()} if archivable else {}
        known = {c.id: c for c in user.company_ids}

        class _Model:
            _fields = fields

            def browse(self, ids):
                return _Companies(known[i] for i in ids)

        self._model = _Model()

    def __getitem__(self, name):
        assert name == 'res.company'
        return self._model


def test_default_company_without_a_screen():
    a, b = _Company(1), _Company(2)
    env = _Env(_User(b, [a, b]), context={'allowed_company_ids': [1, 2], 'lang': 'es_ES'})
    ctx = oc.one_company_context(env)
    assert ctx['allowed_company_ids'] == [2]
    assert ctx['lang'] == 'es_ES'
    assert oc.SCREEN_COMPANIES not in ctx


def test_the_screen_wins_and_keeps_its_order():
    a, b = _Company(1), _Company(2)
    env = _Env(_User(a, [a, b]), context={oc.SCREEN_COMPANIES: [2, 1]})
    ctx = oc.one_company_context(env)
    assert ctx['allowed_company_ids'] == [2, 1]
    assert ctx[oc.SCREEN_COMPANIES] == [2, 1]


def test_a_company_that_is_not_mine_is_dropped():
    a, b = _Company(1), _Company(2)
    env = _Env(_User(a, [a, b]), context={oc.SCREEN_COMPANIES: [9, 2, '2', 'x']})
    assert oc.one_company_context(env)['allowed_company_ids'] == [2]
    only_foreign = _Env(_User(a, [a, b]), context={oc.SCREEN_COMPANIES: [9]})
    assert oc.one_company_context(only_foreign)['allowed_company_ids'] == [1]


def test_an_archived_company_on_the_screen_does_not_count():
    a, b = _Company(1), _Company(2, active=False)
    env = _Env(_User(a, [a, b]), context={oc.SCREEN_COMPANIES: [2]})
    assert oc.one_company_context(env)['allowed_company_ids'] == [1]


def test_an_explicit_request_beats_the_context():
    a, b = _Company(1), _Company(2)
    env = _Env(_User(a, [a, b]), context={oc.SCREEN_COMPANIES: [2]})
    assert oc.one_company_context(env, requested=())['allowed_company_ids'] == [1]
    assert oc.one_company_context(env, requested=[2])['allowed_company_ids'] == [2]


def test_archived_default_falls_to_the_first_active_one():
    a, b, c = _Company(1, active=False), _Company(2, active=False), _Company(3)
    env = _Env(_User(a, [a, b, c]))
    assert oc.one_company_context(env)['allowed_company_ids'] == [3]


def test_odoo_without_archived_companies_keeps_the_default():
    a = _Company(1, active=False)
    env = _Env(_User(a, [a]), archivable=False)
    assert oc.one_company_context(env)['allowed_company_ids'] == [1]


def test_no_company_leaves_the_context_alone():
    env = _Env(_User(None, []), context={'allowed_company_ids': [5]})
    assert oc.one_company_context(env)['allowed_company_ids'] == [5]


def test_read_and_write_boxes_use_it():
    helpers = addon_file('controllers', 'controller_helpers.py').read_text(encoding='utf-8')
    assert 'one_company_context(base_env)' in helpers
    plans = addon_file('models', 'safe_operation.py').read_text(encoding='utf-8')
    assert 'one_company_context(\n            exec_env, requested=data.get(SCREEN_COMPANIES) or (),' in plans


def test_a_plan_keeps_the_companies_it_was_asked_in():
    propose = addon_file('controllers', 'safe_plan.py').read_text(encoding='utf-8')
    assert 'operation_data[SCREEN_COMPANIES] = screen' in propose
