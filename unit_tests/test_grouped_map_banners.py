# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Per-section map banners when result.tables[] carry map_url."""
from __future__ import annotations

from _load_addon import load_module

render = load_module('relaxaicode_render', 'utils', 'relaxaicode_render.py')


def test_grouped_html_renders_map_banner_per_table_block():
    result = {
        'tables': [
            {
                'title': 'Anillos',
                'data': [{'id': 1, 'Cliente': 'A'}],
                'map_url': 'https://example.com/geo/map/aaaa',
            },
            {
                'title': 'Proveedores',
                'data': [{'id': 2, 'Proveedor': 'B'}],
                'map_url': 'https://example.com/geo/map/bbbb',
            },
            {
                'title': 'Bancos',
                'data': [{'id': 3, 'Entidad': 'C'}],
                'map_pins': {
                    '__map_thumb__': True,
                    'href': 'https://example.com/geo/map/cccc',
                    'provider': 'osm',
                    'alt': 'Bancos',
                },
            },
        ],
    }
    html = render.grouped_table_html(result, summary='')
    assert html
    assert html.count('o_ai_map_banner') >= 3
    assert '/geo/map/aaaa' in html
    assert '/geo/map/bbbb' in html
    assert '/geo/map/cccc' in html


def test_result_groups_keeps_map_only_block():
    result = {
        'tables': [
            {
                'title': 'Solo mapa',
                'map_url': 'https://example.com/geo/map/zzzz',
            },
            {
                'title': 'Con filas',
                'data': [{'id': 1, 'N': 'X'}],
                'map_url': 'https://example.com/geo/map/yyyy',
            },
        ],
    }
    sections = render._result_groups(result)
    assert sections is not None
    assert len(sections) == 2
    assert sections[0][2].get('map_payload', {}).get('map_url')
    html = render.grouped_table_html(result)
    assert '/geo/map/zzzz' in html
    assert '/geo/map/yyyy' in html
