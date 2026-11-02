# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Ack cites only the CRUD header; business_documents pack owns write rules."""
from __future__ import annotations

from pathlib import Path

from _load_addon import load_module

ack = load_module(
    'verification_ack_records', 'utils', 'verification_ack_records.py',
)
cite = load_module('record_cite', 'utils', 'record_cite.py')


class _HeaderEnv:
    """Catalog of model names: header iff ``{model}.line`` is present."""

    def __init__(self, names):
        self._names = set(names)

    def __contains__(self, key):
        return key in self._names


ENV = _HeaderEnv({'demo.header', 'demo.header.line'})


def _parent_of(model, rid):
    if model == 'demo.header.line':
        return ('demo.header', 10)
    return None


def _lookup(model, fname):
    return {
        ('demo.header', 'partner_id'): ('many2one', 'res.partner'),
        ('demo.header', 'line_ids'): ('one2many', 'demo.line'),
        ('demo.line', 'product_id'): ('many2one', 'product.product'),
    }.get((model, fname))


def test_collect_only_crud_header():
    recs = ack.collect_ack_records(
        [{'op': 'create', 'model': 'demo.header', 'id': 3180, 'name': 'DOC/1'}],
        steps=[{
            'op': 'create',
            'model': 'demo.header',
            'values': {
                'partner_id': 42,
                'line_ids': [[0, 0, {'product_id': 99, 'qty': 13}]],
            },
        }],
        lookup=_lookup,
        env=ENV,
    )
    assert recs == [{
        'model': 'demo.header', 'id': 3180, 'name': 'DOC/1', 'role': 'document',
    }]


def test_write_ids_are_documents():
    recs = ack.collect_ack_records(
        [{'op': 'write', 'model': 'demo.header', 'ids': [7, 8], 'count': 2}],
        lookup=_lookup,
        env=ENV,
    )
    assert [(r['id'], r['role']) for r in recs] == [
        (7, 'document'), (8, 'document'),
    ]


def test_write_line_cites_header():
    recs = ack.collect_ack_records(
        [{'op': 'write', 'model': 'demo.header.line', 'ids': [99], 'name': 'Art'}],
        env=ENV,
        parent_of=_parent_of,
    )
    assert recs == [{
        'model': 'demo.header', 'id': 10, 'name': 'demo.header #10',
        'role': 'document',
    }]


def test_a_record_just_created_gets_a_card_even_with_no_lines():
    """Most records have no lines; the phone was left with nothing to tap."""
    recs = ack.collect_ack_records(
        [{'op': 'create', 'model': 'product.product', 'id': 5, 'name': 'Art'}],
        env=ENV,
    )
    assert recs == [{
        'model': 'product.product', 'id': 5, 'name': 'Art', 'role': 'document',
    }]


def test_a_line_just_created_still_points_at_its_header():
    recs = ack.collect_ack_records(
        [{'op': 'create', 'model': 'demo.header.line', 'id': 99, 'name': 'Art'}],
        env=ENV,
        parent_of=_parent_of,
    )
    assert [(r['model'], r['id']) for r in recs] == [('demo.header', 10)]


def test_write_product_only_no_document():
    recs = ack.collect_ack_records(
        [{'op': 'write', 'model': 'product.product', 'ids': [5], 'name': 'Art'}],
        env=ENV,
    )
    assert recs == []


def test_write_line_and_product_only_header():
    recs = ack.collect_ack_records(
        [
            {'op': 'write', 'model': 'demo.header.line', 'ids': [99], 'name': 'Art'},
            {'op': 'write', 'model': 'product.product', 'ids': [5], 'name': 'Art'},
        ],
        env=ENV,
        parent_of=_parent_of,
    )
    assert [(r['model'], r['id'], r['role']) for r in recs] == [
        ('demo.header', 10, 'document'),
    ]


