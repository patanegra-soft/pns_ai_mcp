# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Odoo 14 warns if class=btn sits on a span (simili button). Origin chips must be <a>."""
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _views():
    return (
        _ROOT / 'stacks' / 'owl1' / 'pns_ai_mcp' / 'views' / 'ai_agent_views.xml',
        _ROOT / 'stacks' / 'owl2' / 'pns_ai_mcp' / 'views' / 'ai_agent_views.xml',
    )


def test_origin_filter_chips_are_anchors_not_spans():
    for path in _views():
        xml = path.read_text(encoding='utf-8')
        assert xml.count('class="btn btn-sm btn-primary mr-1 o_pns_origin_filter') == 8
        assert xml.count('<a href="#" role="button"') == 8
        assert '<span role="button"' not in xml


def test_origin_filter_does_not_watch_the_whole_document():
    owl1 = (
        _ROOT / 'stacks' / 'owl1' / 'pns_ai_mcp' / 'static' / 'src' / 'js'
        / 'ai_agent_origin_filter_v14.js'
    ).read_text(encoding='utf-8')
    owl2 = (
        _ROOT / 'stacks' / 'owl2' / 'pns_ai_mcp' / 'static' / 'src' / 'js'
        / 'ai_agent_origin_filter.js'
    ).read_text(encoding='utf-8')
    for js in (owl1, owl2):
        assert 'document.documentElement' not in js
        assert 'function bindOriginOn' in js or 'function bindOriginOn(' in js
        assert 'o_pns_origin_filter_bar' in js
