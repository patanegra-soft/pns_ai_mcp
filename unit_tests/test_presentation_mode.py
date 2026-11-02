# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Presentation show_mode detection and HTML attribute."""
from __future__ import annotations

import inspect
from pathlib import Path

from _load_addon import engine_source, load_module

pm = load_module('presentation_mode', 'utils', 'presentation_mode.py')
render = load_module('relaxaicode_render', 'utils', 'relaxaicode_render.py')


def test_default_show_mode_table_chart():
    assert pm.normalize_show_mode(None) == pm.SHOW_MODE_TABLE_CHART
    assert pm.normalize_show_mode('') == pm.SHOW_MODE_TABLE_CHART
    assert pm.normalize_show_mode('bogus') == pm.SHOW_MODE_TABLE_CHART


def test_show_mode_from_context_not_model():
    class _Env:
        context = {'presentation_show_mode': 'show-chart'}
        user = type('U', (), {'lang': 'es_ES'})()

    assert pm._show_mode_from_session(_Env()) == pm.SHOW_MODE_CHART_TABLE


def test_result_show_mode_override():
    class _Env:
        context = {}
        user = type('U', (), {'lang': 'es_ES'})()

    mode = pm.resolve_show_mode_for_render(
        _Env(),
        result={'show_mode': 'chart-table'},
    )
    assert mode == pm.SHOW_MODE_CHART_TABLE


def test_legacy_result_showmode_override():
    class _Env:
        context = {}
        user = type('U', (), {'lang': 'es_ES'})()

    mode = pm.resolve_show_mode_for_render(
        _Env(),
        result={'showmode': 'chart-table'},
    )
    assert mode == pm.SHOW_MODE_CHART_TABLE


def test_table_block_open_emits_show_mode():
    html = render._table_block_open(
        [{'mes': '2025-01', 'total': 100}],
        render_context={'show_mode': 'chart-table'},
    )
    assert 'data-ai-show-mode="show-chart"' in html
    assert 'data-ai-chart-engine="echarts"' in html
    assert 'data-ai-dataset=' in html


def test_table_block_open_emits_chart_engine():
    html = render._table_block_open(
        [{'a': 1}],
        render_context={'chart_engine': 'chartjs'},
    )
    assert 'data-ai-chart-engine="chartjs"' in html


def test_normalize_dual_axis():
    assert pm.normalize_dual_axis(None) is None
    assert pm.normalize_dual_axis(False) is False
    assert pm.normalize_dual_axis(True) is True
    assert pm.normalize_dual_axis('single') is False
    assert pm.normalize_dual_axis('dual') is True
    assert pm.normalize_dual_axis('auto') is None


def test_table_block_open_emits_dual_axis():
    html = render._table_block_open(
        [{'mes': '2025-01', 'fact': 100, 'sal': 40}],
        render_context={'dual_axis': False},
    )
    assert 'data-ai-dual-axis="0"' in html
    html2 = render._table_block_open(
        [{'mes': '2025-01', 'fact': 100, 'pct': 25}],
        render_context={'dual_axis': True},
    )
    assert 'data-ai-dual-axis="1"' in html2
    html3 = render._table_block_open(
        [{'mes': '2025-01', 'fact': 100}],
        render_context={},
    )
    assert 'data-ai-dual-axis' not in html3


def test_result_dual_axis_override():
    class _Env:
        context = {}
        user = type('U', (), {'lang': 'es_ES'})()

    assert pm.resolve_dual_axis_for_render(
        _Env(),
        result={'dual_axis': False},
    ) is False
    assert pm.resolve_dual_axis_for_render(_Env(), result={}) is None


def test_table_block_open_default_show_mode():
    html = render._table_block_open(
        [{'mes': '2025-01', 'total': 100}],
        render_context={},
    )
    assert 'data-ai-show-mode="show-table"' in html


def test_fallback_table_shared_block_title():
    html = render.fallback_table_html(
        {'data': [{'area': 'INC', 'total': 100}], 'summary': 'Facturación por área'},
        render_context={'show_mode': 'chart-table'},
    )
    assert html
    assert 'o_ai_block_title' in html
    assert 'Facturación por área' in html
    assert html.index('o_ai_block_title') < html.index('table-responsive')


def test_the_engine_reads_no_words_to_pick_a_layout():
    src = Path(pm.__file__).read_text(encoding='utf-8')
    assert '_HINTS' not in src
    assert 'import re' not in src
    for fn in (pm.resolve_show_mode_for_render, pm.resolve_dual_axis_for_render):
        assert 'user_message' not in inspect.signature(fn).parameters

    class _Env:
        context = {
            'user_message': 'muéstrame un gráfico con un solo eje',
            'presentation_show_mode': 'show-table',
        }

    assert pm.resolve_show_mode_for_render(_Env()) == pm.SHOW_MODE_TABLE_CHART
    assert pm.resolve_dual_axis_for_render(_Env()) is None


def test_only_the_layout_pair_moves_the_session():
    assert pm.layout_from_result({'show_mode': 'show-chart'}) == pm.SHOW_MODE_CHART_TABLE
    assert pm.layout_from_result({'show_mode': 'table-chart'}) == pm.SHOW_MODE_TABLE_CHART
    assert pm.layout_from_result({'show_mode': 'dashboard'}) is None
    assert pm.layout_from_result({'show_mode': 'table'}) is None
    assert pm.layout_from_result({'show_mode': 'bogus'}) is None
    assert pm.layout_from_result({}) is None
    assert pm.layout_from_result(None) is None


def test_the_model_choice_reaches_the_host_from_relaxaicode_only():
    loop = engine_source()
    block = loop.split("if tool_name == 'relaxaicode':\n                    from .presentation_mode import layout_from_result", 1)
    assert len(block) == 2
    assert 'presentation_show_mode=_layout' in block[1].split('_tool_loop_direct_candidate', 1)[0]
    assert "_done['presentation_show_mode'] = _ctx_show" in loop
