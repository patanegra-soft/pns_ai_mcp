# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""A related record is named and placed, so the reader knows which one it is."""
from _load_addon import load_module


def _mod():
    return load_module('record_label', 'utils', 'record_label.py')


class _Rec(object):
    def __init__(self, name, placed=None, show_address=False):
        self.display_name = name
        self._placed = placed
        self._show_address = show_address

    def sudo(self):
        return self

    def browse(self, rid=None):
        return self

    def exists(self):
        return True

    def with_context(self, **kw):
        return _Rec(self.display_name, self._placed, bool(kw.get('show_address')))

    def name_get(self):
        if self._show_address and self._placed:
            return [(1, self._placed)]
        return [(1, self.display_name)]


class _Env(object):
    def __init__(self, **models):
        self._models = models

    def __contains__(self, name):
        return name in self._models

    def __getitem__(self, name):
        return self._models[name]


def _env_with(name, placed=None):
    return _Env(**{'a.model': _Rec(name, placed)})


def test_the_label_carries_street_zip_city_province_and_country():
    env = _env_with(
        'HOTEL ACME',
        'HOTEL ACME\nCTRA. NACIONAL KM 100, \n99999 VILLAEJEMPLO (Jaén, Spain)',
    )
    assert _mod().placed_label(env, 'a.model', 7629) == (
        'HOTEL ACME — CTRA. NACIONAL KM 100, 99999 VILLAEJEMPLO (Jaén, Spain)'
    )


def test_a_missing_part_does_not_leave_its_punctuation_behind():
    """The format prints blind: no province still printed «(, Spain)»."""
    env = _env_with(
        'ACME TALLERES CB',
        'ACME TALLERES CB\nCALLE MAYOR 12-14, \n99999 VILLAEJEMPLO (, Spain)',
    )
    assert _mod().placed_label(env, 'a.model', 5788) == (
        'ACME TALLERES CB — CALLE MAYOR 12-14, 99999 VILLAEJEMPLO (Spain)'
    )


def test_a_model_that_cannot_place_itself_answers_with_its_name():
    assert _mod().placed_label(_env_with('Sales'), 'a.model', 31) == 'Sales'


def test_nothing_to_read_is_no_label_and_no_crash():
    mod = _mod()
    env = _env_with('Sales')
    assert mod.placed_label(env, 'no.such.model', 1) == ''
    assert mod.placed_label(None, 'a.model', 1) == ''
    assert mod.placed_label(env, 'a.model', 0) == ''
