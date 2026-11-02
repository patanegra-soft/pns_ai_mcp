# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Frozen-row AST lock for skill code_body."""
from _load_addon import load_module

live = load_module('skill_live_code', 'utils', 'skill_live_code.py')


def test_pasted_three_dicts_is_frozen():
    src = (
        "data = [\n"
        "    {'id': 1, 'name': 'A'},\n"
        "    {'id': 2, 'name': 'B'},\n"
        "    {'id': 3, 'name': 'C'},\n"
        "]\n"
        "result = {'data': data, '__return_direct__': True}\n"
    )
    assert live.code_has_frozen_result_rows(src)


def test_search_loop_append_is_live():
    src = (
        "recs = env['res.partner'].search([], limit=10)\n"
        "data = []\n"
        "for rec in recs:\n"
        "    data.append({'id': rec.id, 'name': rec.name})\n"
        "result = {'data': data}\n"
    )
    assert not live.code_has_frozen_result_rows(src)


def test_two_dict_lookup_is_allowed():
    src = (
        "rows = [{'code': 'draft', 'name': 'Draft'}, "
        "{'code': 'done', 'name': 'Done'}]\n"
        "result = {'data': rows}\n"
    )
    assert not live.code_has_frozen_result_rows(src)


def test_api_call_only_is_allowed():
    src = (
        "result = {'propose_steps': ["
        "{'tool': 'api_call', 'url': 'https://example.test'}"
        "]}\n"
    )
    assert not live.code_has_frozen_result_rows(src)


def test_listcomp_from_records_is_allowed():
    src = (
        "recs = env['res.partner'].search([], limit=5)\n"
        "data = [{'id': r.id, 'name': r.name} for r in recs]\n"
        "result = {'data': data}\n"
    )
    assert not live.code_has_frozen_result_rows(src)


def test_empty_and_syntax_error_are_not_frozen():
    assert not live.code_has_frozen_result_rows('')
    assert not live.code_has_frozen_result_rows('data = [')
