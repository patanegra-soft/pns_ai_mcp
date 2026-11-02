# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""fetch_url only reaches the public internet, hop by hop, with a size cap."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from _load_addon import safe_plan_source

_COMMON = Path(__file__).resolve().parents[1] / 'common'
_PLAN = safe_plan_source()
_OPENAPI = (_COMMON / 'lib' / 'api' / 'drivers' / 'openapi_driver.py').read_text(encoding='utf-8')


def _safe():
    spec = importlib.util.spec_from_file_location(
        'fetch_url_safe_for_ssrf_test', _COMMON / 'utils' / 'fetch_url_safe.py',
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize('url', [
    'http://127.0.0.1:8069/web',
    'http://10.0.0.5/',
    'http://192.168.1.1/',
    'http://172.16.0.1/',
    'http://169.254.169.254/latest/meta-data/',
    'http://100.64.0.1/',
    'http://0.0.0.0/',
    'http://[::1]/',
    'http://[::ffff:127.0.0.1]/',
    'http://[fe80::1]/',
])
def test_an_internal_address_is_refused(url):
    assert _safe().non_public_host_error(url)


def test_a_public_address_passes():
    assert _safe().non_public_host_error('https://8.8.8.8/') == ''


def test_a_url_without_host_is_refused():
    assert _safe().non_public_host_error('http:///nothing')


def _request_helper():
    start = _PLAN.index('def _fetch_url_request')
    return _PLAN[start:_PLAN.index('\ndef _execute_fetch_url', start)]


def test_every_hop_is_checked_before_it_is_sent():
    body = _request_helper()
    assert 'allow_redirects=False' in body
    assert 'allow_redirects=True' not in _PLAN
    loop = body[body.index('for _hop in range(FETCH_URL_MAX_REDIRECTS + 1)'):]
    assert loop.index('non_public_host_error(url)') < loop.index('_requests.request(')
    assert 'check_fetch_url_steps(' in loop


def test_the_body_is_read_with_a_cap():
    body = _request_helper()
    assert 'stream=True' in body
    assert 'iter_content(' in body
    assert 'len(body) > FETCH_URL_MAX_BYTES' in body


def test_fetch_url_goes_through_the_checked_request():
    start = _PLAN.index('def _execute_fetch_url')
    body = _PLAN[start:_PLAN.index('\n# ── api_call', start)]
    assert '_fetch_url_request(' in body
    assert '_requests.request(' not in body


def test_a_downloaded_spec_does_not_choose_the_host():
    start = _OPENAPI.index('def _base_url')
    body = _OPENAPI[start:_OPENAPI.index('def _find_operation', start)]
    assert 'self._spec_is_manual(server)' in body
    assert 'urlparse(url).hostname == spec_host' in body
    assert 'raise APIDriverError(' in body
