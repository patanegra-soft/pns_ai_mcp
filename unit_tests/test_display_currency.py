# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Unit tests for the display-currency ISO list and ICP read."""

from __future__ import annotations

from _load_addon import load_module

cur = load_module('display_currency', 'utils', 'display_currency.py')


def test_fifty_unique_iso_codes():
    codes = cur.currency_codes()
    assert len(codes) == 50
    assert len(set(codes)) == 50
    assert codes[0] == 'USD'
    assert 'EUR' in codes
    assert all(len(c) == 3 and c.isupper() for c in codes)


def test_normalize_currency():
    assert cur.normalize_currency('eur') == 'EUR'
    assert cur.normalize_currency('USD') == 'USD'
    assert cur.normalize_currency('nope') == 'USD'
    assert cur.normalize_currency(None) == 'USD'


def test_get_display_currency_reads_icp():
    class _ICP:
        def get_param(self, key, default=None):
            assert key == cur.ICP_DISPLAY_CURRENCY
            return 'EUR'

    class _Env:
        def __getitem__(self, name):
            assert name == 'ir.config_parameter'
            return self

        def sudo(self):
            return _ICP()

    assert cur.get_display_currency(_Env()) == 'EUR'


def test_get_display_currency_defaults_usd():
    class _ICP:
        def get_param(self, key, default=None):
            return default

    class _Env:
        def __getitem__(self, name):
            return self

        def sudo(self):
            return _ICP()

    assert cur.get_display_currency(_Env()) == 'USD'
