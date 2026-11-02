# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""An optional capability that did not run gets its own place and colour.

Where the row sits is the point: it goes on the turn thread, in the step
where the thing was asked for, greyed out. A row with no turn and step 0
tells you nothing about what had already happened.
"""
from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_LOG = (_ROOT / 'common' / 'models' / 'ai_log.py').read_text(encoding='utf-8')
_ENGINE = (_ROOT / 'common' / 'models' / 'ai_execution_engine.py').read_text(
    encoding='utf-8',
)


def test_the_endpoint_is_published_and_names_no_module():
    assert "CAPABILITY_SKIPPED = 'capability_skipped'" in _LOG
    head = _LOG.split('class AILog', 1)[0]
    for word in ('canvas', 'chatboo', 'design', 'page'):
        assert word not in head.lower()


def test_it_has_its_own_flow_colour_and_icon():
    assert "('skipped',      'Not done')" in _LOG
    flow = _LOG.split('def _compute_flow', 1)[1].split('\n    #', 1)[0]
    assert 'if ep == CAPABILITY_SKIPPED:' in flow
    assert "rec.flow = 'skipped'" in flow
    # ai.log is English on purpose: no _() on this surface.
    assert "rec.flow_label = rs or 'Not done'" in flow
    assert "'skipped': 'capability_skipped'" in _LOG
    assert "'capability_skipped': (" in _LOG
    assert "'Not done', True, 'capability_skipped'" in _LOG


def test_both_stacks_grey_the_row_out():
    for stack in ('owl1', 'owl2'):
        xml = (
            _ROOT / 'stacks' / stack / 'pns_ai_mcp' / 'views'
            / 'ai_log_views.xml'
        ).read_text(encoding='utf-8')
        assert xml.count('decoration-muted="flow == \'skipped\'"') == 2
        assert xml.count("'failover', 'external', 'skipped'") == 2


def test_the_missing_role_row_sits_in_the_turn():
    row = _ENGINE.split('def _log_role_without_provider', 1)[1].split(
        '\n    def ', 1,
    )[0]
    assert 'tool_name=CAPABILITY_SKIPPED' in row
    assert '_resolve_log_threading(turn, turn_step)' in row
    assert 'turn=turn,' in row
    assert 'turn_step=turn_step,' in row
    # The turn id travels in the env context, so a nested cursor keeps it.
    assert 'mcp_turn' in _ENGINE