def test_attach_adds_records_and_names():
    payload = ack.attach_ack_records(
        {'success': True},
        [{'op': 'copy', 'model': 'demo.header', 'new_id': 5, 'name': 'old'}],
        name_of=lambda model, rid: 'Named-%s' % rid if model == 'demo.header' else None,
        env=ENV,
    )
    assert payload['records'][0]['name'] == 'Named-5'
    assert payload['records'][0]['role'] == 'document'


def test_cite_one_unlabeled_header():
    out = cite.document_cite_refs(
        [{'model': 'demo.header', 'id': 1, 'name': 'DOC/1'}],
        env=ENV,
    )
    assert out == [{
        'model': 'demo.header', 'id': 1, 'name': 'DOC/1', 'role': 'document',
    }]


def test_cite_one_product_unlabeled_empty():
    assert cite.document_cite_refs(
        [{'model': 'product.product', 'id': 5, 'name': 'Art'}],
        env=ENV,
    ) == []


def test_cite_one_line_unlabeled_lifts_header():
    out = cite.document_cite_refs(
        [{'model': 'demo.header.line', 'id': 99, 'name': 'Art'}],
        env=ENV,
        parent_of=_parent_of,
    )
    assert out == [{
        'model': 'demo.header', 'id': 10, 'role': 'document',
    }]


def test_cite_drops_explicit_product_document():
    assert cite.document_cite_refs(
        [{'model': 'product.product', 'id': 5, 'role': 'document'}],
        env=ENV,
    ) == []


def test_cite_drops_mural():
    assert cite.document_cite_refs([
        {'model': 'demo.header', 'id': 1, 'name': 'DOC/1'},
        {'model': 'res.partner', 'id': 42, 'name': 'P'},
        {'model': 'product.product', 'id': 99, 'name': 'Art'},
    ], env=ENV) == []


def test_cite_keeps_explicit_document():
    out = cite.document_cite_refs([
        {'model': 'demo.header', 'id': 1, 'name': 'DOC/1', 'role': 'document'},
        {'model': 'res.partner', 'id': 42, 'name': 'P'},
    ], env=ENV)
    assert [r['id'] for r in out] == [1]


def test_business_documents_pack():
    root = Path(__file__).resolve().parents[1] / 'common' / 'ai' / 'contexts'
    pack = (root / 'domain' / 'business_documents.xml').read_text(encoding='utf-8')
    prompt = (root / 'core' / 'system_prompt.xml').read_text(encoding='utf-8')
    pack_flat = ' '.join(pack.split())
    assert '<code>business_documents</code>' in pack
    assert 'discount_ideal' not in pack
    assert 'unit="ratio"' not in pack
    assert 'write 0.5' not in pack
    assert 'every article line' in pack_flat
    assert 'Spoken "50%" → write 50' in pack_flat
    assert 'type="budget"' in pack
    assert 'last document id' in pack
    assert 'summary of a write' not in pack
    assert 'cite only the document header' in pack
    assert 'price_unit on that line' in pack
    assert 'Do not write the product list price' in pack
    assert 'commercial_documents' not in pack
    assert (root / 'domain' / 'commercial_documents.xml').exists() is False
    assert 'cite only that document header' in prompt
    assert 'last document id in this thread' in prompt


def test_the_prompt_asks_before_it_invents_a_create_value():
    """A required field is a question; a code field belongs to the instance."""
    root = Path(__file__).resolve().parents[1] / 'common' / 'ai' / 'contexts'
    prompt = (root / 'core' / 'system_prompt.xml').read_text(encoding='utf-8')
    flat = ' '.join(prompt.split())
    assert '<create_values>' in prompt
    assert 'default_get' in flat
    assert 'STOPS the plan' in flat
    assert "NEVER send the placeholder ('/', 'New')" in flat
    assert 'do not retry with another made-up value' in flat
    # A create that quietly drops what the user named is a wrong record.
    assert 'NEVER DISAPPEARS IN SILENCE' in flat
    assert 'STOPS the plan' in flat
    assert 'do NOT put a near-enough record in it' in flat
