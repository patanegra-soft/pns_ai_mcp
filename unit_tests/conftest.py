# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Pytest: put unit_tests/ on the path for _load_addon."""
import importlib.util
import sys
import types
from pathlib import Path

import pytest

_UNIT = Path(__file__).resolve().parent
if str(_UNIT) not in sys.path:
    sys.path.insert(0, str(_UNIT))

# pns_base is its own repo, next to this one.
_PDF_IO = _UNIT.parents[1] / 'pns_base' / 'stacks' / 'owl2' / 'pns_base' / 'utils' / 'pdf_io.py'
_PDF_IO_NAME = 'odoo.addons.pns_base.utils.pdf_io'


@pytest.fixture
def pns_base_pdf_io(monkeypatch):
    """pns_base's pure ``pdf_io`` under the name Odoo gives it, for this test only."""
    if not _PDF_IO.exists():
        pytest.skip('pns_base is not next to this repo')
    for name in ('odoo', 'odoo.addons', 'odoo.addons.pns_base', 'odoo.addons.pns_base.utils'):
        if name not in sys.modules:
            monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
    spec = importlib.util.spec_from_file_location(_PDF_IO_NAME, _PDF_IO)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setitem(sys.modules, _PDF_IO_NAME, module)
    return module
