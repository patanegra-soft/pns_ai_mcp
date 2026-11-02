# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""What the model demands stops the plan; what the form demands is pending."""
from __future__ import annotations

from pathlib import Path

from _load_addon import load_module, safe_plan_source

required_fields = load_module('required_fields', 'utils', 'required_fields.py')

ROOT = Path(__file__).resolve().parents[1]
SAFE_PLAN = safe_plan_source()
PROMPT = (
    ROOT / 'common' / 'ai' / 'contexts' / 'core' / 'system_prompt.xml'
).read_text(encoding='utf-8')

FORM = """<form>
  <field name="name" modifiers='{"required": true}'/>
  <field name="source_id" modifiers='{"required": true}'/>
  <field name="team_id" modifiers='{"required": true}'/>
  <field name="sequence_code" modifiers='{"required": true, "readonly": true}'/>
  <field name="group_id" modifiers='{"required": true, "readonly": [["team_id", "!=", false]]}'/>
  <field name="type" modifiers='{"required": true, "invisible": true}'/>
  <field name="date_deadline" modifiers='{"required": [["type", "=", "lead"]]}'/>
  <field name="company_name" modifiers='{"required": true}'/>
  <field name="line_ids">
    <tree>
      <field name="product_id" modifiers='{"required": true}'/>
    </tree>
  </field>
</form>"""


class Field:
    def __init__(self, string, required=False, compute=None, inverse=None,
                 related=None, readonly=True):
        self.string = string
        self.required = required
        self.compute = compute
        self.inverse = inverse
        self.related = related
        self.readonly = readonly


class Record:
    def __init__(self, rid, values):
        self.id = rid
        self._values = values

    def __getitem__(self, name):
        return self._values[name]


class Model:
    #: What the screen of a Spanish user shows for these fields.
    TRANSLATED = {'partner_id': 'Cliente', 'name': 'Oportunidad'}

    def __init__(self, fields, defaults=None, arch=FORM):
        self._fields = fields
        self._defaults = defaults or {}
        self._arch = arch

    def default_get(self, names):
        return {n: self._defaults[n] for n in names if n in self._defaults}

    def fields_get(self, names):
        return {
            n: {'string': self.TRANSLATED.get(n, self._fields[n].string)}
            for n in names if n in self._fields
        }

    def fields_view_get(self, view_type='form'):
        return {'arch': self._arch}


class Env:
    def __init__(self, model):
        self._model = model

    def __contains__(self, name):
        return name == 'crm.lead'

    def __getitem__(self, name):
        return self._model


def _env(**overrides):
    fields = {
        'name': Field('Opportunity', required=True, compute='_compute_name'),
        'sequence_code': Field('Serial no.', required=True),
        'type': Field('Type', required=True),
        'source_id': Field('Origin'),
        'team_id': Field('Sales Team'),
        'partner_id': Field('Customer', required=True),
        'date_deadline': Field('Deadline'),
        'company_name': Field('Company', related='partner_id.name'),
        'line_ids': Field('Lines'),
    }
    fields.update(overrides.pop('fields', {}))
    defaults = {'sequence_code': '/', 'type': 'lead'}
    defaults.update(overrides.pop('defaults', {}))
    return Env(Model(fields, defaults, **overrides))


def _blocking(values, **overrides):
    return [
        name for name, _label in
        required_fields.missing_required_fields(_env(**overrides), 'crm.lead', values)
    ]


def _pending(values, rid=7, **overrides):
    found = required_fields.form_pending_by_record(
        _env(**overrides), 'crm.lead', [Record(rid, values)],
    )
    return [name for name, _label in found.get(rid, [])]


# ── What the model demands: it stops the plan ────────────────────────────

def test_a_field_the_model_needs_and_nobody_filled():
    assert _blocking({}) == ['partner_id']


def test_giving_it_is_enough():
    assert _blocking({'partner_id': 489}) == []


def test_an_empty_value_counts_as_absent():
    assert _blocking({'partner_id': False}) == ['partner_id']


def test_zero_is_a_value():
    assert _blocking({'partner_id': 0}) == []


def test_a_step_reference_counts_as_a_value():
    assert _blocking({'partner_id': '$0.id'}) == []


def test_what_odoo_fills_on_its_own_is_never_asked():
    # sequence_code and type carry a default, name is computed.
    assert _blocking({}) == ['partner_id']


def test_a_computed_field_with_an_inverse_is_still_asked():
    fields = {'name': Field('Opportunity', required=True,
                            compute='_compute_name', inverse='_inverse_name')}
    assert 'name' in _blocking({}, fields=fields)


def test_a_computed_field_the_user_writes_is_still_asked():
    """The subject of a lead: worked out only when it is left empty.

    Skipped as «computed», the record was born with no line saying what it
    was about, and nothing had asked for one.
    """
    fields = {'name': Field('Opportunity', required=True,
                            compute='_compute_name', readonly=False)}
    assert 'name' in _blocking({}, fields=fields)


def test_the_label_is_the_one_on_this_user_s_screen():
    """`_fields[...].string` is the English in the source, never translated."""
    found = required_fields.missing_required_fields(_env(), 'crm.lead', {})
    assert found == [('partner_id', 'Cliente')]


