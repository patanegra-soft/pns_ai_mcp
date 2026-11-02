# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Unit tests for api_call LLM formatting and pagination hints."""
from __future__ import annotations

import json

import pytest

from _load_addon import load_module

acr = load_module('api_call_result', 'utils', 'api_call_result.py')


def test_small_json_passes_through():
    body = json.dumps([{'id': 1, 'name': 'a'}])
    llm, truncated, pagination = acr.format_api_call_body_for_llm(body, {'limit': 10})
    assert not truncated
    assert pagination is None
    assert llm == body


def test_large_list_is_paginated_not_blind_cut():
    items = [{'id': i, 'label': 'x' * 80} for i in range(200)]
    body = json.dumps(items)
    assert len(body) > acr.API_CALL_LLM_MAX_CHARS

    llm, truncated, pagination = acr.format_api_call_body_for_llm(
        body, {'limit': 50, 'offset': 0},
    )
    assert truncated
    assert pagination is not None
    assert pagination['has_more'] is True
    assert pagination['total_items'] == 200
    assert pagination['preview_items'] < 200
    assert len(llm) <= acr.API_CALL_LLM_MAX_CHARS
    parsed = json.loads(llm)
    assert isinstance(parsed, list)
    assert len(parsed) == pagination['preview_items']
    assert pagination['suggested_arguments']['offset'] == 50


def test_dict_with_list_field_paginates():
    items = [{'id': i, 'label': 'row-' + str(i)} for i in range(800)]
    body = json.dumps({'meta': {'page': 1}, 'data': items})
    assert len(body) > acr.API_CALL_LLM_MAX_CHARS
    llm, truncated, pagination = acr.format_api_call_body_for_llm(
        body, {'page': 1},
    )
    assert truncated
    assert pagination['list_field'] == 'data'
    parsed = json.loads(llm)
    assert len(parsed['data']) == pagination['preview_items']
    assert pagination['suggested_arguments']['page'] == 2


def test_cache_key_is_stable():
    k1 = acr.cache_key_for_api_call('srv', 'Tool', {'b': 1, 'a': 2})
    k2 = acr.cache_key_for_api_call('srv', 'Tool', {'a': 2, 'b': 1})
    assert k1 == k2


def test_cache_key_depends_on_the_user():
    args = {'q': 'x'}
    assert (acr.cache_key_for_api_call('srv', 'Tool', args, uid=7)
            != acr.cache_key_for_api_call('srv', 'Tool', args, uid=8))
