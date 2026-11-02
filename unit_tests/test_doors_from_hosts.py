# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""The engine lists its own doors; each host adds its own with ``selection_add``."""
from _load_addon import addon_file, safe_plan_source


def _read(*parts):
    return addon_file(*parts).read_text(encoding='utf-8')


def _origin_selection(src):
    return src.split('origin = fields.Selection(', 1)[1].split('string=', 1)[0]


def test_engine_origin_lists_only_its_doors():
    log = _origin_selection(_read('models', 'ai_log.py'))
    assert "('mcp_client', 'MCP Client')" in log
    assert "('internal', 'Internal')" in log
    assert 'chatboo' not in log
    journal = _origin_selection(_read('models', 'ai_change_journal.py'))
    assert "('revert', 'Revert')" in journal
    assert 'chatboo' not in journal


def test_door_checks_read_the_field():
    logging_src = _read('utils', 'mcp_logging.py')
    doors = logging_src.split('def known_doors', 1)[1].split('\ndef ', 1)[0]
    assert "_fields['origin'].get_values(env)" in doors
    sources = (
        _read('models', 'ai_log.py'),
        _read('models', 'ai_change_journal.py'),
        _read('models', 'safe_operation.py'),
        safe_plan_source(),
    )
    for src in sources:
        assert 'known_doors(' in src
        assert "'chatboo', 'mcp_client', 'internal'" not in src
    operation = _read('models', 'safe_operation.py')
    origin = operation.split('def _resolve_log_origin', 1)[1].split('\n    def ', 1)[0]
    assert "startswith('skill:')" not in origin


def test_client_is_only_what_the_caller_said():
    logging_src = _read('utils', 'mcp_logging.py')
    client = logging_src.split('def resolve_client_label', 1)[1].split('\ndef ', 1)[0]
    assert 'agent' not in client
    assert 'CLIENT_' not in logging_src
    assert "if origin == 'mcp_client':" in client
    assert 'return None' in client


def test_log_views_do_not_name_a_host():
    for stack in ('owl1', 'owl2'):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        views = (root / 'stacks' / stack / 'pns_ai_mcp' / 'views' / 'ai_log_views.xml').read_text(
            encoding='utf-8',
        )
        assert 'chatboo' not in views
        assert "decoration-info=\"origin not in ('mcp_client', 'internal')\"" in views
