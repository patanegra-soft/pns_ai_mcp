# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""User-session clock helpers (no Odoo runtime)."""
from __future__ import annotations

from datetime import timezone

from _load_addon import load_module

ut = load_module('user_time', 'utils', 'user_time.py')


def test_naive_iso_treated_as_utc_then_user_tz():
    iso, tz = ut.normalize_clock_iso(
        '2026-08-15T22:31:08', 'Europe/Madrid',
    )
    assert tz == 'Europe/Madrid'
    assert iso == '2026-08-16T00:31:08+02:00'


def test_aware_iso_converted_to_user_tz():
    iso, tz = ut.normalize_clock_iso(
        '2026-08-15T22:31:08+00:00', 'Europe/Madrid',
    )
    assert tz == 'Europe/Madrid'
    assert iso == '2026-08-16T00:31:08+02:00'


def test_no_tz_leaves_naive_iso():
    iso, tz = ut.normalize_clock_iso('2026-08-15T22:31:08', None)
    assert iso == '2026-08-15T22:31:08'
    assert tz is None


def test_card_tz_converts_session_offset():
    iso, tz = ut.normalize_clock_iso(
        '2026-08-15T23:15:00+02:00', 'Asia/Tokyo',
    )
    assert tz == 'Asia/Tokyo'
    assert iso == '2026-08-16T06:15:00+09:00'


def test_user_local_now_is_aware():
    now = ut.user_local_now('UTC')
    assert now.tzinfo is not None
    assert now.utcoffset() == timezone.utc.utcoffset(now)
