# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""``kind=form`` card: a form the person opens and saves. Nothing is written here."""
from __future__ import annotations

import html
import json

from _load_addon import load_module

render = load_module('relaxaicode_render', 'utils', 'relaxaicode_render.py')
sr = load_module('skill_runtime', 'utils', 'skill_runtime.py')


def _card(**item):
    cards = render.collect_svg_cards({'card': dict({'kind': 'form'}, **item)})
    return cards[0] if cards else None


def test_form_card_keeps_action_values_and_lines():
    card = _card(
        action='account.action_move_in_invoice_type',
        title='Vendor bill',
        values={'partner_id': 7, 'invoice_date': '2026-03-10', 'ref': None},
        lines=['Vendor: ACME', ''],
    )
    assert card['action'] == 'account.action_move_in_invoice_type'
    assert card['values'] == {'partner_id': 7, 'invoice_date': '2026-03-10', 'ref': None}
    assert card['lines'] == ['Vendor: ACME']


def test_form_card_needs_an_action_or_a_model():
    assert _card(title='Nothing to open') is None
    assert _card(action='javascript:alert(1)') is None
    assert _card(model='Res Partner') is None
    assert _card(model='res.partner')['title'] == 'res.partner'


def test_form_card_drops_odd_field_names():
    card = _card(model='res.partner', values={'name': 'ACME', 'bad key': 1, 'Name': 2})
    assert card['values'] == {'name': 'ACME'}


def test_an_existing_record_carries_no_values():
    card = _card(model='res.partner', res_id=5, values={'name': 'ACME'})
    assert card['res_id'] == 5
    assert 'values' not in card


def test_form_card_html_lists_every_field_and_has_the_button():
    out = render.render_svg_cards_html({'card': {
        'kind': 'form',
        'model': 'res.partner',
        'title': '<b>New</b> contact',
        'values': {'name': 'ACME', 'email': 'info@example.com'},
        'lines': ['Name: ACME'],
    }})
    assert 'o_ai_form_card' in out
    assert 'o_ai_form_card_open' in out
    assert 'email, name' in out
    assert '<b>New</b>' not in out
    raw = out.split('data-ai-card="', 1)[1].split('"', 1)[0]
    assert json.loads(html.unescape(raw))['values']['name'] == 'ACME'


def test_a_card_alone_is_a_skill_presentation():
    pres = sr.presentation_from_bootstrap({
        'card': {'kind': 'form', 'model': 'res.partner'},
    })
    assert pres is not None
