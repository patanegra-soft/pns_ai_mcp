# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""A dictated sentence split among the fields that were asked for."""
import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / 'common' / 'utils' / 'spoken_fields.py'


def _mod():
    spec = importlib.util.spec_from_file_location('spoken_fields', _SRC)
    module = importlib.util.module_from_spec(spec)
    sys.modules['spoken_fields'] = module
    spec.loader.exec_module(module)
    return module


_FIELDS = [
    {'name': 'partner_id', 'label': 'Customer', 'type': 'many2one',
     'relation': 'res.partner'},
    {'name': 'name', 'label': 'Subject', 'type': 'char', 'relation': ''},
    {'name': 'date_deadline', 'label': 'Date', 'type': 'date', 'relation': ''},
]


def test_prose_around_the_answer_is_not_the_answer():
    """Models talk. What we can use is the object inside what they say."""
    mod = _mod()
    said = mod.read_answer(
        'Sure! Here you go:\n{"name": "Broken lift"}\nHope that helps.',
        _FIELDS,
    )
    assert said == {'name': 'Broken lift'}


def test_a_field_nobody_asked_for_is_dropped():
    mod = _mod()
    said = mod.read_answer(
        '{"name": "Lift", "user_id": 3, "priority": "1"}', _FIELDS,
    )
    assert said == {'name': 'Lift'}


def test_an_empty_answer_is_a_correct_answer():
    """Half a sentence fills half the script; it does not invent the rest."""
    mod = _mod()
    assert mod.read_answer('{}', _FIELDS) == {}
    assert mod.read_answer('', _FIELDS) == {}
    assert mod.read_answer('no idea', _FIELDS) == {}
    assert mod.read_answer('[1, 2]', _FIELDS) == {}


def test_a_cut_off_object_keeps_the_fields_that_closed():
    """The provider stops mid-JSON. What already closed is still a value."""
    mod = _mod()
    said = mod.read_answer(
        '{\n  "name": "Polipasto",\n  "partner_id": "EJÉRCITO DE TIERRA",\n'
        '  "date_deadline":',
        _FIELDS,
    )
    assert said == {
        'name': 'Polipasto',
        'partner_id': 'EJÉRCITO DE TIERRA',
    }
    assert mod.read_answer('{\n  "name": "P', _FIELDS) == {}
    assert mod.unfinished_answer('{\n  "name": "P')
    assert not mod.unfinished_answer('{}')
    assert not mod.unfinished_answer('')


def test_the_form_split_does_not_spend_tokens_on_thinking():
    """Thinking ate the 400-token budget and the object never closed."""
    source = _SRC.read_text(encoding='utf-8')
    body = source.split('def split_sentence')[1]
    assert 'disable_thinking=True' in body
    assert '_RETRY_TOKENS' in body
    assert 'unfinished_answer' in body


def test_nothing_useful_is_thrown_away_for_being_the_wrong_shape():
    mod = _mod()
    said = mod.read_answer(
        '{"partner_id": 0, "name": ["Broken", "lift"], "date_deadline": null}',
        _FIELDS,
    )
    assert said == {'partner_id': '0', 'name': 'Broken lift'}


def test_a_relation_comes_back_as_a_name_not_as_an_id():
    """An id guessed by a model is a wrong record; a name can be looked up."""
    mod = _mod()
    assert 'never an id' in mod._SYSTEM


def test_a_day_said_against_today_needs_today_to_be_said():
    """«Next Wednesday» is a phrase until it is told which day this is."""
    mod = _mod()
    assert mod._when('2026-09-22 (Tuesday)') == 'Today is 2026-09-22 (Tuesday).\n\n'
    assert mod._when('') == ''
    assert 'relative to today' in mod._SYSTEM


def test_the_name_may_be_said_in_front_of_the_value():
    """«Descripción avería en el tercero» is how people actually dictate.

    Told the speaker would never name a field, the model read the label as
    part of what was said and the value came back with the word «descripción»
    in front of it —or went to the wrong field altogether.
    """
    mod = _mod()
    assert 'may name a field before saying its value' in mod._SYSTEM
    assert 'not part of it' in mod._SYSTEM
    # And saying nothing is still an answer: it gets worked out.
    assert 'When nothing is named' in mod._SYSTEM


def test_a_field_that_lists_its_options_is_answered_from_them():
    """Choosing from fourteen is a far smaller question than naming one."""
    mod = _mod()
    lines = mod._field_lines([
        {'name': 'team_id', 'label': 'Area', 'type': 'many2one',
         'relation': 'crm.team', 'options': ['Lifts', 'Solar']},
    ])
    assert 'one of: Lifts | Solar' in lines
    assert 'even if the speaker used' in mod._SYSTEM


def test_a_field_is_asked_by_every_word_it_goes_by():
    """One word only, and the field never gets filled in by anyone else."""
    mod = _mod()
    lines = mod._field_lines([
        {'name': 'source_id', 'label': 'Origen', 'type': 'many2one',
         'relation': 'utm.source', 'also': ['fuente', 'origen']},
    ])
    assert 'also called fuente or origen' in lines
    # No words of any one language in here: whoever owns the record says
    # which they are, and the engine only passes them along.
    source = _SRC.read_text(encoding='utf-8')
    assert 'fuente' not in source


def test_what_is_in_a_field_already_is_read_out_with_it():
    """«The salesperson is Ann, not Bob» is a correction only to someone
    who can see that Bob is what is in there. Without it the sentence came
    back as a name with a «not Bob» stuck to the end of it.
    """
    mod = _mod()
    lines = mod._field_lines(
        [{'name': 'user_id', 'label': 'Salesperson', 'type': 'many2one',
          'relation': 'res.users'},
         {'name': 'name', 'label': 'Description', 'type': 'char'}],
        filled={'user_id': 'Bob'},
    )
    assert 'now: Bob' in lines
    # An empty one says nothing rather than saying it is empty.
    assert lines.count('now:') == 1
    assert 'the value that stands' in mod._SYSTEM
    assert 'never with the one being taken back' in mod._SYSTEM


def test_a_list_too_long_to_read_is_not_read_out():
    mod = _mod()
    many = ['Option %d' % i for i in range(mod.OPTIONS_MAX + 1)]
    lines = mod._field_lines([
        {'name': 'partner_id', 'label': 'Customer', 'type': 'many2one',
         'relation': 'res.partner', 'options': many},
    ])
    assert 'one of:' not in lines


def test_no_words_of_any_one_language_decide_where_a_value_goes():
    """A list of Spanish words here is an app that only works in Spanish."""
    source = _SRC.read_text(encoding='utf-8')
    for word in ('cliente', 'fecha', 'asunto', 'customer', 'subject'):
        assert word not in source.lower().split('_SYSTEM')[0]


def test_nothing_is_asked_when_there_is_nothing_to_place():
    mod = _mod()
    assert mod.split_sentence(None, _FIELDS, '   ') == {}
    assert mod.split_sentence(None, [], 'anything') == {}


def test_what_the_record_is_born_with_decides_what_it_is_asked():
    """A model asks for different things depending on the kind of record."""
    source = (
        _ROOT / 'common' / 'utils' / 'required_fields.py'
    ).read_text(encoding='utf-8')
    wanted = source.split('def fields_wanted')[1].split('\ndef ')[0]
    assert 'missing_for_agent(env, model, given)' in wanted
    assert 'missing_required_fields(env, model, given)' in wanted
