# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Escape stray % in old-style string formatting (7F9J)."""
from __future__ import annotations

from _load_addon import load_module

v_repair = load_module('validators_repair', 'controllers', 'validators_repair.py')


def test_escape_keeps_real_conversions():
    src = 'paid %.0f%% of %s'
    assert v_repair.escape_stray_percent_in_format(src) == src


def test_escape_kpi_equals_percent():
    src = 'Excluidos buenos pagadores: Deuda % = pendiente / facturado < %.0f%%.'
    out = v_repair.escape_stray_percent_in_format(src)
    assert out == (
        'Excluidos buenos pagadores: Deuda %% = pendiente / facturado < %.0f%%.'
    )
    assert out % 10.0 == (
        'Excluidos buenos pagadores: Deuda % = pendiente / facturado < 10%.'
    )


def test_repair_7f9j_footer_and_leave_dict_keys():
    src = (
        "rows = [{'Deuda %': 88.16}]\n"
        "n = 3 % 2\n"
        "result = ("
        "'Excluidos buenos pagadores: Deuda % = pendiente / facturado < %.0f%%.'"
        ") % 10.0\n"
    )
    out, changed = v_repair.repair_percent_format_strings(src)
    assert changed
    assert "'Deuda %'" in out or '"Deuda %"' in out
    ns = {}
    exec(out, ns, ns)
    assert ns['n'] == 1
    assert ns['rows'][0]['Deuda %'] == 88.16
    assert 'Deuda % =' in ns['result']
    assert '10%' in ns['result']


def test_repair_noop_when_already_valid():
    src = "result = 'paid %.0f%%' % 10.0\n"
    out, changed = v_repair.repair_percent_format_strings(src)
    assert not changed
    assert out == src
