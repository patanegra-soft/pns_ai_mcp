# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""ORM domain helpers: name alias + My-language filter strip."""
from __future__ import annotations

from _load_addon import load_module

orm_domain = load_module('orm_domain', 'utils', 'orm_domain.py')


def test_rewrites_name_leaf_to_rec_name():
    domain = ['&', ('active', '=', True), ('name', 'ilike', 'chip')]
    out = orm_domain.alias_name_leaves(domain, rec_name='code', has_name_field=False)
    assert out == ['&', ('active', '=', True), ('code', 'ilike', 'chip')]


def test_leaves_name_when_model_has_name_field():
    domain = [('name', 'ilike', 'chip')]
    assert orm_domain.alias_name_leaves(
        domain, rec_name='code', has_name_field=True,
    ) == domain


def test_ignores_dotted_and_non_list():
    dotted = [('name.foo', '=', 1)]
    assert orm_domain.alias_name_leaves(dotted, rec_name='code') == dotted
    assert orm_domain.alias_name_leaves(True, rec_name='code') is True


def test_strip_my_locale_drops_dangling_and_with_action_domain():
    """Discovery: action domain ANDed with My-language must stay valid."""
    # What Odoo builds when opening Discovery with the locale chip on:
    combined = [
        '&',
        '|', ('locale', '=', False), ('locale', '=', 'es_ES'),
        ['context_type', '=', 'discovery'],
    ]
    assert orm_domain.domain_has_my_locale_filter(combined) is True
    cleaned = orm_domain.strip_my_locale_filter(combined)
    assert cleaned == [['context_type', '=', 'discovery']]
    # Rewritten domain as _search would build it — no unary '&':
    rewritten = orm_domain.and_join(
        orm_domain.my_locale_domain('es_ES'), cleaned,
    )
    assert rewritten[0] == '&'
    assert ('locale', '=', 'es_ES') in rewritten
    assert cleaned[-1] in rewritten


def test_strip_my_locale_only_filter():
    domain = ['|', ('locale', '=', False), ('locale', '=', 'en_US')]
    assert orm_domain.strip_my_locale_filter(domain) == []


def test_strip_my_locale_preserves_unrelated_and():
    domain = [
        '&', ('active', '=', True),
        '|', ('locale', '=', False), ('locale', '=', 'es_ES'),
    ]
    # After strip: only the active leaf remains (leading & for locale is dropped).
    assert orm_domain.strip_my_locale_filter(domain) == [('active', '=', True)]


def test_no_locale_or_is_not_my_language():
    none = ['|', ('locale', '=', False), ('locale', '=', '')]
    assert orm_domain.domain_has_my_locale_filter(none) is False
    assert orm_domain.strip_my_locale_filter(none) == none


def test_my_locale_accepts_either_order():
    flipped = ['|', ('locale', '=', 'es_ES'), ('locale', '=', False)]
    assert orm_domain.domain_has_my_locale_filter(flipped) is True
    assert orm_domain.strip_my_locale_filter(flipped) == []


def test_and_join_and_my_locale_domain_arity():
    rest = [('context_type', '=', 'discovery')]
    out = orm_domain.and_join(orm_domain.my_locale_domain('es_ES'), rest)
    assert orm_domain.domain_arity_balance(out) == 0
    assert out[0] == '&'


def test_rewrite_recovers_short_or_after_active_leaf_stripped():
    """Discovery crash: leftover '|', '|', False, '' after Active was dropped."""
    incoming = [
        '&',
        '|', ('locale', '=', False), ('locale', '=', 'es_ES'),
        ['context_type', '=', 'discovery'],
        '|', '|', ['locale', '=', False], ['locale', '=', ''],
    ]
    assert orm_domain.domain_has_my_locale_filter(incoming) is True
    raw = orm_domain.and_join(
        orm_domain.my_locale_domain('es_ES'),
        orm_domain.strip_my_locale_filter(incoming),
    )
    assert orm_domain.domain_is_odoo_prefix_ok(raw) is False
    fixed = orm_domain.rewrite_my_locale_domain(incoming, 'es_ES')
    assert orm_domain.domain_is_odoo_prefix_ok(fixed) is True
    assert ('locale', '=', 'es_ES') in fixed
    assert ['context_type', '=', 'discovery'] in fixed


def test_has_and_strip_three_or_my_locale():
    domain = [
        '&',
        '|', '|',
        ('locale', '=', False), ('locale', '=', ''), ('locale', '=', 'es_ES'),
        ('context_type', '=', 'discovery'),
    ]
    assert orm_domain.domain_has_my_locale_filter(domain) is True
    assert orm_domain.strip_my_locale_filter(domain) == [
        ('context_type', '=', 'discovery'),
    ]