def test_the_form_alone_never_stops_a_create():
    # source_id and team_id are required in the form and nowhere else.
    assert 'source_id' not in _blocking({})
    assert 'team_id' not in _blocking({})


def test_a_field_the_screen_works_out_is_never_asked_for():
    """Read-only as soon as its neighbour is filled in: one question, once.

    The analytic group of a business area is written by the screen the
    moment the area is picked. Asked for as well, the same answer is owed
    twice and the second time nobody knows what it is being asked.
    """
    env = _env()
    assert 'group_id' not in required_fields._form_required(env, 'crm.lead')
    # The one the screen really does ask a person for is still there.
    assert 'source_id' in required_fields._form_required(env, 'crm.lead')
    assert required_fields.form_pending_by_record(
        env, 'crm.lead', [Record(1, {'group_id': False, 'source_id': False})],
    ) == {1: [('source_id', 'Origin')]}


def test_an_unknown_model_asks_for_nothing():
    env = _env()
    assert required_fields.missing_required_fields(env, 'res.partner', {}) == []
    assert required_fields.form_pending_by_record(env, 'res.partner', []) == {}


# ── What the form demands: the record is waiting for it ──────────────────

def test_the_record_says_what_the_form_still_wants():
    assert _pending({
        'name': 'AVERIA', 'source_id': False, 'team_id': False,
        'sequence_code': 'Aviso/2026/1355', 'type': 'notice',
        'date_deadline': False, 'company_name': False,
    }) == ['source_id', 'team_id']


def test_a_field_the_instance_filled_by_itself_is_not_pending():
    assert _pending({
        'name': 'AVERIA', 'source_id': 3, 'team_id': 1,
        'sequence_code': 'Aviso/2026/1355', 'type': 'notice',
        'date_deadline': False, 'company_name': False,
    }) == []


def test_a_hidden_or_locked_form_field_is_asked_of_nobody():
    empty = {name: False for name in ('name', 'source_id', 'team_id',
                                      'sequence_code', 'type', 'date_deadline',
                                      'company_name')}
    found = _pending(empty)
    assert 'sequence_code' not in found and 'type' not in found


def test_a_required_that_depends_on_other_values_does_not_hold():
    assert 'date_deadline' not in _pending({'source_id': False, 'team_id': False,
                                            'name': False, 'sequence_code': '/',
                                            'type': 'lead', 'date_deadline': False,
                                            'company_name': False})


def test_a_related_field_is_nobody_s_to_fill():
    assert 'company_name' not in _pending({'source_id': 1, 'team_id': 1,
                                           'name': False, 'sequence_code': '/',
                                           'type': 'lead', 'date_deadline': False,
                                           'company_name': False})


def test_a_field_of_a_nested_list_belongs_to_another_model():
    assert 'product_id' not in _pending({'source_id': False, 'team_id': False,
                                         'name': False, 'sequence_code': '/',
                                         'type': 'lead', 'date_deadline': False,
                                         'company_name': False})


def test_a_broken_form_leaves_nothing_pending():
    assert _pending({'source_id': False}, arch='<form>not xml') == []


def test_the_label_travels_with_the_field():
    env = _env()
    found = env and required_fields.form_pending_by_record(
        env, 'crm.lead', [Record(7, {
            'name': 'AVERIA', 'source_id': False, 'team_id': False,
            'sequence_code': '/', 'type': 'lead', 'date_deadline': False,
            'company_name': False,
        })],
    )
    assert found[7] == [('source_id', 'Origin'), ('team_id', 'Sales Team')]


# ── Wiring ───────────────────────────────────────────────────────────────

def test_only_the_model_stops_the_plan():
    assert 'from ..utils.required_fields import missing_required_fields' in SAFE_PLAN
    assert 'cannot be created without ' in SAFE_PLAN
    assert 'offer candidate rows ' in SAFE_PLAN


def test_the_record_is_read_after_the_write():
    assert 'from ..utils.required_fields import form_pending_by_record' in SAFE_PLAN
    assert "pending = _form_pending(env, model, rec)" in SAFE_PLAN
    assert "pending_before = _form_pending(env, model, recs)" in SAFE_PLAN


def test_a_write_that_changes_nothing_says_nothing():
    assert 'if before is not None and (before.get(record.id) or []) == empty:' in SAFE_PLAN


def test_the_card_carries_what_is_left():
    assert "def still_to_fill(item):" in SAFE_PLAN
    assert "_('Still to fill in: %s')" in SAFE_PLAN
    assert "'Written through the assistant. Still to fill in: %s'" in SAFE_PLAN
    assert 'record.message_post(body=' in SAFE_PLAN


def test_the_prompt_tells_the_two_apart():
    assert 'A field the MODEL requires' in PROMPT
    assert 'What only the FORM requires does NOT stop anything' in PROMPT
    assert 'ASKING FOR A FIELD THAT POINTS AT A RECORD' in PROMPT
    import re
    # The prompt carries a version; which one is not pinned here.
    assert re.search(r'<version>\d+\.\d+</version>', PROMPT)


def test_the_core_never_says_how_the_user_picks_a_row():
    """How a row is chosen is the host's; the core only delivers the rows."""
    block = PROMPT.split('<create_values>')[1].split('</create_values>')[0]
    for surface in ('tap', 'out loud', 'spell', 'type it', 'say the'):
        assert surface not in block.lower()
