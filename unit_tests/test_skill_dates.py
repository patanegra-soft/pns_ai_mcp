# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Deterministic skill date phrases + hybrid param AI gate."""
from __future__ import annotations

from datetime import date

from _load_addon import load_module

sd = load_module('skill_dates', 'utils', 'skill_dates.py')
sr = load_module('skill_runtime', 'utils', 'skill_runtime.py')

# Friday 2026-08-07
TODAY = date(2026, 8, 7)


def test_try_resolve_basic_relatives():
    assert sd.try_resolve_date('hoy', TODAY) == TODAY
    assert sd.try_resolve_date('mañana', TODAY) == date(2026, 8, 8)
    assert sd.try_resolve_date('ayer', TODAY) == date(2026, 8, 6)
    assert sd.try_resolve_date('2026-08-13', TODAY) == date(2026, 8, 13)


def test_try_resolve_next_thursday():
    # Friday → next Thursday is 2026-08-13
    assert sd.try_resolve_date('el jueves que viene', TODAY) == date(2026, 8, 13)
    assert sd.try_resolve_date('próximo jueves', TODAY) == date(2026, 8, 13)
    assert sd.try_resolve_date('next Thursday', TODAY) == date(2026, 8, 13)


def test_try_resolve_this_friday_is_today():
    assert sd.try_resolve_date('este viernes', TODAY) == TODAY


def test_month_relatives_are_NOT_deterministic():
    """Hybrid contract: months/periods stay unresolved → LLM path."""
    assert sd.try_resolve_date('de hace 3 meses', TODAY) is None
    assert not hasattr(sd, 'try_resolve_month')


def test_enrich_params_sets_fecha():
    params = sr.parse_skill_arguments('el jueves que viene')
    assert params.get('lugar') == 'el jueves que viene'
    assert params.get('fecha') is None
    resolved = sd.try_resolve_date(params['lugar'], TODAY)
    assert resolved == date(2026, 8, 13)
    params['fecha'] = resolved.isoformat()
    schema = {'fecha': {'type': 'string', 'desc': 'day'}}
    assert not sr.schema_needs_ai_resolution(
        params, schema, 'el jueves que viene',
    )


def test_schema_needs_ai_for_unresolved_month_phrase():
    """«de hace 3 meses» + hole in mes → must invoke LLM (not invent parsers)."""
    schema = {
        'mes': {'type': 'string', 'desc': 'YYYY-MM'},
        'sort_by': {'type': 'string', 'desc': 'bruto|neto'},
    }
    params = sr.parse_skill_arguments('de hace 3 meses')
    sr.enrich_params_with_dates(params)
    assert params.get('mes') is None
    assert params.get('lugar') == 'de hace 3 meses'
    assert sr.schema_needs_ai_resolution(params, schema, 'de hace 3 meses')


def test_schema_skips_ai_for_canonical_mes_equals():
    schema = {
        'mes': {'type': 'string', 'desc': 'YYYY-MM'},
        'sort_by': {'type': 'string', 'desc': 'bruto|neto'},
    }
    params = sr.parse_skill_arguments('mes=2026-05')
    sr.enrich_params_with_dates(params)
    assert params.get('mes') == '2026-05'
    assert not sr.schema_needs_ai_resolution(params, schema, 'mes=2026-05')


def test_non_canonical_mes_counts_as_hole():
    assert not sr._param_value_resolved('mes', 'de hace 3 meses')
    assert sr._param_value_resolved('mes', '2026-05')


def test_schema_needs_ai_only_when_unresolved():
    schema = {'fecha': {'type': 'string', 'desc': 'day'}}
    params = {'lugar': 'el jueves que viene', 'fecha': '2026-08-13'}
    assert not sr.schema_needs_ai_resolution(
        params, schema, 'el jueves que viene',
    )
    params2 = {'lugar': 'dentro de tres quincenas lunares', 'fecha': None}
    assert sr.schema_needs_ai_resolution(
        params2, schema, 'dentro de tres quincenas lunares',
    )


def test_schema_skips_ai_for_help_tokens():
    """?, help, ayuda must never trigger hybrid LLM param extraction."""
    schema = {
        'periodo': {'type': 'string', 'desc': 'period'},
        'meses': {'type': 'integer', 'desc': 'N months'},
        'mes': {'type': 'string', 'desc': 'YYYY-MM'},
    }
    for raw in ('?', 'help', 'ayuda', 'opciones', '???'):
        params = sr.parse_skill_arguments(raw)
        sr.enrich_params_with_dates(params)
        assert sd.is_help_like(raw), raw
        assert not sr.schema_needs_ai_resolution(params, schema, raw), raw


def test_skill_args_are_help_options():
    assert sd.skill_args_are_help('?')
    assert sd.skill_args_are_help('options')
    assert sd.skill_args_are_help('OPTIONS')
    assert sd.skill_args_are_help('ayuda')
    assert sd.skill_args_are_help('help')
    assert not sd.skill_args_are_help('ytd')
    assert not sd.skill_args_are_help('2025')

