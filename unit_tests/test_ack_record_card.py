# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""The ack says what was written the way a person reads it — never an id."""
from _load_addon import load_module


def _mod():
    return load_module('ack_record_card', 'utils', 'ack_record_card.py')


class _Field(object):
    def __init__(self, ftype, string, store=True, selection=None):
        self.type = ftype
        self.string = string
        self.store = store
        self.selection = selection


class _Partner(object):
    """A contact that knows how to place itself, as Odoo's address format does."""

    _name = 'res.partner'
    id = 7629
    display_name = 'HOTEL ACME - HIJOS DE EJEMPLO SL'
    _placed = (
        'HOTEL ACME - HIJOS DE EJEMPLO SL\n'
        'CTRA. NACIONAL KM 100, \n'
        '99999 VILLAEJEMPLO (Jaén, Spain)'
    )

    def __init__(self, show_address=False):
        self._show_address = show_address

    def __bool__(self):
        return True

    def sudo(self):
        return self

    def browse(self, rid=None):
        return self

    def exists(self):
        return True

    def with_context(self, **kw):
        return _Partner(show_address=bool(kw.get('show_address')))

    def name_get(self):
        return [(self.id, self._placed if self._show_address else self.display_name)]


class _Team(object):
    """A model with no address: it answers with its name and nothing else."""

    _name = 'crm.team'
    id = 31
    display_name = 'Sales'

    def __bool__(self):
        return True

    def sudo(self):
        return self

    def browse(self, rid=None):
        return self

    def exists(self):
        return True

    def with_context(self, **kw):
        return self

    def name_get(self):
        return [(self.id, self.display_name)]


class _Lead(object):
    """A notice: a name, a customer, and a reference the instance assigned."""

    _description = 'Lead/Opportunity'
    _fields = {
        'name': _Field('char', 'Opportunity'),
        'sequence_code': _Field('char', 'Nº serie'),
        'email_from': _Field('char', 'Email'),
        'partner_id': _Field('many2one', 'Customer'),
        'team_id': _Field('many2one', 'Sales Team'),
        'date_deadline': _Field('date', 'Expected Closing'),
        'active': _Field('boolean', 'Active'),
    }
    _values = {
        'name': 'AVERIA MANDO PUENTE GRUA',
        'sequence_code': 'Aviso/2026/1354',
        'email_from': False,
        'partner_id': _Partner(),
        'team_id': _Team(),
        'date_deadline': '2026-09-23',
        'active': True,
    }
    display_name = 'AVERIA MANDO PUENTE GRUA'

    def browse(self, rid=None):
        return self

    def exists(self):
        return True

    def default_get(self, names):
        # The Odoo idiom for a reference: a placeholder the create replaces.
        return {'sequence_code': '/'} if 'sequence_code' in names else {}

    def fields_get(self, names, _attrs=None):
        return {
            name: {
                'string': self._fields[name].string,
                'type': self._fields[name].type,
                'selection': self._fields[name].selection,
            }
            for name in names if name in self._fields
        }

    def __getitem__(self, name):
        return self._values[name]


class _Env(object):
    def __init__(self):
        self._models = {
            'crm.lead': _Lead(),
            'res.partner': _Partner(),
            'crm.team': _Team(),
        }

    def __contains__(self, name):
        return name in self._models

    def __getitem__(self, name):
        return self._models[name]


def test_the_card_leads_with_the_reference_the_instance_assigned():
    card = _mod().record_card(
        _Env(), 'crm.lead', 3704,
        values={'name': 'x', 'partner_id': 7629, 'date_deadline': '2026-09-23'},
    )
    assert card
    assert card[0] == '- **AVERIA MANDO PUENTE GRUA** (Lead/Opportunity)'
    assert card[1] == '  - Nº serie: Aviso/2026/1354'
    assert (
        '  - Customer: HOTEL ACME - HIJOS DE EJEMPLO SL — '
        'CTRA. NACIONAL KM 100, 99999 VILLAEJEMPLO (Jaén, Spain)'
    ) in card
    # An id is not a reference: nobody sees one in Odoo.
    assert not any('3704' in line for line in card)
    # The header already said the name; the row would only repeat it.
    assert not any(line.startswith('  - Opportunity:') for line in card)


def test_a_related_record_with_no_address_is_just_its_name():
    """Where it is only shows up when the model has somewhere to be."""
    card = _mod().record_card(_Env(), 'crm.lead', 3704, values={'team_id': 31})
    assert '  - Sales Team: Sales' in card


def test_a_field_nobody_wrote_stays_out():
    """Only what was asked for, plus what the instance decided."""
    card = _mod().record_card(_Env(), 'crm.lead', 3704, values={'name': 'x'})
    assert not any('Email' in line for line in card)
    assert not any('Expected Closing' in line for line in card)
    assert card[1] == '  - Nº serie: Aviso/2026/1354'


def test_the_caller_wording_wraps_the_header():
    card = _mod().record_card(
        _Env(), 'crm.lead', 3704, values={},
        title_of=lambda head: 'Creado: %s' % head,
    )
    assert card[0].startswith('- Creado: **AVERIA MANDO PUENTE GRUA**')


def test_an_unknown_model_is_no_card_and_no_crash():
    mod = _mod()
    assert mod.record_card(_Env(), 'no.such.model', 1) is None
    assert mod.record_card(None, 'crm.lead', 1) is None
    assert mod.record_card(_Env(), 'crm.lead', 0) is None
