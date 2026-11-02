# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Dashboard show_mode: grouped cards HTML."""
from __future__ import annotations

from _load_addon import load_module

render = load_module('relaxaicode_render', 'utils', 'relaxaicode_render.py')


def test_grouped_dashboard_html_renders_cards():
    result = {
        'summary': 'Cuadro de mandos',
        'show_mode': 'dashboard',
        'chart_engine': 'echarts',
        'groups': [
            {'title': 'Mes', 'data': [{'BA': 'COR', 'Margen': 100}], 'span': 2},
            {'title': 'Ranking', 'data': [{'BA': 'COR', 'Margen %': 12.5}]},
        ],
    }
    ctx = {'show_mode': 'dashboard', 'chart_engine': 'echarts'}
    html = render.grouped_dashboard_html(result, summary='Cuadro', render_context=ctx)
    assert html is not None
    assert 'o_ai_dashboard' in html
    assert 'o_ai_dashboard_card' in html
    assert 'data-ai-dashboard-id' in html
    assert 'data-card-id="c0-mes"' in html
    assert 'o_ai_dashboard_card_span2' in html
    assert 'data-ai-show-mode="show-chart"' in html
    assert 'o_ai_dashboard_reset' in html
    assert '>Restaurar<' in html or '>Restore<' in html
    assert 'Restaurar layout' not in html


def test_grouped_dashboard_skips_without_dashboard_mode():
    result = {
        'groups': [{'title': 'A', 'data': [{'x': 1}]}],
    }
    ctx = {'show_mode': 'show-table'}
    assert render.grouped_dashboard_html(result, render_context=ctx) is None


def test_no_charts_does_not_flatten_dashboard_to_stacked_tables():
    result = {
        'summary': 'Cuadro',
        'show_mode': 'dashboard',
        '__no_charts__': True,
        'groups': [
            {'title': 'Mes', 'rows': [{'Metric': 'Revenue', 'Value': 1}]},
            {'title': 'YTD', 'rows': [{'Metric': 'Revenue', 'Value': 2}]},
        ],
    }
    html = render.render_result_html(result, summary='Cuadro')
    assert 'o_ai_dashboard' in html
    assert html.count('class="o_ai_dashboard_card"') == 2
    assert 'o_ai_dashboard_winbtn' in html
    assert 'data-ai-dataset' not in html
    assert 'o_ai_grouped_result' not in html


def test_render_result_prefers_dashboard_over_vertical_groups():
    result = {
        'summary': 'Test',
        'show_mode': 'dashboard',
        'groups': [
            {'title': 'Bloque', 'data': [{'k': 1}]},
        ],
    }
    ctx = {'show_mode': 'dashboard', 'chart_engine': 'echarts'}
    html = render.render_result_html(result, summary='Test', render_context=ctx)
    assert 'o_ai_dashboard' in html
    assert '<h4 class="mt-3 mb-2"' not in html
