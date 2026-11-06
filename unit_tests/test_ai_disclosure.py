# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Exported files say, to a machine, that an AI system made them."""
from __future__ import annotations

import io
import sys

import pytest

from _load_addon import load_module

openpyxl = pytest.importorskip('openpyxl')
pytest.importorskip('reportlab')

ai = load_module('ai_disclosure', 'utils', 'ai_disclosure.py')
fmt = load_module('formatters', 'controllers', 'formatters.py')
ae = load_module('artifact_export', 'utils', 'artifact_export.py')
table = load_module('artifact_export_table', 'utils', 'artifact_export_table.py')

_ROWS = [{'Name': 'ACME', 'Total': 10}, {'Name': 'Ejemplo', 'Total': 20}]


def _assert_marked(raw):
    props = openpyxl.load_workbook(io.BytesIO(raw)).properties
    assert props.creator == ai.AI_GENERATOR
    assert props.keywords == ai.AI_KEYWORD


def _specs():
    specs = ae._normalize_xlsx_sheets([{'title': 'Sales', 'rows': _ROWS}])
    for spec in specs:
        spec['number_style'] = ae.xlsx_number_style()
    return specs


def test_engine_workbook_is_marked():
    _assert_marked(fmt.format_data_as_excel(_ROWS, table.columns_config(_ROWS), title='Sales'))


def test_export_workbook_is_marked(monkeypatch):
    for name, mod in list(sys.modules.items()):
        if name.startswith(ae.__name__) and hasattr(mod, '_load_formatters'):
            monkeypatch.setattr(mod, '_load_formatters', lambda: fmt)
    _assert_marked(ae._as_xlsx_openpyxl_book(_specs()))


def test_workbook_written_without_openpyxl_is_marked():
    _assert_marked(ae._as_xlsx_ooxml_book(_specs()))


def test_engine_pdf_is_marked():
    raw = fmt.format_data_as_pdf(_ROWS, table.columns_config(_ROWS), title='Sales')
    assert ai.AI_GENERATOR.encode() in raw
    assert ai.AI_KEYWORD.encode() in raw


@pytest.mark.parametrize('kind', ['html', 'doc'])
def test_html_and_word_name_their_generator(kind):
    raw = ae.serialize_rows(_ROWS, kind, title='Sales').decode('utf-8')
    head = raw.split('</head>', 1)[0]
    assert ai.HTML_META in head
