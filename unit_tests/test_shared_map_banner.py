# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Shared Leaflet maps must not be labelled as «Mapa OSM» by URL alone."""
from __future__ import annotations

from _load_addon import load_module

render = load_module('relaxaicode_render', 'utils', 'relaxaicode_render.py')


def test_shared_map_banner_is_neutral_not_osm_acronym():
    html = render._result_map_banner_html({
        'map_url': 'https://odoo.example/geo/map/abcd',
        'summary': '7 localizados de 20',
    })
    assert 'o_ai_map_banner_card' in html
    assert '/geo/map/abcd' in html
    assert 'Mapa OSM' not in html
    assert '7 localizados' in html or 'Mapa compartido' in html


def test_shared_map_banner_prefers_title_over_provider_alt():
    html = render._result_map_banner_html({
        'title': 'Clientes con facturación alta en Sevilla',
        'map_pins': {
            '__map_thumb__': True,
            'href': 'https://odoo.example/geo/map/abcd',
            'provider': 'osm',
            'alt': 'OSM (7)',
            'png_b64': None,
            'pin_count': 7,
        },
    })
    assert 'Clientes con facturación alta en Sevilla' in html
    assert 'Mapa OSM' not in html
    assert 'OpenStreetMap' in html


def test_shared_map_banner_shows_google_maps_provider():
    html = render._result_map_banner_html({
        'title': 'Top 30',
        'map_pins': {
            '__map_thumb__': True,
            'href': '/geo/map/zzzz',
            'provider': 'google',
            'png_b64': None,
            'pin_count': 30,
        },
    })
    assert 'Google Maps' in html
    assert 'o_ai_map_banner_gm' in html


def test_grouped_map_block_gets_default_title_when_empty():
    result = {
        'tables': [
            {
                'map_url': 'https://example.com/geo/map/zzzz',
                'data': [{'id': 1}],
            },
        ],
    }
    sections = render._result_groups(result)
    assert sections is not None
    assert sections[0][0] == 'Map result'
    html = render.grouped_table_html(result)
    assert 'Map result' in html
    assert 'Mapa OSM' not in html


def test_shared_map_keeps_lat_lon_on_payload_hides_in_table():
    """Rectify/rebuild needs Lat/Lon; the chat table must not show them."""
    result = {
        'data': [
            {'Tarea': 'A', 'Lat': 37.9, 'Lon': -4.7, 'Ciudad': 'Sevilla'},
        ],
        'title': 'Tareas',
        'summary': 'Posiciones',
        'map_url': 'https://odoo.example/geo/map/abcd',
    }
    html = render.render_result_html(result)
    assert result['data'][0]['Lat'] == 37.9
    assert result['data'][0]['Lon'] == -4.7
    # Headers carry sort attributes, so match the cell, not a bare tag.
    assert '>Lat</th>' not in (html or '')
    assert '>Lon</th>' not in (html or '')
    assert '>Tarea</th>' in (html or '')
    assert '/geo/map/abcd' in (html or '')
