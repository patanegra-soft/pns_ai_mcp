# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Parameter list ↔ param_schema. No invented unread keys."""
from __future__ import annotations

from _load_addon import load_module

sr = load_module('skill_runtime', 'utils', 'skill_runtime.py')


def test_empty_rows_to_empty_schema():
    assert sr.param_rows_to_schema([]) == {}
    assert sr.param_rows_fingerprint([]) == '[]'
    assert sr.param_rows_to_prose([]) == ''


def test_schema_rows_roundtrip_label_desc_default():
    schema = {
        'desde_hasta': {
            'type': 'string',
            'label': 'Period',
            'desc': 'YYYY or YYYY-YYYY. Empty = 12 months.',
            'default': '',
        },
    }
    rows = sr.schema_to_param_rows(schema)
    assert rows == [{
        'key': 'desde_hasta',
        'label': 'Period',
        'desc': 'YYYY or YYYY-YYYY. Empty = 12 months.',
        'default': '',
        'required': False,
    }]
    back = sr.param_rows_to_schema(rows, schema)
    assert back['desde_hasta']['label'] == 'Period'
    assert back['desde_hasta']['desc'] == 'YYYY or YYYY-YYYY. Empty = 12 months.'
    assert 'default' not in back['desde_hasta']


def test_label_equal_to_key_is_not_stored():
    rows = [{'key': 'mes', 'label': 'mes', 'desc': 'YYYY-MM', 'default': ''}]
    schema = sr.param_rows_to_schema(rows)
    assert 'label' not in schema['mes']
    assert schema['mes']['desc'] == 'YYYY-MM'


def test_integer_default_sets_type():
    rows = [{'key': 'anio', 'label': 'Year', 'desc': 'Calendar year', 'default': '2026'}]
    schema = sr.param_rows_to_schema(rows)
    assert schema['anio']['type'] == 'integer'
    assert schema['anio']['default'] == '2026'
    assert schema['anio']['label'] == 'Year'


def test_apply_code_keys_prefers_nameerror_keys():
    rows = [{'key': '', 'label': 'Period', 'desc': 'YYYY', 'default': ''}]
    out = sr.apply_code_keys_to_rows(rows, ['periodo', 'codes'])
    assert out[0]['key'] == 'periodo'
    assert out[0]['label'] == 'Period'


def test_identifier_label_becomes_key():
    rows = [{'key': '', 'label': 'codes', 'desc': 'CSV', 'default': ''}]
    out = sr.apply_code_keys_to_rows(rows, [])
    assert out[0]['key'] == 'codes'


def test_row_without_key_is_dropped_from_schema():
    rows = [{'key': '', 'label': 'Somewhere', 'desc': 'places', 'default': ''}]
    schema = sr.param_rows_to_schema(rows)
    assert schema == {}


def test_fingerprint_changes_with_desc():
    a = [{'label': 'Period', 'desc': 'YYYY', 'default': ''}]
    b = [{'label': 'Period', 'desc': 'YYYY-YYYY', 'default': ''}]
    assert sr.param_rows_fingerprint(a) != sr.param_rows_fingerprint(b)
    assert sr.param_rows_fingerprint(a) == sr.param_rows_fingerprint(list(a))


def test_help_prompt_uses_procedure_and_code():
    system, user = sr.build_param_help_prompt(
        [{'label': 'Period', 'desc': 'YYYY or YYYY-YYYY', 'default': ''}],
        procedure='Monthly billing table for a period.',
        code_body='result = {"data": []}',
    )
    assert 'Do not invent a capability' in system
    assert '{"help"' in system
    assert 'locale en_US' in system
    system_es, _user_es = sr.build_param_help_prompt(
        [],
        procedure='Monthly billing table for a period.',
        code_body='result = {"data": []}',
        lang='es_ES',
    )
    assert 'locale es_ES' in system_es
    assert 'Procedure:' in user
    assert 'Monthly billing table' in user
    assert 'Code:' in user
    assert 'Period' in user
    assert 'YYYY or YYYY-YYYY' in user
    assert 'desde_hasta' not in user


