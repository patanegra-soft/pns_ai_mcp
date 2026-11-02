# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Pointing at a row is naming a record; the engine has to hear it."""
from __future__ import annotations

from _load_addon import load_module

marks = load_module('pns_ai_mcp_record_marks', 'utils', 'record_marks.py')


def test_a_row_without_a_record_behind_it_is_not_a_mark():
    assert marks.clean_marks([
        {'model': 'res.partner', 'id': 2889, 'label': 'ACEROS'},
        {'model': 'res.partner'},
        {'id': 3365},
        {'model': 'res.partner', 'id': 0},
        {'model': '', 'id': 7},
        'not a row',
    ]) == [{'model': 'res.partner', 'id': 2889, 'label': 'ACEROS'}]


def test_the_same_row_twice_is_one_record():
    out = marks.clean_marks([
        {'model': 'res.partner', 'id': 5, 'label': 'A'},
        {'model': 'res.partner', 'id': 5, 'label': 'A'},
    ])
    assert len(out) == 1


def test_an_id_that_came_as_text_still_names_the_record():
    assert marks.clean_marks(
        [{'model': 'crm.lead', 'id': '3704'}],
    ) == [{'model': 'crm.lead', 'id': 3704, 'label': ''}]


def test_the_sentence_carries_model_and_id_so_nobody_searches_the_name():
    said = marks.marks_sentence([
        {'model': 'res.partner', 'id': 2889, 'label': 'ACEROS SUR'},
        {'model': 'res.partner', 'id': 3365, 'label': ''},
    ])
    assert 'res.partner#2889 (ACEROS SUR)' in said
    assert 'res.partner#3365' in said
    assert 'do not search the name again' in said


def test_nothing_marked_says_nothing():
    assert marks.marks_sentence([]) == ''
    assert marks.marks_sentence(None) == ''


def test_the_next_turn_reuses_the_rows_that_were_pointed_at():
    rows = [
        {'id': 2889, 'name': 'ACEROS', '__model': 'res.partner'},
        {'id': 3365, 'name': 'VIDRIOS', '__model': 'res.partner'},
    ]
    picked = marks.narrow_rows(
        [{'model': 'res.partner', 'id': 3365, 'label': 'VIDRIOS'}], rows,
    )
    assert picked == [rows[1]]


def test_a_mark_the_dataset_forgot_leaves_the_dataset_alone():
    rows = [{'id': 1, '__model': 'res.partner'}]
    assert marks.narrow_rows(
        [{'model': 'crm.lead', 'id': 99, 'label': ''}], rows,
    ) == rows


def test_what_was_just_written_is_what_change_it_means():
    said = marks.last_write_sentence(
        {'model': 'crm.lead', 'id': 3704, 'label': 'AV/2026/0042'},
    )
    assert 'crm.lead#3704 (AV/2026/0042)' in said
    # A hint, not an order: the next sentence may well name another one.
    assert 'If it names or describes another record' in said


def test_nothing_written_yet_says_nothing():
    assert marks.last_write_sentence(None) == ''
    assert marks.last_write_sentence({}) == ''
    assert marks.last_write_sentence({'model': 'crm.lead'}) == ''
    assert marks.last_write_sentence({'model': 'crm.lead', 'id': 0}) == ''


def test_the_labels_are_what_a_transcriber_can_lean_on():
    assert marks.marked_labels([
        {'model': 'res.partner', 'id': 1, 'label': 'ACEROS'},
        {'model': 'res.partner', 'id': 2, 'label': ''},
    ]) == ['ACEROS']
