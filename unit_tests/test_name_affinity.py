# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Affinity search: letter swaps rank; no business literals in the helper."""
from __future__ import annotations

from pathlib import Path

from _load_addon import addon_file, load_module

mod = load_module('pns_ai_mcp_name_affinity', 'utils', 'name_affinity.py')
affinity_score = mod.affinity_score
search_by_affinity = mod.search_by_affinity
windows_of = mod.windows_of


class _Field(object):
    pass


class _Rec(object):
    def __init__(self, **vals):
        for key, value in vals.items():
            setattr(self, key, value)


class _RS(object):
    _name = 'demo.model'
    _fields = {
        'name': _Field(),
        'display_name': _Field(),
        'email': _Field(),
        'ref': _Field(),
        'vat': _Field(),
    }

    def __init__(self, rows, universe=None):
        self._rows = list(rows)
        self._universe = list(universe if universe is not None else rows)

    @property
    def ids(self):
        return [rec.id for rec in self._rows]

    def search(self, domain, limit=80):
        leaves = [
            item for item in (domain or [])
            if isinstance(item, (list, tuple)) and len(item) == 3
        ]
        matched = []
        for rec in self._universe:
            for field, op, value in leaves:
                if op != 'ilike':
                    continue
                raw = getattr(rec, field, None)
                if raw is None:
                    continue
                if str(value).lower() in str(raw).lower():
                    matched.append(rec)
                    break
        return _RS(matched[:limit], self._universe)

    def name_search(self, name='', args=None, operator='ilike', limit=50):
        found = self.search([('name', 'ilike', name)], limit=limit)
        return [(rec.id, rec.name) for rec in found._rows]

    def browse(self, ids):
        want = set(ids if not isinstance(ids, int) else [ids])
        return _RS(
            [rec for rec in self._universe if rec.id in want],
            self._universe,
        )

    def __iter__(self):
        return iter(self._rows)


class _Env(object):
    def __init__(self, model):
        self._model = model

    def __contains__(self, name):
        return name == self._model._name

    def __getitem__(self, name):
        if name != self._model._name:
            raise KeyError(name)
        return self._model


def _catalog():
    return _RS([
        _Rec(id=1, name='ADORGASE, SA', display_name='ADORGASE, SA',
             email='info@adorgase.example', ref='', vat='A123'),
        _Rec(id=2, name='GASES IBERICOS DEL NORTE, SL',
             display_name='GASES IBERICOS DEL NORTE, SL',
             email='', ref='', vat=''),
        _Rec(id=3, name='GASES TECNICOS DEL SUR, SAU',
             display_name='GASES TECNICOS DEL SUR, SAU',
             email='', ref='', vat=''),
        _Rec(id=4, name='GASES INDUSTRIALES ESPAÑA, SLU',
             display_name='GASES INDUSTRIALES ESPAÑA, SLU',
             email='', ref='', vat=''),
    ])


def test_helper_has_no_business_literals():
    src = addon_file('utils', 'name_affinity.py').read_text(encoding='utf-8')
    for token in (
        'cliente', 'customer_rank', 'customer=True', 'res.partner',
        'aldogase', 'adorgase',
    ):
        assert token not in src


def test_transposed_token_scores_higher_than_unrelated():
    close = affinity_score('aldogase', 'ADORGASE, SA')
    also = affinity_score('ardogase', 'ADORGASE, SA')
    far = affinity_score('aldogase', 'GASES IBERICOS DEL NORTE, SL')
    assert close >= 0.75
    assert also >= 0.75
    assert close > far
    assert 'gase' in windows_of('aldogase')


def test_search_finds_transposed_name():
    env = _Env(_catalog())
    rows = search_by_affinity(
        env, 'demo.model', ['aldogase', 'ardogase'],
    )
    assert rows
    assert rows[0]['id'] == 1
    assert rows[0]['name'] == 'ADORGASE, SA'
    assert rows[0]['score'] >= 0.75
    assert rows[0]['__model'] == 'demo.model'


def test_empty_needles_return_empty():
    env = _Env(_catalog())
    assert search_by_affinity(env, 'demo.model', []) == []
    assert search_by_affinity(env, 'demo.model', 'zzzz-no-such') == []


def _pack(*parts):
    return (
        Path(__file__).resolve().parents[1]
        / 'common' / 'ai' / 'contexts' / Path(*parts)
    ).read_text(encoding='utf-8')


def test_an_ambiguous_name_is_asked_with_its_candidates():
    """Two plausible rows is a question, not a coin toss.

    The rule is knowledge, never an ``if`` in the engine: it says to deliver
    the candidates as rows the user can point at, and it holds for any model.
    """
    prompt = _pack('core', 'system_prompt.xml')
    assert 'AMBIGUOUS RECORD' in prompt
    assert 'do NOT take the first one' in prompt
    assert 'BEFORE safe_plan_request' in prompt
    partners = _pack('domain', 'partners.xml')
    assert 'which_partner_did_you_mean' in partners
    geo = _pack('domain', 'geography.xml')
    assert 'SHOW the candidates' in geo


def test_a_shared_attribute_asks_the_same_question_as_a_name():
    """Saying where someone is does not say who they are.

    The user who gives a town, a trade or a date has named no record. If more
    than one row carries it, the answer is the table — the best fit is still a
    guess, and the reply never shows that a guess was made.
    """
    prompt = _pack('core', 'system_prompt.xml')
    assert 'a town, a trade, a date' in prompt
    assert 'An attribute is NOT an identity' in prompt


def test_partners_pack_teaches_the_helper():
    pack = (
        Path(__file__).resolve().parents[1]
        / 'common' / 'ai' / 'contexts' / 'domain' / 'partners.xml'
    ).read_text(encoding='utf-8')
    assert 'search_by_affinity' in pack
    assert 'approx_partner_name' in pack
    prompt = (
        Path(__file__).resolve().parents[1]
        / 'common' / 'ai' / 'contexts' / 'core' / 'system_prompt.xml'
    ).read_text(encoding='utf-8')
    assert 'search_by_affinity(model, needles)' in prompt


def test_the_pack_says_the_helper_hands_back_dicts():
    """It ranks rows, it does not browse them.

    The model kept writing ``hit.id`` and the turn died on an AttributeError,
    so the published shape travels with the helper, in the pack the model
    reads, for any model and not only partners.
    """
    hits = search_by_affinity(
        None, _RS([_Rec(id=7, name='ACME GRUAS, SL')]), ['acme gruas'],
    )
    assert hits and isinstance(hits[0], dict) and hits[0]['id'] == 7
    prompt = _pack('core', 'system_prompt.xml')
    assert 'RANKED DICTS' in prompt
    assert "read hit['id'], never hit.id" in prompt
    partners = _pack('domain', 'partners.xml')
    assert "[h['id'] for h in hits]" in partners
