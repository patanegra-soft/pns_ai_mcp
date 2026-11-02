# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Usage display helpers for notifications and summaries."""
from __future__ import annotations

from pathlib import Path

from common.utils.display_currency import format_amount_with_symbol

_ROOT = Path(__file__).resolve().parents[1]


def test_usage_display_module_exports():
    src = (_ROOT / 'common' / 'utils' / 'usage_display.py').read_text(encoding='utf-8')
    assert 'def format_turn_tokens_label' in src
    assert 'def format_cost_label' in src
    assert 'def format_usage_chip' in src
    assert 'get_display_currency' in src
    assert 'format_amount_with_symbol' in src
    assert "env['ai.fx.source'].convert_usd" in src


def test_format_amount_with_symbol():
    assert format_amount_with_symbol('EUR', 0.05) == '0.05 €'
    assert format_amount_with_symbol('USD', 1.23) == '1.23 $'
    assert format_amount_with_symbol('GBP', 0.0012) == '0.0012 £'
    # A cheap parser call keeps two significant digits instead of 0.0000.
    assert format_amount_with_symbol('EUR', 0.000167) == '0.00017 €'
    assert format_amount_with_symbol('EUR', 0.00004) == '0.00004 €'
    assert format_amount_with_symbol('USD', 0.0000001) == '0.0000001 $'
    assert format_amount_with_symbol('SEK', 10.5) == '10.50 kr'
    assert format_amount_with_symbol('CHF', 2.0) == 'CHF 2.00'
    assert format_amount_with_symbol('EUR', -1) == '-'
    assert format_amount_with_symbol('EUR', None) == '-'


def test_ai_usage_chip_js_shared_owl2():
    js = (
        _ROOT / 'stacks' / 'owl2' / 'pns_ai_mcp'
        / 'static' / 'src' / 'js' / 'ai_usage_chip.js'
    ).read_text(encoding='utf-8')
    assert 'export function formatUsageChip' in js
    assert 'get_usage_display_context' in js


def test_log_usage_is_a_legend_chip_not_a_banner():
    model = (_ROOT / 'common' / 'models' / 'ai_log.py').read_text(encoding='utf-8')
    assert 'o_mcp_log_usage_chip' in model
    assert 'Colors:' not in model
    owl1 = (
        _ROOT / 'stacks' / 'owl1' / 'pns_ai_mcp'
        / 'static' / 'src' / 'js' / 'mcp_log_usage_summary_v14.js'
    ).read_text(encoding='utf-8')
    owl2 = (
        _ROOT / 'stacks' / 'owl2' / 'pns_ai_mcp'
        / 'static' / 'src' / 'js' / 'mcp_log_legend.js'
    ).read_text(encoding='utf-8')
    for js in (owl1, owl2):
        assert 'o_mcp_log_usage_chip' in js
        assert 'domain' in js
        assert 'days: 30' not in js
        assert 'Tokens and cost for the current filter' in js
        assert '_t(' not in js
        assert 'alert-info' not in js
        assert 'o_ai_usage_summary_banner' not in js or 'remove' in js
    assert 'get_user_usage_summary' in owl2
    assert 'mcp_log_usage_summary.js' not in owl2
    for rel in (
        'stacks/owl1/pns_ai_mcp/static/src/css/mcp_log_tree.css',
        'stacks/owl2/pns_ai_mcp/static/src/css/mcp_log_tree.css',
    ):
        css = (_ROOT / rel).read_text(encoding='utf-8')
        assert '.o_mcp_log_usage_chip' in css
        assert 'space-between' in css
        bar = css.split('.o_mcp_log_legend_bar {', 1)[1].split('}', 1)[0]
        assert 'align-items: center' in bar
        chip = css.split('.o_mcp_log_usage_chip {', 1)[1].split('}', 1)[0]
        assert 'background: #ffe082' in chip
        assert 'color: #1d1d1d' in chip
        assert 'border: 1px solid #e9ecef' in chip


def test_manifest_includes_usage_assets():
    manifest = (
        _ROOT / 'stacks' / 'owl2' / 'pns_ai_mcp' / '__manifest__.py'
    ).read_text(encoding='utf-8')
    assert 'ai_usage_chip.js' in manifest
    assert 'external_server_usage.js' in manifest
    assert 'mcp_log_legend.js' in manifest
    assert 'mcp_log_usage_summary.js' not in manifest
