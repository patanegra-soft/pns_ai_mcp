# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""One skill runs from its own phrases. Several matches do not."""
from __future__ import annotations

from _load_addon import load_module

match = load_module(
    'skill_trigger_match', 'utils', 'skill_trigger_match.py',
)

_FINANCE = {
    'command': 'financial-health',
    'triggers': (
        'estado financiero, situación financiera, informe financiero, '
        'financial health'
    ),
}
_OTHER = {
    'command': 'fleet',
    'triggers': 'estado de la flota, fleet status',
}


def test_one_phrase_runs_that_skill_with_the_sentence():
    sentence = 'estado financiero de la empresa en septiembre de 2026'
    hit = match.match_one_skill(sentence, [_FINANCE, _OTHER])
    assert hit == ('financial-health', sentence)


def test_unrelated_sentence_does_not_run():
    assert match.match_one_skill(
        'perfil de los clientes que más facturan',
        [_FINANCE, _OTHER],
    ) is None


def test_two_hits_do_not_run():
    both = [
        _FINANCE,
        {'command': 'other', 'triggers': 'estado financiero'},
    ]
    assert match.match_one_skill(
        'estado financiero de la empresa', both,
    ) is None


def test_slash_is_left_to_the_slash_parser():
    assert match.match_one_skill(
        '/financial-health 2026-09', [_FINANCE],
    ) is None
