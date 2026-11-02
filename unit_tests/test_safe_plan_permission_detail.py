# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Authorising a write means seeing what is going in, not just how many rows."""
from _load_addon import safe_plan_source


def _src():
    return safe_plan_source()


def _chunk(src, start, end):
    return src.split(start)[1].split(end)[0]


def test_the_card_spells_out_each_step_under_the_count():
    src = _src()
    headline = _chunk(src, 'def describe_safe_plan', '\ndef ')
    assert '_crud_step_details(env, op, model, group)' in headline
    detail = _chunk(src, 'def _crud_step_details', 'def describe_safe_plan')
    # Create and copy show the values; write and unlink show what they hit.
    assert '_value_lines(env, model, values)' in detail
    assert '_step_targets(env, model, step)' in detail


def test_a_long_field_does_not_push_the_next_one_off_the_card():
    """Strung together, the date fell off the end of a customer's address."""
    lines = _chunk(_src(), 'def _value_lines', 'def _step_targets')
    assert "lines.append('%s: %s' % (label, shown))" in lines
    assert '_VALUE_CHARS_MAX' in lines  # cut each value, never the last field
    assert '_VALUE_FIELDS_MAX' in lines
    detail = _chunk(_src(), 'def _crud_step_details', 'def describe_safe_plan')
    assert "out.append('   · ' + line)" in detail


def test_a_date_is_written_the_way_the_reader_writes_dates():
    value = _chunk(_src(), 'def _describe_value(', 'def _value_lines')
    assert "if ftype in ('date', 'datetime')" in value
    written = _chunk(_src(), 'def _written_date', 'def _describe_value(')
    assert 'format_date(env, value)' in written
    assert 'format_datetime(env, value)' in written


def test_many_steps_keep_the_headline_alone():
    """Three lines help a person decide; forty hide the traffic light."""
    detail = _chunk(_src(), 'def _crud_step_details', 'def describe_safe_plan')
    assert 'if len(group) > _DETAIL_GROUP_MAX' in detail
    assert 'return []' in detail


def test_a_related_value_is_named_and_placed():
    value = _chunk(_src(), 'def _describe_value(', 'def _value_lines')
    assert 'placed_label(env, comodel, value)' in value
    # The name stays as the fallback: a model with no address still reads.
    assert '_names_for(env, comodel, [value])' in value


def test_the_records_a_delete_would_take_are_named():
    targets = _chunk(_src(), 'def _step_targets', 'def _crud_step_details')
    assert '_names_for(env, model, ids)' in targets
    assert '_DETAIL_IDS_MAX' in targets
