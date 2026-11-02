# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""The engine does not write the chat module's name: not in code, comments,
views, catalogs or styles.

What is left are the named renames the ``-u`` runs once (old parameter keys,
old markup, the old compose token) and the trademark notice.
"""
from __future__ import annotations

from pathlib import Path

from _load_addon import load_module

_ROOT = Path(__file__).resolve().parents[1]
_HOST = 'chatboo'
_SUFFIXES = ('.py', '.xml', '.js', '.css', '.po')
# Named leftovers: they rename what older versions stored under the old name.
_RENAMES = (
    'common/utils/markup_rename.py',
    'common/utils/schema_fossils.py',
    'common/utils/formatting_mode_policy.py',
)


def _sources():
    for base in (_ROOT / 'common', _ROOT / 'stacks'):
        for path in sorted(base.rglob('*')):
            if path.suffix not in _SUFFIXES:
                continue
            if {'tests', 'migrations', '__pycache__'} & set(path.parts):
                continue
            rel = path.relative_to(_ROOT).as_posix()
            if rel in _RENAMES:
                continue
            yield rel, path.read_text(encoding='utf-8', errors='replace')


def test_no_host_name_outside_the_named_renames():
    params = load_module('engine_params', 'utils', 'engine_params.py')
    allowed = {old for old, _new in params.PREVIOUS_KEYS}
    found = []
    for rel, text in _sources():
        for lineno, line in enumerate(text.splitlines(), 1):
            if _HOST not in line.lower():
                continue
            if rel == 'common/utils/engine_params.py' and any(
                "'%s'" % key in line for key in allowed
            ):
                continue
            found.append('%s:%d: %s' % (rel, lineno, line.strip()))
    assert not found, '\n'.join(found)


def test_engine_reads_its_own_parameter_keys():
    params = load_module('engine_params', 'utils', 'engine_params.py')
    for key in (
        params.ICP_CHART_ENGINE,
        params.ICP_DEFAULT_SHOW_MODE,
        params.ICP_XLSX_FLOAT_DECIMALS,
        params.ICP_XLSX_THOUSANDS,
        params.ICP_DOWNLOAD_MAX_BYTES,
    ):
        assert key.startswith('pns_ai.')
    assert params.normalize_layout_show_mode('chart-table') == 'show-chart'
    assert params.normalize_layout_show_mode('dashboard') == 'show-table'
    assert params.normalize_chart_engine('ChartJS') == 'chartjs'
    assert params.normalize_xlsx_float_decimals(99) == 10


class _Env:
    """``env`` with one stored parameter and a company currency."""

    def __init__(self, stored=None, places=2):
        self.stored = stored
        self.company = type('C', (), {
            'currency_id': type('Cur', (), {'decimal_places': places})(),
        })()

    def __getitem__(self, name):
        return self

    def sudo(self):
        return self

    def get_param(self, key, default=None):
        return self.stored if self.stored is not None else default


def test_decimals_follow_the_company_currency_until_someone_sets_them():
    params = load_module('engine_params', 'utils', 'engine_params.py')
    assert params.xlsx_float_decimals(_Env(places=3)) == 3
    assert params.xlsx_float_decimals(_Env(places=0)) == 0
    assert params.xlsx_float_decimals(_Env(stored='4', places=3)) == 4
    assert params.xlsx_float_decimals(_Env(stored='x', places=3)) == 3
    assert params.currency_decimals(object()) == params.DEFAULT_XLSX_FLOAT_DECIMALS
