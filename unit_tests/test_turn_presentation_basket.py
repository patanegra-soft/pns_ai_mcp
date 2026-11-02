# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Turn presentation basket: N presentable tool results → one tables payload."""
from __future__ import annotations

from _load_addon import load_module

# Renderer must be importable as sibling when basket falls back to absolute import.
import sys
sys.modules.setdefault(
    'relaxaicode_render',
    load_module('relaxaicode_render', 'utils', 'relaxaicode_render.py'),
)
basket = load_module(
    'turn_presentation_basket', 'utils', 'turn_presentation_basket.py',
)


def test_probe_extraction_not_presentable():
    payload = {
        'data': [{'id': 1}],
        '__phase__': 'extraction',
        'formatted_text': '<table></table>',
        '__fmt_type__': 'server_side_python',
    }
    assert not basket.is_basket_presentable(payload)


def test_presentation_payload_is_presentable():
    payload = {
        'data': [{'id': 1, 'Nombre': 'A'}],
        'summary': 'Demo A',
        '__phase__': 'presentation',
        '__return_direct__': True,
        'formatted_text': '<table></table>',
        '__fmt_type__': 'server_side_python',
    }
    assert basket.is_basket_presentable(payload)


def test_page_url_alone_is_presentable():
    """A page with no rows is still the document (not an extraction probe)."""
    payload = {
        'data': [],
        'summary': 'Weekly forecast',
        'page_url': '/chatboo/canvas/38?rev=2',
    }
    assert basket.has_presentable_content(payload)
    assert basket.is_basket_presentable(payload)


def test_map_banner_alone_is_presentable():
    payload = {
        'data': [{'id': 1}],
        'map_url': 'https://example/geo/map/abc',
        '__return_direct__': True,
        '__phase__': 'presentation',
    }
    assert basket.is_basket_presentable(payload)


def test_append_and_synthesize_multi():
    acc = []
    a = {
        'data': [{'id': 1, 'N': 'A'}],
        'summary': 'Anillos',
        'map_url': 'https://ex/map/1',
        '__return_direct__': True,
        '__phase__': 'presentation',
    }
    b = {
        'data': [{'id': 2, 'N': 'B'}],
        'summary': 'Proveedores',
        'map_url': 'https://ex/map/2',
        '__return_direct__': True,
        '__phase__': 'presentation',
    }
    assert basket.append_presentable(acc, a)
    assert basket.append_presentable(acc, b)
    assert len(acc) == 2
    merged = basket.synthesize_basket_payload(acc)
    assert merged is not None
    assert len(merged['tables']) == 2
    assert merged['tables'][0]['summary'] == 'Anillos'
    assert merged['tables'][1]['map_url'] == 'https://ex/map/2'
    assert merged.get('__return_direct__') is True


def test_single_block_unchanged_shape():
    acc = []
    only = {
        'data': [{'id': 1}],
        'summary': 'Solo',
        '__return_direct__': True,
        '__phase__': 'presentation',
    }
    basket.append_presentable(acc, only)
    merged = basket.synthesize_basket_payload(acc)
    assert merged['summary'] == 'Solo'
    assert 'tables' not in merged or not merged.get('tables')


def test_already_unified_replaces_basket():
    acc = []
    basket.append_presentable(acc, {
        'data': [{'id': 1}],
        'summary': 'One',
        '__return_direct__': True,
        '__phase__': 'presentation',
    })
    unified = {
        'tables': [
            {'title': 'A', 'data': [{'id': 1}]},
            {'title': 'B', 'data': [{'id': 2}]},
        ],
        '__return_direct__': True,
        '__phase__': 'presentation',
    }
    assert basket.payload_already_unified(unified)
    basket.append_presentable(acc, unified)
    assert len(acc) == 1
    merged = basket.synthesize_basket_payload(acc)
    assert len(merged['tables']) == 2


def test_unified_does_not_wipe_when_replace_disallowed():
    acc = []
    basket.append_presentable(acc, {
        'data': [{'id': 1}],
        'title': 'Primary',
        'summary': 'One',
        '__return_direct__': True,
        '__phase__': 'presentation',
    })
    unified = {
        'tables': [
            {'title': 'A', 'data': [{'id': 1}]},
            {'title': 'B', 'data': [{'id': 2}]},
        ],
        '__return_direct__': True,
        '__phase__': 'presentation',
    }
    basket.append_presentable(acc, unified, allow_unified_replace=False)
    assert acc[0].get('title') == 'Primary'
    assert len(acc) == 2


def test_render_basket_html_falls_back_when_single(monkeypatch):
    html = basket.render_basket_html(
        [{'data': [1], 'summary': 'x'}],
        fallback_html='<p>one</p>',
    )
    assert html == '<p>one</p>'


def test_render_basket_html_merges_two(monkeypatch):
    # Force maybe_attach via real renderer if importable.
    acc = [
        {
            'data': [{'id': 1, 'Nombre': 'A'}],
            'title': 'Bloque A',
            '__return_direct__': True,
            '__phase__': 'presentation',
        },
        {
            'data': [{'id': 2, 'Nombre': 'B'}],
            'title': 'Bloque B',
            'map_url': 'https://ex/map/b',
            '__return_direct__': True,
            '__phase__': 'presentation',
        },
    ]
    html = basket.render_basket_html(acc, fallback_html='<p>fallback</p>')
    assert html
    assert html != '<p>fallback</p>'
    # Multi-section titles should appear in HTML
    assert 'Bloque A' in html or 'A' in html
    assert 'Bloque B' in html or 'B' in html


def test_basket_block_keeps_excel_formulas():
    block = basket.payload_to_basket_block({
        'data': [{'a': 1}],
        '__excel_formulas__': {'a': '={b}'},
    })
    assert block['__excel_formulas__'] == {'a': '={b}'}
