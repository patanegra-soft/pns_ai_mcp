# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Unit tests for FX feed parse and USD conversion."""

from __future__ import annotations

from _load_addon import load_module

fx = load_module('fx_rates', 'utils', 'fx_rates.py')


def test_parse_er_api_shape():
    rates = fx.parse_feed_rates({
        'result': 'success',
        'base_code': 'USD',
        'rates': {'EUR': 0.92, 'GBP': 0.78, 'usd': 1},
    })
    assert rates['EUR'] == 0.92
    assert rates['GBP'] == 0.78
    assert rates['USD'] == 1.0


def test_parse_rejects_junk():
    assert fx.parse_feed_rates(None) is None
    assert fx.parse_feed_rates({'rates': {}}) is None
    assert fx.parse_feed_rates({'rates': {'EURO': 0.9, 'bad': -1}}) is None


def test_convert_keeps_usd_without_rate():
    out = fx.convert_usd_amount(0.14, 'EUR', None)
    assert out['currency'] == 'USD'
    assert out['amount'] == 0.14
    assert out['rate'] == 1.0


def test_convert_uses_feed_rate():
    out = fx.convert_usd_amount(
        0.14, 'EUR', {'rates': {'EUR': 0.92}, 'as_of': '2026-08-15'},
    )
    assert out['currency'] == 'EUR'
    assert abs(out['amount'] - 0.1288) < 1e-9
    assert out['rate'] == 0.92
    assert out['as_of'] == '2026-08-15'
