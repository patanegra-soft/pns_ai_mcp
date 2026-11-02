# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""A picture from another site reaches the page only through Odoo and the URL policy."""
from __future__ import annotations

import io
from pathlib import Path

import pytest

from common.utils import remote_image as ri

PIL = pytest.importorskip('PIL.Image')

_COMMON = Path(__file__).resolve().parents[1] / 'common'


def _picture(fmt, size=(20, 10), mode='RGB'):
    out = io.BytesIO()
    PIL.new(mode, size).save(out, format=fmt)
    return out.getvalue()


class _Resp:
    def __init__(self, status=200, headers=None, body=b''):
        self.status_code = status
        self.headers = headers or {}
        self.is_redirect = 300 <= status < 400 and 'Location' in self.headers
        self._body = body

    def iter_content(self, chunk_size=65536):
        yield self._body

    def close(self):
        pass


@pytest.fixture
def no_network(monkeypatch):
    import requests

    def _boom(*a, **k):
        raise AssertionError('network must not be touched')
    monkeypatch.setattr(requests, 'get', _boom)


def test_a_host_the_policy_refuses_is_never_called(no_network):
    assert ri.fetch_image_bytes('https://evil.example/p.png', lambda h: False) is None


def test_only_http_and_https(no_network):
    assert ri.fetch_image_bytes('file:///etc/passwd', lambda h: True) is None
    assert ri.fetch_image_bytes('ftp://x.example/p.png', lambda h: True) is None


def test_an_internal_address_is_refused_even_if_allowed(no_network):
    assert ri.fetch_image_bytes('http://127.0.0.1:8069/web/image', lambda h: True) is None


def test_a_redirect_is_checked_against_the_policy(monkeypatch):
    import requests
    monkeypatch.setattr(ri, 'non_public_host_error', lambda url: '')
    calls = []

    def _get(url, **kwargs):
        calls.append(url)
        assert kwargs.get('allow_redirects') is False
        return _Resp(302, {'Location': 'https://evil.example/p.png'})
    monkeypatch.setattr(requests, 'get', _get)
    allowed = lambda h: h == 'ok.example'
    assert ri.fetch_image_bytes('https://ok.example/p.png', allowed) is None
    assert calls == ['https://ok.example/p.png']


def test_the_body_has_a_cap(monkeypatch):
    import requests
    monkeypatch.setattr(ri, 'non_public_host_error', lambda url: '')
    big = b'x' * (ri.REMOTE_IMAGE_MAX_BYTES + 1)
    monkeypatch.setattr(requests, 'get', lambda url, **k: _Resp(200, {}, big))
    assert ri.fetch_image_bytes('https://ok.example/p.png', lambda h: True) is None


def test_an_allowed_picture_comes_back(monkeypatch):
    import requests
    monkeypatch.setattr(ri, 'non_public_host_error', lambda url: '')
    raw = _picture('PNG')
    monkeypatch.setattr(requests, 'get', lambda url, **k: _Resp(200, {}, raw))
    assert ri.fetch_image_bytes('https://ok.example/p.png', lambda h: True) == raw


@pytest.mark.usefixtures('pns_base_pdf_io')
def test_jpeg_stays_jpeg_and_the_rest_becomes_png():
    assert ri.reencode_image(_picture('JPEG'))[1] == 'image/jpeg'
    assert ri.reencode_image(_picture('GIF', mode='P'))[1] == 'image/png'
    assert ri.reencode_image(_picture('PNG', mode='RGBA'))[1] == 'image/png'


@pytest.mark.usefixtures('pns_base_pdf_io')
def test_a_large_picture_is_shrunk():
    payload, _mime = ri.reencode_image(_picture('PNG', size=(4000, 1000)))
    with PIL.open(io.BytesIO(payload)) as img:
        assert max(img.size) == ri.REMOTE_IMAGE_MAX_PX


@pytest.mark.parametrize('raw', [
    b'',
    b'not a picture',
    b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
    b'<html><script>alert(1)</script></html>',
])
@pytest.mark.usefixtures('pns_base_pdf_io')
def test_what_is_not_a_raster_never_comes_back(raw):
    assert ri.reencode_image(raw) is None


def test_the_route_needs_a_user_and_cannot_be_read_as_a_page():
    src = (_COMMON / 'controllers' / 'remote_image.py').read_text(encoding='utf-8')
    assert "auth='user'" in src
    assert 'may_show_remote_image' in src
    assert 'reencode_image(' in src
    assert "('X-Content-Type-Options', 'nosniff')" in src
    assert "default-src 'none'" in src
    init = (_COMMON / 'controllers' / '__init__.py').read_text(encoding='utf-8')
    assert 'from . import remote_image' in init
