# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""One key for a result that is also a page in its own tab.

A module publishes a helper that returns a url and sets ``page_url``. The
engine paints it, keeps it as the turn artifact and remembers it, without
naming the module that made it.
"""
from __future__ import annotations

import sys
from pathlib import Path

from _load_addon import engine_source, load_module

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / 'common'))

rp = load_module('result_page', 'utils', 'result_page.py')
render = load_module('relaxaicode_render', 'utils', 'relaxaicode_render.py')
primary = load_module('primary_artifact', 'utils', 'primary_artifact.py')
basket = load_module('turn_presentation_basket', 'utils', 'turn_presentation_basket.py')
compact = load_module('history_compact', 'utils', 'history_compact.py')

_CANVAS = '/chatboo/canvas/7?rev=3'
_MAP = 'https://example.invalid/geo/map/abcd'


def test_the_generic_key_wins_and_the_old_spelling_still_reads():
    assert rp.page_url_on_result({'page_url': _CANVAS}) == _CANVAS
    assert rp.page_url_on_result({'map_url': _MAP}) == _MAP
    assert rp.page_url_on_result({'pins_url': _MAP}) == _MAP
    assert rp.page_url_on_result({'page_url': _CANVAS, 'map_url': _MAP}) == _CANVAS
    assert rp.page_url_on_result({}) == ''
    assert rp.page_url_on_result({'page_url': 'javascript:boom'}) == ''
    assert rp.page_url_on_result(None) == ''


def test_the_card_is_chosen_by_the_content_not_by_the_module():
    rows = [{'City': 'Sevilla'}]
    page = render.fallback_table_html({'data': rows, 'page_url': _CANVAS})
    assert 'o_ai_page_link' in page
    assert 'o_ai_map_banner' not in page
    shared = render.fallback_table_html({'data': rows, 'page_url': _MAP})
    assert 'o_ai_map_banner' in shared
    assert 'o_ai_page_link' not in shared
    # One painter: a page is never both a card and a link.
    assert render._result_page_html({'page_url': _CANVAS}).count('<a ') == 1
    assert 'target="_blank"' in render._result_page_html({'page_url': _CANVAS})
    assert 'o_ai_page_link_card' in render._result_page_html(
        {'page_url': _CANVAS},
    )
    empty = render.fallback_table_html({
        'data': [],
        'summary': 'Weekly forecast',
        'page_url': _CANVAS,
    })
    assert empty
    assert 'o_ai_page_link_card' in empty
    payload = {'data': [], 'page_url': _CANVAS, 'summary': 'Weekly forecast'}
    assert render.maybe_attach_formatted_text(payload) is True
    assert 'o_ai_page_link_card' in payload['formatted_text']


def test_a_page_is_an_artifact_the_turn_keeps_and_remembers():
    payload = {'page_url': _CANVAS, '__phase__': 'presentation'}
    assert primary.is_hollow(payload) is False
    assert basket.has_presentable_content(payload) is True
    assert compact.inspect_payload(payload).get('is_artifact') is True
    assert 'page_url' in primary.PRESENTATION_KEYS
    assert 'page_url' in basket._BLOCK_KEYS


def test_a_wanted_page_is_only_the_card():
    class Env:
        context = {rp.PAGE_REQUEST_KEY: {}}

    assert rp.note_page_wanted(Env)
    assert rp.page_wanted(Env)
    payload = {'data': [{'Cliente': 'ACME'}], 'page_url': _CANVAS}
    rp.mark_page_only(payload)
    assert payload['__page_only__'] is True
    html = render.fallback_table_html(payload)
    assert 'o_ai_page_link_card' in html
    # maybe_attach with the flag skips the data table.
    attached = {'data': [{'Cliente': 'ACME'}], 'page_url': _CANVAS}
    assert render.maybe_attach_formatted_text(attached) is True
    assert 'o_ai_page_link_card' in attached['formatted_text']
    assert 'ACME' not in attached['formatted_text']
    assert attached.get('__stop_after_direct__') is True
    mapped = {'data': [{'Cliente': 'ACME'}], 'page_url': _MAP}
    assert render.maybe_attach_formatted_text(mapped) is True
    assert 'ACME' not in mapped['formatted_text']


def test_a_page_without_rows_waits_then_uses_them():
    class Env:
        context = {rp.PAGE_REQUEST_KEY: {}}

    seen = []

    def fulfill(env, rows):
        seen.append(list(rows))
        return '/page/1'

    assert rp.note_page_waiting(Env, fulfill)
    empty = {'data': [], 'summary': 'soon'}
    rp.fulfill_waiting_page(Env, empty)
    assert 'page_url' not in empty
    payload = {'data': [{'Day': 'Sat', 'Max': 28}]}
    rp.fulfill_waiting_page(Env, payload)
    assert payload['page_url'] == '/page/1'
    assert seen == [[{'title': '', 'data': [{'Day': 'Sat', 'Max': 28}]}]]
    tables = {
        'tables': [
            {'title': 'KPIs', 'data': [{'Metric': 'Sales', 'Value': 10}]},
            {'title': 'Months', 'data': [{'Month': 'Jan', 'Untaxed': 3}]},
        ],
    }
    assert rp.blocks_on_payload(tables) == [
        {'title': 'KPIs', 'data': [{'Metric': 'Sales', 'Value': 10}]},
        {'title': 'Months', 'data': [{'Month': 'Jan', 'Untaxed': 3}]},
    ]
    later = {'data': [{'Day': 'Sun'}], 'page_url': '/page/old'}
    Env.context[rp.PAGE_REQUEST_KEY]['waiting'] = True
    Env.context[rp.PAGE_REQUEST_KEY]['fulfill'] = fulfill
    rp.fulfill_waiting_page(Env, later)
    assert later['page_url'] == '/page/old'
    engine = engine_source()
    assert 'PAGE_REQUEST_KEY' in engine
    assert 'fulfill_waiting_page(' in engine
    assert '_claim_page_turn(' in engine
    assert '_offer_page_card(' in engine
    assert 'matched_domain_codes' in engine
    page_done = engine.split('_page_card = self._offer_page_card', 1)[1].split(
        'return', 1,
    )[0]
    assert '_done_event(' in page_done
    assert 'local=True' not in page_done


def test_a_page_laid_out_before_the_result_names_it_takes_that_name():
    """5VZC: page_url(rows) first, result['summary'] after; the tab said Canvas."""
    class Env:
        context = {rp.PAGE_REQUEST_KEY: {}}

    seen = []
    assert rp.note_page_untitled(Env, lambda env, href, title: seen.append((href, title)))
    assert not rp.title_untitled_page(Env, {'summary': 'No page here'})
    payload = {
        'data': [{'Plate': '0000 BBB'}],
        'summary': 'Fleet catalogue (17 vehicles)',
        'page_url': _CANVAS,
    }
    assert rp.title_untitled_page(Env, payload)
    assert seen == [(_CANVAS, 'Fleet catalogue (17 vehicles)')]
    assert not rp.title_untitled_page(Env, payload)
    assert rp.note_page_untitled(Env, lambda env, href, title: seen.append(title))
    assert rp.title_untitled_page(Env, {'page_url': _CANVAS}, 'From the tool call')
    assert seen[-1] == 'From the tool call'
    assert rp.note_page_untitled(Env, lambda env, href, title: seen.append(title))
    assert not rp.title_untitled_page(Env, {'page_url': _CANVAS})
    engine = engine_source()
    tool_end = engine.split('_had_page = has_page_url(turn._payload)', 1)[1].split(
        'self._offer_page_card(turn._payload)', 1,
    )[0]
    assert 'title_untitled_page(' in tool_end


def test_the_contract_does_not_name_a_module():
    src = (_ROOT / 'common' / 'utils' / 'result_page.py').read_text(
        encoding='utf-8',
    )
    for word in ('chatboo', 'geo', 'canvas', 'pns_'):
        assert word not in src.lower().replace('page in its own', '')
