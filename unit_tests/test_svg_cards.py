# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""SVG card envelope (data-ai-card) from result card/cards."""
from __future__ import annotations

from pathlib import Path

from _load_addon import load_module

render = load_module('relaxaicode_render', 'utils', 'relaxaicode_render.py')
payload = load_module('mcp_tool_payload', 'utils', 'mcp_tool_payload.py')


def test_clock_naive_iso_rewritten_to_user_tz():
    result = {
        'card': {
            'kind': 'clock',
            'iso': '2026-08-15T22:31:08',
            'title': 'Server time',
        }
    }
    cards = render.collect_svg_cards(
        result, render_context={'user_tz': 'Europe/Madrid'},
    )
    assert len(cards) == 1
    assert cards[0]['tz'] == 'Europe/Madrid'
    assert cards[0]['iso'] == '2026-08-16T00:31:08+02:00'


def test_card_tz_wins_over_session_user_tz():
    """Same instant, three card tz → three wall clocks (session tz must not win)."""
    instant = '2026-08-15T23:15:00+02:00'
    result = {
        'cards': [
            {'kind': 'clock', 'iso': instant, 'tz': 'Asia/Tokyo', 'title': 'A'},
            {'kind': 'clock', 'iso': instant, 'tz': 'America/Los_Angeles', 'title': 'B'},
            {
                'kind': 'clock',
                'iso': instant,
                'tz': 'America/Argentina/Buenos_Aires',
                'title': 'C',
            },
        ]
    }
    cards = render.collect_svg_cards(
        result, render_context={'user_tz': 'Europe/Madrid'},
    )
    assert [c['tz'] for c in cards] == [
        'Asia/Tokyo',
        'America/Los_Angeles',
        'America/Argentina/Buenos_Aires',
    ]
    assert cards[0]['iso'] == '2026-08-16T06:15:00+09:00'
    assert cards[1]['iso'] == '2026-08-15T14:15:00-07:00'
    assert cards[2]['iso'] == '2026-08-15T18:15:00-03:00'


def test_clock_envelope_and_direct_return():
    result = {
        'card': {
            'kind': 'clock',
            'iso': '2026-08-13T05:41:00',
            'title': 'Server time',
        }
    }
    assert render.maybe_attach_formatted_text(result, force=False)
    html = result.get('formatted_text') or ''
    assert 'data-ai-card=' in html
    assert 'o_ai_svg_card' in html
    assert '2026-08-13T05:41:00' in html
    assert result.get('__return_direct__')
    assert result.get('__fmt_type__') == 'server_side_python'


def test_clock_without_iso_does_not_paint():
    result = {'card': {'kind': 'clock', 'title': 'Nope'}}
    assert render.collect_svg_cards(result) == []
    assert render.render_svg_cards_html(result) == ''
    assert not render.maybe_attach_formatted_text(result, force=False)
    assert not result.get('formatted_text')


def test_fact_card_and_cards_list():
    result = {
        'cards': [
            {'kind': 'fact', 'title': 'N', 'value': '7'},
            {'kind': 'unknown', 'title': 'X', 'value': '1'},
        ]
    }
    html = render.render_svg_cards_html(result)
    assert html.count('data-ai-card=') == 2
    assert '"kind":"fact"' in html.replace('&quot;', '"') or 'fact' in html


def test_cards_not_owned_by_compose_model():
    result = {
        'card': {'kind': 'clock', 'iso': '2026-08-13T05:41:00'},
    }
    render.maybe_attach_formatted_text(result, force=False)
    assert payload.payload_has_svg_cards(result)
    assert not payload.remote_owns_tabular_presentation(True, result)
    stripped = payload.strip_server_html_for_remote(result)
    assert stripped.get('formatted_text')
    assert stripped.get('__return_direct__')


def test_link_banner_and_rejects_javascript():
    result = {
        'card': {
            'kind': 'link',
            'url': 'https://example.com/docs',
            'title': 'Example docs',
        }
    }
    html = render.render_svg_cards_html(result)
    assert 'o_ai_link_banner_card' in html
    assert 'href="https://example.com/docs"' in html
    assert 'Example docs' in html
    assert 'rel="noopener noreferrer"' in html
    assert render.maybe_attach_formatted_text(
        {'card': {'kind': 'link', 'url': 'javascript:alert(1)', 'title': 'x'}},
        force=False,
    ) is False
    assert render.collect_svg_cards(
        {'card': {'kind': 'link', 'url': 'javascript:alert(1)'}}
    ) == []
    bare = render.collect_svg_cards(
        {'card': {'kind': 'link', 'url': 'example.com', 'title': 'Ex'}}
    )
    assert bare and bare[0]['url'] == 'https://example.com'


def test_system_prompt_no_generic_svg_ban():
    root = Path(__file__).resolve().parents[1] / 'common' / 'ai' / 'contexts'
    xml = (root / 'core' / 'system_prompt.xml').read_text(encoding='utf-8')
    assert 'NEVER INVENT DATA' not in xml
    assert 'NEVER FABRICATE' in xml
    assert 'presentation_grids' not in xml
    assert 'structured rows' in xml
    assert 'FORBIDDEN: drawing charts yourself with SVG' not in xml
    assert 'ai.provider.laconic_mode' not in xml
    assert 'bool(r.image_128)' not in xml
    assert 'Maine Coon' not in xml
    assert 'Open-Meteo' not in xml
    assert 'GEO VISIT ORDER' not in xml
    assert 'PRINCIPAL CRITERION ON MAPS' not in xml
    assert 'if lugar:' not in xml
    assert 'compose-agent' not in xml
