# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""PAAP I7 (cusp protection): reading many2many commands and user group fields."""
from __future__ import annotations

from _load_addon import addon_file, load_module, safe_plan_source

cusp = load_module('privilege_cusp', 'utils', 'privilege_cusp.py')


class _Field:
    def __init__(self, comodel=None):
        self.comodel_name = comodel


def test_command_codes_are_not_ids():
    assert cusp.ids_in([(4, 7)]) == {7}
    assert cusp.ids_in([[4, 7], [3, 9]]) == {7, 9}
    assert cusp.ids_in([(6, 0, [2, 3])]) == {2, 3}
    assert cusp.ids_in([(0, 0, {'name': 'x'})]) == set()
    assert cusp.ids_in([(5,)]) == set()
    assert cusp.ids_in([5, 8]) == {5, 8}
    assert cusp.ids_in(12) == {12}
    assert cusp.ids_in(True) == set()


def test_user_group_fields_are_found_by_comodel_and_odoo_form_names():
    fields = {
        'name': _Field(),
        'groups_id': _Field('res.groups'),
        'company_ids': _Field('res.company'),
    }
    assert cusp.writes_user_groups(fields, {'name': 'A'}) == []
    assert cusp.writes_user_groups(fields, {'groups_id': [(4, 1)]}) == ['groups_id']
    assert cusp.writes_user_groups(fields, {'in_group_3': True}) == ['in_group_3']
    assert cusp.writes_user_groups(fields, {'sel_groups_1_2': 2}) == ['sel_groups_1_2']
    assert cusp.writes_user_groups(fields, {'company_ids': [(4, 1)]}) == []


def test_cusp_is_checked_when_proposing_and_when_executing():
    plan = safe_plan_source()
    validate = plan[plan.index('def validate_safe_plan'):plan.index('def compute_danger_level')]
    execute = plan[plan.index('def execute_safe_plan'):plan.index('def _journal_snapshot')]
    assert 'crud_cusp_error' in validate
    assert execute.count('crud_cusp_error(') == 4
    action = addon_file('models', 'ai_system_action.py').read_text(encoding='utf-8')
    assert action.count('self._resolve_group_below_cusp(group)') == 4
