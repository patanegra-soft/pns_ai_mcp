# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Cell values and map links from a turn cannot carry markup or javascript: hrefs."""
from __future__ import annotations

from pathlib import Path

from _load_addon import load_module, render_source

render = load_module('relaxaicode_render', 'utils', 'relaxaicode_render.py')

_ROOT = Path(__file__).resolve().parents[1]


def test_base64_image_cell_is_escaped():
    evil = 'iVBORw' + 'A' * 70 + '" onerror="alert(1)'
    out = render._render_cell('foto', evil, {})
    assert 'onerror="' not in out
    assert '&quot; onerror=&quot;' in out


_PIC = 'https://bucket.example.com/public-read/b3205.jpg'


def test_picture_url_draws_whatever_the_column_is_called():
    for column in ('Foto', 'Fotografia', '写真', 'x'):
        out = render._render_cell(column, _PIC, {})
        assert '<img src="%s"' % _PIC in out, column
    assert render._has_image_columns([{'nombre': 'Ana', '写真': _PIC}])


def test_url_that_is_not_a_picture_is_not_drawn():
    out = render._render_cell('Foto', 'https://example.com/profile', {})
    assert '<img' not in out
    assert not render._has_image_columns([{'Foto': 'https://example.com/profile'}])


def test_img_markup_in_a_cell_is_text():
    out = render._render_cell('Foto', '<img src="%s">' % _PIC, {})
    assert '<img' not in out
    assert '&lt;img' in out


def test_renderer_has_no_column_word_list_for_pictures():
    src = render_source()
    assert '_IMG_KEY_HINTS' not in src
    assert "'foto'" not in src


def test_map_thumb_drops_javascript_href():
    out = render._render_map_thumb_cell({
        '__map_thumb__': True, 'href': 'javascript:alert(1)', 'alt': 'x',
    })
    assert 'javascript:' not in out
    assert '<a ' not in out


def test_coords_cell_drops_javascript_href():
    out = render._render_coords_cell({
        '__coords__': True, 'text': '1,2', 'href': 'javascript:alert(1)',
    })
    assert 'javascript:' not in out


def test_map_banner_drops_javascript_href():
    assert render._map_banner_card_html('javascript:alert(1)', 'Mapa') == ''
    ok = render._map_banner_card_html('https://www.openstreetmap.org/?mlat=1&mlon=2#map=16/1/2', 'Mapa')
    assert 'href="https://www.openstreetmap.org/' in ok


def test_context_stats_html_is_computed_and_escaped():
    src = (_ROOT / 'common' / 'wizard' / 'context_stats_wizard.py').read_text(encoding='utf-8')
    assert "compute='_compute_stats_html'" in src
    assert "res['stats_html']" not in src
    assert '_esc(cache_error)' in src
    assert '_esc(title)' in src
    agent = (_ROOT / 'common' / 'models' / 'ai_agent.py').read_text(encoding='utf-8')
    assert "'stats_html':" not in agent


class _Bin:
    type = 'binary'


class _Char:
    type = 'char'


class _Model:
    def __init__(self, fields):
        self._fields = fields


def test_the_click_uses_the_largest_size_the_model_stores():
    """A missing larger field must not become the link: the web route
    paints the generic placeholder and the viewer swaps the real picture."""
    env = {
        'pic.record': _Model({
            'image_128': _Bin(),
            'image_512': _Bin(),
            'image_1920': _Bin(),
            'name': _Char(),
        }),
        'pic.mark': _Model({
            'image_128': _Bin(),
            'avatar_1920': _Bin(),
        }),
        'pic.face': _Model({
            'avatar_128': _Bin(),
            'avatar_512': _Bin(),
        }),
    }
    photo = '/web/image/pic.record/7/image_128'
    out = render._render_cell('picture', photo, {'env': env})
    assert 'href="/web/image/pic.record/7/image_1920"' in out
    assert 'src="/web/image/pic.record/7/image_128"' in out

    mark = '/web/image/pic.mark/4/image_128'
    out = render._render_cell('picture', mark, {'env': env})
    assert 'href="/web/image/pic.mark/4/image_128"' in out
    assert 'image_1920' not in out

    face = '/web/image/pic.face/3/avatar_128'
    out = render._render_cell('picture', face, {'env': env})
    assert 'href="/web/image/pic.face/3/avatar_512"' in out

    plain = '/web/image/pic.mark/4/logo'
    out = render._render_cell('picture', plain, {'env': env})
    assert 'href="/web/image/pic.mark/4/logo"' in out

    bare = render._render_cell('picture', mark, {})
    assert 'href="/web/image/pic.mark/4/image_128"' in bare
    assert 'image_1920' not in bare


def test_engine_ships_no_vendor_libs():
    for path in (
        _ROOT / 'stacks' / 'owl1' / 'pns_ai_mcp' / 'views' / 'assets.xml',
        _ROOT / 'stacks' / 'owl1' / 'pns_ai_mcp' / '__manifest__.py',
        _ROOT / 'stacks' / 'owl2' / 'pns_ai_mcp' / '__manifest__.py',
    ):
        text = path.read_text(encoding='utf-8')
        for lib in ('showdown', 'jspdf', 'xlsx.full'):
            assert lib not in text, (path.name, lib)
