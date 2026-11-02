# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Presentation axis slash helpers (compose / footmode / showmode)."""
from __future__ import annotations

from _load_addon import load_module

f = load_module('formatting_mode_policy', 'utils', 'formatting_mode_policy.py')


def test_parse_axis_slashes_alone():
    axis, value, rest = f.parse_axis_slash('/compose-agent')
    assert axis == f.AXIS_COMPOSE
    assert value == f.COMPOSE_AGENT
    assert rest == ''
    axis, value, rest = f.parse_axis_slash('/compose-model')
    assert value == f.COMPOSE_MODEL
    axis, value, rest = f.parse_axis_slash('/foot-verbose')
    assert axis == f.AXIS_FOOTMODE
    assert value == f.FOOT_VERBOSE
    axis, value, rest = f.parse_axis_slash('/foot-laconic')
    assert value == f.FOOT_LACONIC
    axis, value, rest = f.parse_axis_slash('/show-table')
    assert axis == f.AXIS_SHOWMODE
    assert value == f.SHOW_TABLE
    axis, value, rest = f.parse_axis_slash('/show-chart')
    assert value == f.SHOW_CHART


def test_retired_report_table_are_not_aliases():
    axis, value, rest = f.parse_axis_slash('/report')
    assert axis is None
    assert '/report' in rest
    axis, value, rest = f.parse_axis_slash('/table situación')
    assert axis is None
    axis, value, rest = f.parse_axis_slash('/painter-local')
    assert axis is None
    axis, value, rest = f.parse_axis_slash('/painter-free')
    assert axis is None


def test_normalize_compose_rejects_old_names():
    assert f.normalize_compose('compose-model') == f.COMPOSE_MODEL
    assert f.normalize_compose('compose-agent') == f.COMPOSE_AGENT
    assert f.normalize_compose('compose-chatboo') == f.COMPOSE_AGENT
    assert f.normalize_compose('painter-free') is None
    assert f.normalize_compose('painter-local') is None
    assert f.normalize_compose('report') is None
    assert f.normalize_compose('table') is None
    assert f.normalize_compose('') is None
    assert f.normalize_compose(None) is None


def test_resolve_compose_priority():
    assert f.resolve_compose(turn_value='compose-model') == f.COMPOSE_MODEL
    assert f.resolve_compose(turn_value='compose-agent') == f.COMPOSE_AGENT
    assert f.resolve_compose(provider_value='compose-model') == f.COMPOSE_MODEL
    assert f.resolve_compose() == f.COMPOSE_AGENT
    assert f.resolve_compose(
        turn_value='compose-agent', explicit=True,
    ) == f.COMPOSE_MODEL
    assert f.resolve_compose(
        skill_value='compose-model', provider_value='compose-agent',
    ) == f.COMPOSE_MODEL


def test_resolve_footmode():
    assert f.resolve_footmode(provider_value='foot-laconic') == f.FOOT_LACONIC
    assert f.resolve_footmode(turn_value='foot-verbose',
                              provider_value='foot-laconic') == f.FOOT_VERBOSE
    assert f.resolve_footmode() == f.FOOT_VERBOSE


def test_apply_turn_axis_showmode_parses_without_write():
    axis, value, rest = f.apply_turn_axis(
        None, '/show-chart facturación mensual',
    )
    assert axis == f.AXIS_SHOWMODE
    assert value == f.SHOW_CHART
    assert 'facturación' in rest


def test_system_prompt_uses_axis_tokens():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / 'common' / 'ai' / 'contexts'
    xml = (root / 'core' / 'system_prompt.xml').read_text(encoding='utf-8')
    assert 'presentation_grids' not in xml
    assert 'compose-agent' not in xml
    assert 'ai.provider.laconic_mode' not in xml
    assert 'formatting_mode: report' not in xml
    assert 'datetime.now()' in xml
    assert 'NEVER INVENT DATA' not in xml
    assert 'NEVER FABRICATE' in xml
    assert 'pyjama' not in xml
    assert 'MEJORES' not in xml
    assert 'No hay datos' not in xml
    assert 'Bootstrap' not in xml
    assert 'on-screen image' not in xml
    assert 'No data for the period.' in xml
    assert 'install pin' in xml
    assert 'FORBIDDEN: drawing charts yourself with SVG' not in xml


def test_system_prompt_says_when_previous_result_applies():
    """First-turn extraction must not bind result to an empty prior list."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    xml = (
        root / 'common' / 'ai' / 'contexts' / 'core' / 'system_prompt.xml'
    ).read_text(encoding='utf-8')
    tool = (
        root / 'common' / 'controllers' / 'tools_relaxaicode.py'
    ).read_text(encoding='utf-8')
    needle = "previous_result.get('data') or []"
    assert 'PREVIOUS RESULT' in xml
    assert needle in xml
    assert 'already returned rows' in xml
    assert needle in tool
    assert 'already returned rows' in tool


def test_system_prompt_names_sandbox_version_globals():
    """The prompt must name sandbox globals; never import odoo.release."""
    from pathlib import Path
    xml = (
        Path(__file__).resolve().parents[1]
        / 'common' / 'ai' / 'contexts' / 'core' / 'system_prompt.xml'
    ).read_text(encoding='utf-8')
    assert 'odoo.release' not in xml
    assert 'name="odoo_version"' in xml
    assert 'name="odoo_series"' in xml
    assert 'relaxaicode globals (odoo_version, odoo_series' in xml


def test_excel_formulas_live_on_host_not_core():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / 'common' / 'ai' / 'contexts'
    xml = (root / 'core' / 'system_prompt.xml').read_text(encoding='utf-8')
    ae = load_module('artifact_export', 'utils', 'artifact_export.py')
    assert 'EXCEL FORMULAS' not in xml
    assert '__excel_formulas__' not in xml
    assert 'presentation_grids' not in xml
    assert 'geocode' not in xml
    assert '__excel_formulas__' in ae.SESSION_FILE_PROTOCOL
