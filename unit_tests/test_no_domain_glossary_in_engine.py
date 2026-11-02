# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Anchors: the engine must not reintroduce business glossaries."""
from __future__ import annotations

from _load_addon import addon_file
from _tenant_needles import names_tenant


def test_context_utils_has_no_rank_rule_placeholders():
    src = addon_file('utils', 'context_utils.py').read_text(encoding='utf-8')
    assert '{customer_rank_rule}' not in src
    assert '{supplier_rank_rule}' not in src


def test_report_outline_guard_has_no_finance_stub():
    src = addon_file('utils', 'report_outline_guard.py').read_text(encoding='utf-8')
    assert 'pólizas' not in src
    assert 'cobros' not in src
    assert 'liquidez' not in src
    assert "'recomendaciones'" not in src
    assert "'recommendations'" not in src
    assert "'acciones prioritarias'" not in src


def test_mcp_utils_has_no_entity_glossary():
    src = addon_file('lib', 'llm', 'utils', 'mcp_utils.py').read_text(
        encoding='utf-8',
    )
    for token in ("'cliente'", "'factura'", "'producto'", "'empleado'"):
        assert token not in src


def test_engine_does_not_ship_geo_context():
    """Maps pack lives in pns_geo, not in the engine tree."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / 'common'
    assert not (root / 'ai' / 'contexts' / 'domain' / 'geo' / 'geo.xml').is_file()
    discovery = root / 'ai' / 'contexts' / 'discovery'
    assert not (discovery / 'discovery_geo.json').is_file()
    assert not (discovery / 'discovery_geo_es_ES.json').is_file()


def test_module_does_not_ship_tenant_pilot_seeds():
    """A customer's skills and contexts live in its instance or pack, not here."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / 'common' / 'ai'
    assert not (root / 'contexts' / 'domain' / 'domain_knowledge_crm.xml').is_file()
    named = [
        p.relative_to(root).as_posix()
        for p in root.rglob('*')
        if names_tenant(p.relative_to(root).as_posix())
    ]
    assert named == []