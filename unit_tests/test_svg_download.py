# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Inline SVG drawings → session download chips (not decorative chrome)."""
from __future__ import annotations

from _load_addon import load_module

svg = load_module('svg_download', 'utils', 'svg_download.py')

_CAT = (
    '<svg viewBox="0 0 240 240" width="200" height="200">'
    + ('<ellipse cx="120" cy="140" rx="70" ry="55" fill="#333"/>' * 8)
    + '<title>Gato</title></svg>'
)


def test_extracts_drawing_and_skips_pin_chrome():
    drawing = (
        '<svg viewBox="0 0 200 200">'
        + ('<circle cx="100" cy="100" r="40" fill="orange"/>' * 12)
        + '<title>Gato</title></svg>'
    )
    html = (
        '<p>hola</p>'
        + drawing
        + '<svg class="o_ai_map_banner_pins" viewBox="0 0 120 72">'
        + '<circle cx="10" cy="10" r="2"/></svg>'
    )
    found = svg.harvest_drawing_svgs(html)[0]
    assert len(found) == 1
    assert 'orange' in found[0]
    assert 'xmlns="http://www.w3.org/2000/svg"' in found[0]
    assert svg.svg_filename(found[0]) == 'gato.svg'


def test_strips_script_and_javascript_href():
    payload = (
        '<svg viewBox="0 0 100 100" onclick="alert(1)">'
        + ('<rect width="10" height="10"/>' * 50)
        + '<script>alert(1)</script>'
        + '<a href="javascript:alert(1)">x</a>'
        + '</svg>'
    )
    found = svg.harvest_drawing_svgs(payload)[0]
    assert len(found) == 1
    assert '<script' not in found[0].lower()
    assert 'onclick' not in found[0].lower()
    assert 'javascript:' not in found[0].lower()


def test_tiny_icon_is_not_a_drawing():
    icon = '<svg width="16" height="16"><path d="M0 0h16v16z"/></svg>'
    assert svg.harvest_drawing_svgs(icon)[0] == []


def test_fence_svg_leaves_prose_and_drops_source():
    prose = 'Soy Chatboo: ahí va tu gato.'
    text = prose + '\n\n```svg\n' + _CAT + '\n```\n'
    docs, cleaned = svg.harvest_drawing_svgs(text)
    assert len(docs) == 1
    assert 'ellipse' in docs[0]
    assert cleaned == prose
    assert '<svg' not in cleaned
    assert '```' not in cleaned


def test_python_fence_with_svg_string_is_not_stripped():
    body = (
        'print("hello")\n'
        'markup = """' + _CAT + '"""\n'
        'print(markup)\n'
    )
    text = 'Here is the generator:\n\n```python\n' + body + '```\n'
    docs, cleaned = svg.harvest_drawing_svgs(text)
    assert docs == []
    assert '```python' in cleaned


def test_escaped_pre_code_is_harvested():
    escaped = (
        '&lt;svg viewBox="0 0 240 240"&gt;'
        + ('&lt;circle cx="1" cy="1" r="1"/&gt;' * 40)
        + '&lt;/svg&gt;'
    )
    html = '<p>listo</p><pre><code>' + escaped + '</code></pre>'
    docs, cleaned = svg.harvest_drawing_svgs(html)
    assert len(docs) == 1
    assert '<svg' in docs[0]
    assert 'listo' in cleaned
    assert '<pre' not in cleaned.lower()
    assert '&lt;svg' not in cleaned


def test_svg_chip_url_opens_inline_not_download():
    chip = {
        'name': 'drawing-1.svg',
        'url': '/web/content/42?access_token=abc&download=true',
        'mimetype': 'image/svg+xml',
    }
    url = svg.svg_inline_view_url(chip)
    assert 'download' not in url
    assert url == '/pns_ai_mcp/session_file/42'
    already = svg.svg_inline_view_url({'url': url})
    assert already == url


def test_filename_from_compose_model_prompt():
    name = svg.svg_filename(
        '<svg></svg>',
        prompt='/compose-model ¿me pintas un gato en svg?',
    )
    assert name == 'gato.svg'


def test_filename_from_skill_slash():
    name = svg.utterance_filename(
        prompt='/financial-health',
        ext='pdf',
    )
    assert name == 'financial_health.pdf'


def test_filename_prompt_beats_generic_title():
    svg_doc = '<svg><title>Drawing</title></svg>'
    name = svg.svg_filename(
        svg_doc,
        prompt='un gato naranja',
    )
    assert name == 'gato_naranja.svg'


def test_filename_explicit_in_prompt():
    name = svg.utterance_filename(
        prompt='guarda esto como informe_financiero.pdf porfa',
        ext='pdf',
    )
    assert name == 'informe_financiero.pdf'


def test_generic_attachment_name():
    assert svg.is_generic_attachment_name('drawing-1.svg')
    assert svg.is_generic_attachment_name('download.pdf')
    assert svg.is_generic_attachment_name(
        'cb72c4b3-eb9c-4c37-9fe9-44f961d002b6.pdf',
    )
    assert not svg.is_generic_attachment_name('gato.svg')
    assert not svg.is_generic_attachment_name(
        'Contrato trabajo Laura Martín Ortega.pdf',
    )
    name = svg.utterance_filename(
        prompt='descarga el contrato de trabajo porfa',
        ext='pdf',
    )
    assert name == 'contrato_trabajo.pdf'
