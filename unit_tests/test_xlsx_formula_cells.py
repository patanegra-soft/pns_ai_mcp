# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Spreadsheet formula injection: text starting with =, +, - or @ is text.

Both XLSX writers quote such cells. Formulas the renderer declares on
purpose (column totals) stay live formulas.
"""
from __future__ import annotations

import io
import zipfile

from _load_addon import load_module

ae = load_module('artifact_export', 'utils', 'artifact_export.py')

_ROWS = [
    {'Name': '=1+1', 'Total': 10},
    {'Name': ' @SUM(A1:A2)', 'Total': 20},
    {'Name': '-5', 'Total': 30},
    {'Name': 'Alpha', 'Total': 40},
]


def _sheet_xml(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        names = [n for n in zf.namelist() if n.startswith('xl/worksheets/')]
        assert names
        return zf.read(names[0]).decode('utf-8')


def test_safe_text_prefixes_formula_starters():
    assert ae._xlsx_safe_text('=1+1') == "'=1+1"
    assert ae._xlsx_safe_text(' +cmd') == "' +cmd"
    assert ae._xlsx_safe_text('-5') == "'-5"
    assert ae._xlsx_safe_text('@x') == "'@x"
    assert ae._xlsx_safe_text('Alpha') == 'Alpha'
    assert ae._xlsx_safe_text('') == ''
    assert ae._excel_value('=1+1') == "'=1+1"
    assert ae._excel_value(7) == 7


def test_stdlib_writer_quotes_formula_cells():
    specs = ae._normalize_xlsx_sheets([{
        'title': 'Export', 'rows': _ROWS,
    }])
    for spec in specs:
        spec['number_style'] = spec.get('number_style') or ae.xlsx_number_style()
    xml = _sheet_xml(ae._as_xlsx_ooxml_book(specs))
    # The quote is XML-escaped by the writer: it is text, never a formula.
    assert '&#x27;=1+1' in xml
    assert '&#x27; @SUM(A1:A2)' in xml
    assert '&#x27;-5' in xml
    assert '<f>=1+1' not in xml and '<f>1+1' not in xml


def test_openpyxl_writer_quotes_formula_cells():
    import pytest
    pytest.importorskip('openpyxl')
    specs = ae._normalize_xlsx_sheets([{
        'title': 'Export', 'rows': _ROWS,
    }])
    raw = ae._as_xlsx_openpyxl_book(specs)
    from openpyxl import load_workbook
    ws = load_workbook(io.BytesIO(raw)).active
    values = [ws.cell(row=r, column=1).value for r in range(2, 6)]
    assert values == ["'=1+1", "' @SUM(A1:A2)", "'-5", 'Alpha']
    kinds = [ws.cell(row=r, column=1).data_type for r in range(2, 6)]
    assert 'f' not in kinds


def test_declared_formulas_stay_formulas():
    rows = [
        {'a': 1, 'b': 10, 'c': 11},
        {'a': 3, 'b': 20, 'c': 23},
        {'a': 4, 'b': 30, 'c': 34, '_tfoot': True},
    ]
    specs = ae._normalize_xlsx_sheets([{
        'title': 'Export', 'rows': rows, 'formulas': {'c': '={a}+{b}'},
    }])
    for spec in specs:
        spec['number_style'] = spec.get('number_style') or ae.xlsx_number_style()
    xml = _sheet_xml(ae._as_xlsx_ooxml_book(specs))
    assert '<f>SUM(A2:A3)</f>' in xml
