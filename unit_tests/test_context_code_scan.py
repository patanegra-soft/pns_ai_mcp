# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Factory context codes: scan dirs, owner-wins vs takeover."""
from __future__ import annotations

from _load_addon import load_module

scan = load_module('context_code_scan', 'utils', 'context_code_scan.py')


def test_codes_in_contexts_dir_reads_code_tag(tmp_path):
    folder = tmp_path / 'ai' / 'contexts' / 'domain'
    folder.mkdir(parents=True)
    (folder / 'geo.xml').write_text(
        '<context><metadata><code>geo</code></metadata></context>\n',
        encoding='utf-8',
    )
    (folder / 'notes.md').write_text('# skip\n', encoding='utf-8')
    assert scan.codes_in_contexts_dir(str(folder)) == {'geo', 'notes'}


def test_factory_row_blocks_when_owner_still_ships():
    assert scan.factory_row_blocks_incoming('pns_ai_mcp', 'pns_geo', True)
    assert not scan.factory_row_blocks_incoming('pns_ai_mcp', 'pns_geo', False)
    assert not scan.factory_row_blocks_incoming('pns_geo', 'pns_geo', True)
    assert not scan.factory_row_blocks_incoming('', 'pns_geo', True)


def test_engine_tree_has_no_geo_code():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / 'common' / 'ai' / 'contexts'
    assert 'geo' not in scan.codes_in_contexts_dir(str(root))
