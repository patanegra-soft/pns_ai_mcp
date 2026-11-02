# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Direct-return gating: probes vs user-facing tables."""
from __future__ import annotations

from _load_addon import load_module

render = load_module('relaxaicode_render', 'utils', 'relaxaicode_render.py')
policy = load_module('direct_return_policy', 'utils', 'direct_return_policy.py')


def test_maybe_attach_probe_does_not_mark_user_facing():
    result = {'data': [{'id': i, 'name': 'x'} for i in range(6)]}
    ok = render.maybe_attach_formatted_text(result, summary='Probe', force=False)
    assert ok
    assert result.get('formatted_text')
    assert not result.get('__return_direct__')
    assert result.get('__phase__') == 'extraction'


def test_maybe_attach_force_marks_user_facing():
    result = {'data': [{'id': i, 'name': 'x'} for i in range(6)]}
    ok = render.maybe_attach_formatted_text(result, summary='Final', force=True)
    assert ok
    assert result.get('__return_direct__')
    assert result.get('__presentation_complete__')


def test_should_show_direct_explicit_flag():
    payload = {'formatted_text': '<table></table>', '__return_direct__': True}
    assert policy.should_show_direct_to_chat(
        payload, round_n=3, max_rounds=10, tool_name='relaxaicode',
    )


def test_should_hide_probe_mid_turn():
    payload = {
        'formatted_text': '<table></table>',
        '__fmt_type__': 'server_side_python',
    }
    assert not policy.should_show_direct_to_chat(
        payload, round_n=3, max_rounds=10, tool_name='relaxaicode',
    )


def test_should_show_table_on_last_round_without_flag():
    payload = {
        'formatted_text': '<table></table>',
        '__fmt_type__': 'server_side_python',
    }
    assert policy.should_show_direct_to_chat(
        payload, round_n=10, max_rounds=10, tool_name='relaxaicode',
    )


def test_should_show_presentation_complete_mid_turn():
    payload = {
        'formatted_text': '<table></table>',
        '__fmt_type__': 'server_side_python',
        '__presentation_complete__': True,
        '__phase__': 'presentation',
    }
    assert policy.should_show_direct_to_chat(
        payload, round_n=4, max_rounds=10, tool_name='relaxaicode',
    )


def test_should_show_extraction_final_with_summary_mid_turn():
    payload = {
        'formatted_text': '<table></table>',
        '__fmt_type__': 'server_side_python',
        '__extraction_complete__': True,
        '__ready_for_presentation__': True,
        '__phase__': 'extraction',
        'summary': 'Puntualidad julio 2026',
    }
    assert policy.should_show_direct_to_chat(
        payload, round_n=4, max_rounds=10, tool_name='relaxaicode',
    )


def test_should_hide_extraction_probe_without_summary_mid_turn():
    payload = {
        'formatted_text': '<table></table>',
        '__fmt_type__': 'server_side_python',
        '__extraction_complete__': True,
        '__ready_for_presentation__': True,
    }
    assert not policy.should_show_direct_to_chat(
        payload, round_n=4, max_rounds=10, tool_name='relaxaicode',
    )


def test_last_round_hides_unmarked_catalogue_plus_records():
    """Stages + matching rows are a lookup. The last round must not paint them."""
    payload = {
        'formatted_text': '<table></table>',
        '__fmt_type__': 'server_side_python',
        '__phase__': 'extraction',
        'stages': [
            {'id': 1, 'name': 'New', 'is_won': False},
            {'id': 2, 'name': 'Won', 'is_won': True},
        ],
        'leads': [
            {'id': 9, 'name': 'Wet switchboard', 'sub_type': 'opportunity'},
        ],
    }
    assert policy.is_unmarked_multi_probe(payload)
    assert not policy.should_show_direct_to_chat(
        payload, round_n=10, max_rounds=10, tool_name='relaxaicode',
    )


def test_titled_sibling_tables_still_show_on_last_round():
    payload = {
        'formatted_text': '<table></table>',
        '__fmt_type__': 'server_side_python',
        '__phase__': 'extraction',
        '__extraction_complete__': True,
        '__ready_for_presentation__': True,
        'summary': 'Created by month',
        'by_count': [{'id': 1, 'name': 'A', 'n': 2}],
        'by_amount': [{'id': 1, 'name': 'A', 'amount': 3}],
    }
    assert not policy.is_unmarked_multi_probe(payload)
    assert policy.should_show_direct_to_chat(
        payload, round_n=10, max_rounds=10, tool_name='relaxaicode',
    )


def test_should_hide_last_round_fallback_when_primary_already_pinned():
    payload = {
        'formatted_text': '<table></table>',
        '__fmt_type__': 'server_side_python',
    }
    assert policy.should_show_direct_to_chat(
        payload, round_n=10, max_rounds=10, tool_name='relaxaicode',
    )
    assert not policy.should_show_direct_to_chat(
        payload, round_n=10, max_rounds=10, tool_name='relaxaicode',
        has_primary=True,
    )
