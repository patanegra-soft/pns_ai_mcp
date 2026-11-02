# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""A step that rebuilds rows from a literal still knows whose ids those are."""
from __future__ import annotations

from pathlib import Path

from _load_addon import engine_source, load_module, relaxaicode_source

memory = load_module('turn_record_models', 'utils', 'turn_record_models.py')

ROOT = Path(__file__).resolve().parents[1]
ENGINE = engine_source()
TOOL = relaxaicode_source()


def test_an_id_read_from_the_orm_keeps_its_model():
    seen = {}
    memory.remember_record(seen, 'res.partner', 2889)
    assert memory.known_models(seen) == {2889: 'res.partner'}


def test_the_same_id_under_two_models_links_to_neither():
    seen = {}
    memory.remember_record(seen, 'res.partner', 26)
    memory.remember_record(seen, 'crm.team', 26)
    assert memory.known_models(seen) == {}


def test_junk_never_enters_the_memory():
    seen = {}
    memory.remember_record(seen, 'res.partner', 'x')
    memory.remember_record(seen, '', 7)
    memory.remember_record(seen, 'res.partner', 0)
    assert memory.known_models(seen) == {}


def test_rows_that_already_reached_a_screen_teach_their_model():
    seen = {}
    memory.remember_rows(seen, [
        {'id': 836, 'name': 'NEUMATICOS ACME, SL', '__model': 'res.partner'},
        {'id': 2673, 'name': 'MUEBLES EJEMPLO SUR, SA'},
        'not a row',
    ])
    assert memory.known_models(seen) == {836: 'res.partner'}


def test_the_engine_learns_from_the_dataset_the_client_sends_back():
    assert 'remember_rows(turn.turn_record_models, prior_query_data)' in ENGINE


def test_the_engine_learns_from_the_rows_it_reads_this_turn():
    """The step that rebuilds them by hand is the one that loses the model."""
    assert 'def _learn_row_models(self, turn, rows):' in ENGINE
    learn = ENGINE.split('def _learn_row_models(self, turn, rows):')[1].split(
        'def _collect_records_steps',
    )[0]
    assert 'remember_rows(turn.turn_record_models, rows)' in learn
    # Every dataset the turn collects, before any size limit on the cache.
    assert ENGINE.count('_learn_row_models(') >= 4
    rows_block = ENGINE.split('if isinstance(_rows, list) and _rows:')[1][:800]
    assert rows_block.index('_learn_row_models(turn, _rows)') < rows_block.index(
        '_dataset_cache_max_bytes',
    )


def test_the_engine_hands_the_memory_to_the_tool_call():
    assert 'self.turn_record_models = {}' in ENGINE
    assert 'remember_record(turn.turn_record_models' in ENGINE
    assert '_ctl.turn_record_models = known_models(' in ENGINE
    assert 'tool_func(_ctl, tool_args)' in ENGINE


def test_the_tool_stamps_with_what_the_turn_remembered():
    assert "getattr(controller, 'turn_record_models', None)" in TOOL
    assert 'turn_models=_turn_memory_models(controller)' in TOOL
    assert '_TURN_MEMORY_MIN_FIT' in TOOL
