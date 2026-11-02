# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""A turn's file opens only for a logged-in user who may see it; no token URL."""
from __future__ import annotations

from pathlib import Path

_COMMON = Path(__file__).resolve().parents[1] / 'common'
_ROUTE = (_COMMON / 'controllers' / 'session_file.py').read_text(encoding='utf-8')
_DOWNLOAD = (_COMMON / 'utils' / 'session_download.py').read_text(encoding='utf-8')
_SVG = (_COMMON / 'utils' / 'svg_download.py').read_text(encoding='utf-8')


def test_the_route_needs_a_session_and_an_owner():
    assert "auth='user'" in _ROUTE
    assert "auth='public'" not in _ROUTE
    assert 'access_token' not in _ROUTE
    assert 'not _may_read(request.env, att)' in _ROUTE
    may = _ROUTE[_ROUTE.index('def _may_read'):_ROUTE.index('class ')]
    assert 'att.create_uid.id == env.uid' in may
    assert "check_access_rule('read')" in may


def test_only_svg_opens_inline():
    svg = _ROUTE.index("'image/svg+xml'")
    assert _ROUTE.index('sanitize_svg(', svg) < _ROUTE.index('else:', svg)
    assert 'content_disposition(name)' in _ROUTE[_ROUTE.index('else:', svg):]


def test_no_download_url_carries_a_token():
    assert 'access_token' not in _DOWNLOAD
    assert 'access_token' not in _SVG
