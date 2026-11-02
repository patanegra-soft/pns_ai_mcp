# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""What the database refused, said to the person who asked for it."""
from _load_addon import addon_file, load_module, safe_plan_source


def _mod():
    return load_module('db_error_text', 'utils', 'db_error_text.py')


class _Field(object):
    def __init__(self, string):
        self.string = string


class _Model(object):
    _description = 'Iniciativa/Oportunidad'
    _fields = {'sequence_code': _Field('Código'), 'name': _Field('Nombre')}


class _Env(dict):
    def __getitem__(self, name):
        return _Model()


# The one the walkie hit: the code stayed at its placeholder and collided.
_DUPLICATE = (
    'duplicate key value violates unique constraint '
    '"crm_lead_crm_lead_unique_sequence_code"\n'
    'DETAIL:  Key (sequence_code)=(/) already exists.\n'
)


def test_a_duplicate_names_the_field_the_way_the_form_names_it():
    said = _mod().human_db_error(_Env(), _DUPLICATE, model='crm.lead')
    assert 'Código' in said
    # Not one word of the machinery reaches the phone.
    for noise in ('constraint', 'DETAIL', 'sequence_code', 'duplicate key'):
        assert noise not in said


def test_a_missing_value_is_named_not_described():
    said = _mod().human_db_error(
        _Env(),
        'null value in column "name" violates not-null constraint',
        model='crm.lead',
    )
    assert 'Nombre' in said
    assert 'null value' not in said


def test_an_unknown_refusal_keeps_its_sentence_without_the_trace():
    said = _mod().human_db_error(
        _Env(),
        'No puedes escribir en este registro.\nDETAIL:  something\nCONTEXT: x',
        model='crm.lead',
    )
    assert said == 'No puedes escribir en este registro.'


def test_the_card_says_nothing_was_written_before_the_reason():
    card = _mod().failed_ack(
        _Env(), 'Oportunidad Teleplaca', _DUPLICATE, model='crm.lead',
    )
    head, reason = card.split('\n\n')
    assert 'Oportunidad Teleplaca' in head
    assert 'Código' in reason


def test_the_card_speaks_the_language_of_the_caller():
    """Secretary runs public: the plain ``_`` would answer in English."""
    card = _mod().failed_ack(
        _Env(), 'Alta', _DUPLICATE, model='crm.lead',
        translate=lambda source: 'ES:' + source,
    )
    assert card.count('ES:') == 2


def test_every_sentence_it_says_is_in_both_spanish_catalogs():
    """Read off the file: a new sentence must not reach the phone in English."""
    import re
    from pathlib import Path

    source = addon_file('utils', 'db_error_text.py').read_text(encoding='utf-8')
    said = re.findall(r"say\(\s*'((?:[^'\\]|\\.)*)'", source)
    assert said, 'no sentences found — did the helper stop being named say()?'
    repo = Path(__file__).resolve().parents[1]
    for catalog in ('stacks/owl1/pns_ai_mcp/i18n/es.po',
                    'stacks/owl2/pns_ai_mcp/i18n/es_ES.po'):
        text = (repo / catalog).read_text(encoding='utf-8')
        for sentence in said:
            assert 'msgid "%s"' % sentence in text, (catalog, sentence)


def test_the_controller_stopped_pasting_the_driver_text():
    text = safe_plan_source()
    assert 'was confirmed but failed' not in text
    assert 'from ..utils.db_error_text import failed_ack' in text
