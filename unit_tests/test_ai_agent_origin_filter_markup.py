# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Odoo 14 warns if class=btn sits on a span (simili button). Origin chips must be <a>."""
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _view(stack):
    return _ROOT / 'stacks' / stack / 'pns_ai_mcp' / 'views' / 'ai_agent_views.xml'


def _views():
    return (_view('owl1'), _view('owl2'), _view('owl3'))


def test_origin_filter_chips_are_anchors_not_spans():
    for path in _views():
        xml = path.read_text(encoding='utf-8')
        assert len(re.findall(r'class="btn btn-sm btn-primary [^"]*o_pns_origin_filter o_pns_tok_', xml)) == 8
        assert xml.count('<a href="#" role="button"') == 8
        assert '<span role="button"' not in xml


def test_owl2_origin_bars_use_no_bootstrap4_spacing():
    """Odoo 16+ ships Bootstrap 5: mr-1 is dead there, the chips glue together."""
    for stack in ('owl2', 'owl3'):
        xml = _view(stack).read_text(encoding='utf-8')
        assert not re.search(r'class="[^"]*\bmr-1\b', xml)
        css = (
            _ROOT / 'stacks' / stack / 'pns_ai_mcp' / 'static' / 'src' / 'css' / 'mcp_context.css'
        ).read_text(encoding='utf-8')
        assert '.o_pns_origin_filter_bar {' in css and 'gap:' in css


def test_owl2_composition_lists_are_not_inside_the_first_tab_child():
    """Odoo 16.3+ pulls an x2many inside a tab's first child up by 16px over the chips."""
    for stack in ('owl2', 'owl3'):
        xml = _view(stack).read_text(encoding='utf-8')
        for page in ('contexts', 'skills'):
            m = re.search(r'<page string="[^"]+" name="%s">\s*<div class="([^"]*)"' % page, xml)
            assert m and 'o_pns_origin_actions' in m.group(1)


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
