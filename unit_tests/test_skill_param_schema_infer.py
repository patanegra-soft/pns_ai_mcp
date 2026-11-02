# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Infer param_schema from try/except NameError — no invented keys."""
from __future__ import annotations

import json
from pathlib import Path

from _load_addon import load_module

sr = load_module('skill_runtime', 'utils', 'skill_runtime.py')

_NAMERROR_PERIODO = """
try:
    periodo = periodo
except NameError:
    periodo = None
result = {'data': [], '__return_direct__': True}
"""

_ALIAS_RANGO = """
try:
    _rango = rango
    codes = codes
except NameError:
    _rango = None
    codes = None
"""

_HARDCODED_FECHA = """
fecha = '2025-01-01'
partners = env['res.partner'].search([('create_date', '>=', fecha)])
result = {'data': [], '__return_direct__': True}
"""


def test_infers_nameerror_global():
    keys = sr.infer_param_keys_from_code(_NAMERROR_PERIODO)
    assert keys == ['periodo']
    schema = sr.infer_param_schema_from_code(_NAMERROR_PERIODO)
    assert list(schema) == ['periodo']
    assert schema['periodo']['type'] == 'string'
    assert 'Empty if absent' in schema['periodo']['desc']


def test_infers_alias_rhs_and_skips_private():
    keys = sr.infer_param_keys_from_code(_ALIAS_RANGO)
    assert keys == ['rango', 'codes']


def test_skips_sandbox_non_params():
    code = """
try:
    env = env
    arguments = arguments
    result = result
    mes = mes
except NameError:
    mes = None
"""
    assert sr.infer_param_keys_from_code(code) == ['mes']


def test_skips_argn_and_bare_except():
    code = """
try:
    arg0 = arg0
    lugar = lugar
except Exception:
    lugar = None
"""
    assert sr.infer_param_keys_from_code(code) == []


def test_does_not_invent_from_local_assignment():
    assert sr.infer_param_keys_from_code(_HARDCODED_FECHA) == []
    assert sr.infer_param_schema_from_code(_HARDCODED_FECHA) == {}


def test_syntax_error_yields_empty():
    assert sr.infer_param_keys_from_code('def (') == []


def test_canonical_key_gets_format_desc():
    code = """
try:
    fecha = fecha
    year = year
except NameError:
    fecha = None
    year = None
"""
    schema = sr.infer_param_schema_from_code(code)
    assert schema['fecha']['desc'].startswith('YYYY-MM-DD')
    assert schema['year']['type'] == 'integer'


def test_fill_infers_when_empty_and_keeps_authored():
    schema, hint = sr.fill_capture_params(_NAMERROR_PERIODO, '', '')
    parsed = json.loads(schema)
    assert 'periodo' in parsed
    assert hint == 'periodo=…'

    authored = '{"codes":{"type":"string","desc":"CSV"}}'
    schema2, hint2 = sr.fill_capture_params(_NAMERROR_PERIODO, authored, '')
    assert json.loads(schema2) == {'codes': {'type': 'string', 'desc': 'CSV'}}
    assert hint2 == 'codes=…'
    assert 'periodo' not in schema2


def test_fill_leaves_invalid_json_for_wizard():
    raw, hint = sr.fill_capture_params(_NAMERROR_PERIODO, '{nope', 'keep')
    assert raw == '{nope'
    assert hint == 'keep'


def test_system_prompt_does_not_ask_author_for_json():
    xml = (
        Path(__file__).resolve().parents[1]
        / 'common' / 'ai' / 'contexts' / 'core' / 'system_prompt.xml'
    ).read_text(encoding='utf-8')
    assert 'fills the schema from those names' in xml
    assert 'Do not write param_schema JSON' in xml
    assert 'closest formal' not in xml
    assert 'ordinals onto empty' not in xml
    assert 'declare `arg_hint`' not in xml
