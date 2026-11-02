# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Fossil DROP list is named and does not touch live Safe Plan tables."""
from __future__ import annotations

from _load_addon import load_module

fossils = load_module('schema_fossils', 'utils', 'schema_fossils.py')


def test_fossils_include_pns_bundle_rels_and_recipe():
    names = set(fossils.FOSSIL_TABLES)
    assert 'ai_skill_pns_ai_mcp_artifact_bundle_export_wizard_rel' in names
    assert 'ai_relaxaicode_recipe' in names
    assert 'pns_ai_mcp_skill_capture_wizard' in names


def test_turn_column_promote_is_named():
    assert fossils.promote_turn_columns.__name__ == 'promote_turn_columns'
    from pathlib import Path
    src = fossils.__file__
    assert src
    model = Path(src).resolve().parents[1] / 'models' / 'ai_schema_fossil.py'
    text = model.read_text(encoding='utf-8')
    assert 'promote_turn_columns(cr)' in text
    assert 'drop_leftover_columns(cr)' in text


def test_drop_leftover_columns_is_named():
    assert fossils.drop_leftover_columns.__name__ == 'drop_leftover_columns'
    cols = set(fossils.LEFTOVER_COLUMNS)
    assert ('ai_log', 'operation_code') in cols
    # History stays: the agent code on old rows is not dropped on -u (PNS-87).
    assert ('ai_log', 'agent_id') not in cols
    assert ('ai_agent', 'auto_link_mcp_nucleus') in cols
    assert ('ai_context', 'is_shared') in cols
    assert ('ai_skill', 'is_shared') in cols
    assert ('ai_provider', 'cost_policy') in cols
    assert ('ai_provider', 'is_on_premise') in cols


def test_compose_column_promote_is_named():
    assert fossils.promote_compose_column.__name__ == 'promote_compose_column'
    assert ('painter-local', 'compose-agent') in fossils.COMPOSE_VALUE_REMAP
    assert ('compose-chatboo', 'compose-agent') in fossils.COMPOSE_VALUE_REMAP
    assert ('painter-free', 'compose-model') in fossils.COMPOSE_VALUE_REMAP
    assert 'ai_provider' in fossils.COMPOSE_VALUE_TABLES
    assert 'ai_skill' in fossils.COMPOSE_VALUE_TABLES


class _ParamCursor:
    """``ir_config_parameter`` + ``ir_model_data`` for promote_engine_params."""

    def __init__(self, params, xmlids):
        self.params = dict(params)  # id -> key
        self.xmlids = set(xmlids)  # res_id of ir.config_parameter
        self._row = None

    def execute(self, sql, args=()):
        self._row = None
        if sql.startswith('SELECT id FROM ir_config_parameter'):
            ids = [i for i, k in self.params.items() if k == args[0]]
            self._row = (ids[0],) if ids else None
        elif sql.startswith('SELECT 1 FROM ir_config_parameter'):
            self._row = (1,) if args[0] in self.params.values() else None
        elif sql.startswith('DELETE FROM ir_model_data'):
            self.xmlids.discard(args[0])
        elif sql.startswith('DELETE FROM ir_config_parameter'):
            self.params.pop(args[0])
        elif sql.startswith('UPDATE ir_config_parameter'):
            self.params[args[1]] = args[0]
        else:
            raise AssertionError(sql)

    def fetchone(self):
        return self._row


def test_engine_params_move_to_engine_keys():
    cr = _ParamCursor(
        {
            1: 'pns_ai_chatboo.chart_engine',
            2: 'pns_ai_chatboo.default_show_mode',
            3: 'pns_ai_chatboo.default_showmode',
            4: 'pns_ai.xlsx_thousands',
            5: 'pns_ai_chatboo.xlsx_thousands',
            6: 'pns_ai_chatboo.show_systray',
        },
        {1, 2, 3, 5, 6},
    )
    fossils.promote_engine_params(cr)
    assert cr.params == {
        1: 'pns_ai.chart_engine',
        2: 'pns_ai.default_show_mode',
        4: 'pns_ai.xlsx_thousands',
        6: 'pns_ai_chatboo.show_systray',
    }
    assert cr.xmlids == {6}
    fossils.promote_engine_params(cr)
    assert len(cr.params) == 4


def test_previous_keys_all_land_on_engine_names():
    for old_key, new_key in fossils.PREVIOUS_KEYS:
        assert old_key.startswith('pns_ai_chatboo.')
        assert new_key.startswith('pns_ai.')


class _XmlidCursor:
    def __init__(self, names):
        self.names = set(names)
        self._row = None

    def execute(self, sql, args=()):
        self._row = None
        if sql.startswith('SELECT id FROM ir_model_data'):
            self._row = (1,) if args[0] in self.names else None
        elif sql.startswith('UPDATE ir_model_data'):
            new, old = args
            if old in self.names:
                self.names.discard(old)
                self.names.add(new)
        else:
            raise AssertionError(sql)

    def fetchone(self):
        return self._row


def test_xmlid_renames_keep_the_row():
    cr = _XmlidCursor({'mcp_log_user_rule', 'menu_mcp_logs', 'menu_ai_context'})
    fossils.rename_leftover_xmlids(cr)
    assert 'ai_log_user_rule' in cr.names
    assert 'menu_ai_log' in cr.names
    assert 'mcp_log_user_rule' not in cr.names
    # A name already renamed is left alone on the next -u.
    fossils.rename_leftover_xmlids(cr)
    assert 'ai_log_user_rule' in cr.names
    model = fossils.__file__
    from pathlib import Path
    text = (Path(model).resolve().parents[1] / 'models' / 'ai_schema_fossil.py').read_text(encoding='utf-8')
    assert 'rename_leftover_xmlids(cr)' in text


def test_fossils_never_include_live_safe_tables():
    names = set(fossils.FOSSIL_TABLES)
    for protected in fossils.PROTECTED_TABLES:
        assert protected not in names
    assert 'ai_safe_choice' in fossils.PROTECTED_TABLES
    assert 'ai_change_journal' in fossils.PROTECTED_TABLES
