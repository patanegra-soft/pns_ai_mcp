# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Every stack reaches the same things from the same screen.

The widget may differ (a Tools button in Odoo 14, the cog menu in 17+), but
the wizard it opens, the list header buttons and the Action menu entries do
not. A stack that loses one fails here.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STACKS = ('owl1', 'owl2', 'owl3')
# The module name is the folder inside stacks/owl1, not the clone's folder:
# publish.sh runs these tests on a copy of the tree under another name.
MODULE = next(
    p.name for p in sorted((ROOT / 'stacks' / STACKS[0]).iterdir())
    if p.is_dir() and (p / '__manifest__.py').is_file()
)

# Odoo 14 lists have no Duplicate of their own; 17+ lists do.
_O14_ONLY_BOUND = {
    ('action_server_duplicate_ai_providers', 'model_ai_provider', 'list'),
}


def _base(stack):
    return ROOT / 'stacks' / stack / MODULE


def _js_actions(stack):
    found = set()
    for path in (_base(stack) / 'static' / 'src').rglob('*.js'):
        text = path.read_text(encoding='utf-8')
        found |= set(re.findall(
            r"""(?:do_action|doAction)\(\s*['"](%s\.[A-Za-z0-9_]+)['"]""" % MODULE, text))
    return found


def _records(stack, model):
    for path in sorted((_base(stack) / 'views').rglob('*.xml')):
        for rec in ET.parse(path).getroot().iter('record'):
            if rec.get('model') == model:
                yield rec


def _field(rec, name):
    return next((f for f in rec.findall('field') if f.get('name') == name), None)


def _list_header_buttons(stack):
    found = set()
    for rec in _records(stack, 'ir.ui.view'):
        arch, model = _field(rec, 'arch'), _field(rec, 'model')
        if arch is None or model is None:
            continue
        for tree in arch.findall('tree'):
            for header in tree.findall('header'):
                for button in header.iter('button'):
                    found.add((model.text, button.get('name')))
    return found


def _bound_actions(stack):
    found = set()
    for rec in _records(stack, 'ir.actions.server'):
        binding = _field(rec, 'binding_model_id')
        if binding is None or not binding.get('ref'):
            continue
        types = _field(rec, 'binding_view_types')
        found.add((rec.get('id'), binding.get('ref'),
                   types.text if types is not None else 'list,form'))
    return found


def test_every_stack_opens_the_same_wizards_from_its_screens():
    want = _js_actions('owl1')
    assert want
    for stack in STACKS[1:]:
        assert _js_actions(stack) == want, stack


def test_every_stack_has_the_same_list_header_buttons():
    want = _list_header_buttons('owl1')
    assert want
    for stack in STACKS[1:]:
        assert _list_header_buttons(stack) == want, stack


def test_every_stack_hangs_the_same_entries_on_the_action_menu():
    want = _bound_actions('owl1') - _O14_ONLY_BOUND
    assert want
    for stack in STACKS[1:]:
        assert _bound_actions(stack) == want, stack
