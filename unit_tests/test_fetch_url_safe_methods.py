# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Regression: fetch_url allows only safe methods (no network, no DB).

POST/PUT/PATCH/DELETE must be rejected at validation — not an intrusion
against real URLs; the oracle is the policy error message.
"""
from __future__ import annotations

import pytest

from _load_addon import load_module

fu = load_module('fetch_url_safe', 'utils', 'fetch_url_safe.py')


@pytest.mark.parametrize('method', sorted(fu.FETCH_URL_SAFE_METHODS))
def test_safe_methods_accepted(method):
    step = {'url': 'https://example.com/api', 'method': method}
    if method == 'QUERY':
        step['body'] = '{"q":1}'
        step['content_type'] = 'application/json'
    ok, err = fu.validate_fetch_url_step(step)
    assert ok, err
    assert err is None


@pytest.mark.parametrize('method', [
    'POST', 'PUT', 'PATCH', 'DELETE', 'CONNECT', 'TRACE', 'post', 'delete',
])
def test_mutating_methods_rejected(method):
    ok, err = fu.validate_fetch_url_step({
        'url': 'https://example.com/resource',
        'method': method,
    })
    assert not ok
    assert method.upper() in err
    assert 'GET' in err and 'QUERY' in err
    assert 'api_call' in err


def test_default_method_is_get():
    ok, err = fu.validate_fetch_url_step({'url': 'https://example.com/'})
    assert ok, err
    assert fu.normalize_fetch_url_method(None) == 'GET'


def test_query_requires_body_and_content_type():
    base = {'url': 'https://example.com/q', 'method': 'QUERY'}
    ok, err = fu.validate_fetch_url_step(base)
    assert not ok and 'body' in err
    ok, err = fu.validate_fetch_url_step({**base, 'body': '{}'})
    assert not ok and 'content_type' in err
    ok, err = fu.validate_fetch_url_step({
        **base, 'body': '{}', 'content_type': 'application/json',
    })
    assert ok, err


def test_non_http_url_rejected():
    ok, err = fu.validate_fetch_url_step({'url': 'ftp://evil.example/'})
    assert not ok
    assert 'http' in err.lower()