def test_procedure_template_is_not_a_help_source():
    assert sr.procedure_for_help('') == ''
    assert sr.procedure_for_help(sr._PROCEDURE_TEMPLATE) == ''
    assert sr.procedure_for_help(
        'When to use: describe the user request this skill answers.\n'
        'Parameters: always list them. Form Default or Code default; '
        'required keys show Help, never a Code fallback.'
    ) == ''
    assert sr.procedure_for_help('Show overdue invoices.') == (
        'Show overdue invoices.'
    )


def test_help_user_from_code_without_params():
    user = sr.build_skill_help_user(
        'List active users.', 'result = 1', [],
    )
    assert 'Procedure:' in user
    assert 'List active users.' in user
    assert 'Code:' in user
    assert 'Parameters' not in user
    assert sr.build_skill_help_user(sr._PROCEDURE_TEMPLATE, '', []) == ''


def test_help_fingerprint_changes_with_procedure():
    rows = [{'label': 'Period', 'desc': 'YYYY', 'default': ''}]
    a = sr.skill_help_fingerprint('Show invoices', 'result = 1', rows)
    b = sr.skill_help_fingerprint('Show overdue invoices', 'result = 1', rows)
    assert a != b
    assert sr.build_skill_help_user('', '', []) == ''


def test_preserve_choices_from_existing_schema():
    existing = {
        'codes': {
            'type': 'string',
            'desc': 'old',
            'choices_model': 'demo.item',
            'choices_code': 'x_code',
        },
    }
    rows = [{'key': 'codes', 'label': 'Codes', 'desc': 'CSV of codes.', 'default': ''}]
    schema = sr.param_rows_to_schema(rows, existing)
    assert schema['codes']['desc'] == 'CSV of codes.'
    assert schema['codes']['choices_model'] == 'demo.item'
    assert schema['codes']['choices_code'] == 'x_code'


def test_overlay_keeps_leftover_schema_keys():
    rows = [{'key': 'periodo', 'label': 'Period', 'desc': 'YYYY', 'default': ''}]
    schema = {
        'periodo': {'type': 'string', 'desc': 'old'},
        'codes': {'type': 'string', 'desc': 'CSV'},
    }
    out = sr.overlay_rows_on_schema(rows, schema)
    assert out['periodo']['desc'] == 'YYYY'
    assert out['codes']['desc'] == 'CSV'


def test_required_flag_roundtrip_and_prose():
    rows = [{
        'key': 'periodo',
        'label': 'Period',
        'desc': 'YYYY',
        'default': '',
        'required': True,
    }]
    schema = sr.param_rows_to_schema(rows)
    assert schema['periodo']['required'] is True
    back = sr.schema_to_param_rows(schema)
    assert back[0]['required'] is True
    prose = sr.param_rows_to_prose(rows)
    assert 'Required.' in prose
    optional = [{'key': 'codes', 'label': 'Codes', 'desc': 'CSV', 'default': ''}]
    assert 'required' not in sr.param_rows_to_schema(optional)['codes']
    a = [{'label': 'Period', 'desc': 'YYYY', 'default': '', 'required': False}]
    b = [{'label': 'Period', 'desc': 'YYYY', 'default': '', 'required': True}]
    assert sr.param_rows_fingerprint(a) != sr.param_rows_fingerprint(b)


def test_missing_required_after_defaults():
    schema = {
        'periodo': {'type': 'string', 'desc': 'YYYY', 'required': True},
        'codes': {'type': 'string', 'desc': 'CSV', 'default': 'ALL'},
    }
    assert sr.missing_required_params({}, schema) == ['periodo']
    assert sr.empty_args_need_required_ask(schema)
    filled = sr.apply_schema_defaults({}, schema)
    assert filled['codes'] == 'ALL'
    assert sr.missing_required_params({'periodo': '2026'}, schema) == []
    with_default = {
        'periodo': {
            'type': 'string', 'desc': 'YYYY',
            'required': True, 'default': '2026',
        },
    }
    assert sr.missing_required_params({}, with_default) == []
    assert not sr.empty_args_need_required_ask(with_default)
