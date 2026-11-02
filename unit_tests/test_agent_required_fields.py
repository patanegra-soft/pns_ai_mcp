# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""What a model asks of the assistant, closed in code and not in a prompt."""
from _load_addon import load_module, safe_plan_source


def _mod():
    return load_module('required_fields', 'utils', 'required_fields.py')


class _Field(object):
    def __init__(self, ftype, string):
        self.type = ftype
        self.string = string
        self.required = False
        self.compute = None
        self.related = None
        self.inverse = None


class _Model(object):
    """A model of this instance: it owns the condition, the engine does not."""

    _fields = {
        'sub_type': _Field('selection', 'Sub Type'),
        'partner_id': _Field('many2one', 'Customer'),
        'date_deadline': _Field('date', 'Expected Closing'),
        'name': _Field('char', 'Name'),
    }

    @staticmethod
    def ai_required_fields(values):
        owed = ['sub_type']
        if values.get('sub_type') == 'notice':
            owed += ['partner_id', 'date_deadline']
        return owed


class _Plain(object):
    """One that says nothing: nothing is asked of it."""

    _fields = {'name': _Field('char', 'Name')}


class _Env(dict):
    def __init__(self, model):
        super(_Env, self).__init__()
        self._model = model

    def __contains__(self, name):
        return True

    def __getitem__(self, name):
        return self._model


def test_a_model_that_says_nothing_is_asked_for_nothing():
    assert _mod().missing_for_agent(_Env(_Plain()), 'whatever', {}) == []


def test_what_the_model_asks_for_travels_with_its_label_and_its_type():
    owed = _mod().missing_for_agent(
        _Env(_Model()), 'crm.lead', {'sub_type': 'notice', 'name': 'Avería'},
    )
    assert ('partner_id', 'Customer', 'many2one') in owed
    assert ('date_deadline', 'Expected Closing', 'date') in owed


def test_what_the_plan_already_carries_is_not_asked_again():
    owed = _mod().missing_for_agent(_Env(_Model()), 'crm.lead', {
        'sub_type': 'notice', 'partner_id': 5398, 'date_deadline': '2026-09-23',
    })
    assert owed == []


def test_the_condition_can_depend_on_what_the_plan_says():
    """Another kind of record, another list: the model decides, not the engine."""
    owed = _mod().missing_for_agent(
        _Env(_Model()), 'crm.lead', {'sub_type': 'opportunity'},
    )
    assert owed == []


def test_a_plan_that_owes_the_model_something_is_not_proposed():
    plan = safe_plan_source()
    check = plan.split('def _owed_to_the_model')[1].split('\ndef ')[0]
    assert 'missing_for_agent' in check
    # The engine names no model and no field of anyone's business.
    for literal in ('crm.lead', 'notice', 'date_deadline', 'partner_id'):
        assert literal not in check
    # A date is not dictated when the channel can show a picker.
    assert "ftype in ('date', 'datetime')" in check
    validate = plan.split('def validate_safe_plan')[1].split('\ndef ')[0]
    assert '_owed_to_the_model(env, step.get(' in validate
    assert 'return False, owed' in validate
