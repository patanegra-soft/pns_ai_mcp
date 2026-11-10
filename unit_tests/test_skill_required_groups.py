# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Who may use a skill or a context: owner, member of a shared group, or an open row.

One rule (``knowledge_ownership``) in three places that must agree: the
record rule, the ORM domain and the Python filter. The check runs where
skills are listed (list_for_agent), where a slash or an NL trigger resolves
(engine) and where contexts enter a prompt (agent cache vs per-user part).
"""
import importlib
import sys
import types
from pathlib import Path

from _load_addon import addon_file, skill_source, context_source

_ROOT = Path(__file__).resolve().parents[1]
_SKILL = skill_source()
_CONTEXT = context_source()
_AGENT = addon_file('models', 'ai_agent.py').read_text(encoding='utf-8')
_ENGINE = (_ROOT / 'common' / 'utils' / 'engine_skills.py').read_text(encoding='utf-8')
_RULES = (_ROOT / 'common' / 'security' / 'security.xml').read_text(encoding='utf-8')


def _ownership():
    """``knowledge_ownership`` inside a synthetic package with a stub ``compat``."""
    pkg_name = '_pns_ownership_utils'
    if pkg_name not in sys.modules:
        pkg = types.ModuleType(pkg_name)
        pkg.__path__ = [str(_ROOT / 'common' / 'utils')]
        sys.modules[pkg_name] = pkg
        compat = types.ModuleType(pkg_name + '.compat')
        compat.USER_ALL_GROUPS_FIELD = 'all_group_ids'
        sys.modules[pkg_name + '.compat'] = compat
    return importlib.import_module(pkg_name + '.knowledge_ownership')


class _Groups:
    def __init__(self, ids):
        self.ids = list(ids)

    def __bool__(self):
        return bool(self.ids)


class _User:
    def __init__(self, uid, group_ids):
        self.id = uid
        self._fields = {'all_group_ids': _Groups(group_ids)}

    def __getitem__(self, name):
        return self._fields[name]


class _Owner:
    def __init__(self, uid):
        self.id = uid

    def __bool__(self):
        return True


class _Row:
    _fields = {'owner_id': None, 'required_group_ids': None}

    def __init__(self, owner=None, groups=()):
        self.owner_id = _Owner(owner) if owner else False
        self.required_group_ids = _Groups(groups)

    def __getitem__(self, name):
        return getattr(self, name)


ANA, BOB = _User(1, [10, 11]), _User(2, [10, 20])


def test_owner_member_or_open_row():
    may = _ownership().user_may_use
    assert may(_Row(), ANA) and may(_Row(), BOB)                   # open
    assert may(_Row(owner=1), ANA) and not may(_Row(owner=1), BOB)  # only the owner
    assert may(_Row(owner=1, groups=[20]), ANA)                     # owner, not in the group
    assert may(_Row(owner=1, groups=[20]), BOB)                     # member
    assert not may(_Row(groups=[99]), ANA)                          # groups, no owner: members only
    assert may(_Row(groups=[11, 99]), ANA) and not may(_Row(groups=[11, 99]), BOB)


def test_the_domain_and_the_record_rule_say_the_same():
    domain = _ownership().ownership_read_domain(ANA)
    assert domain == [
        '|', '|',
        ('owner_id', '=', 1),
        ('shared_user_ids', 'in', [1]),
        '&', ('owner_id', '=', False), ('required_group_ids', '=', False),
    ]
    rule = (
        "['|', '|', ('owner_id', '=', user.id), ('shared_user_ids', 'in', [user.id]), "
        "'&amp;', ('owner_id', '=', False), ('required_group_ids', '=', False)]"
    )
    assert _RULES.count(rule) == 4  # contexts and skills, user and writer
    assert "('skill_id.shared_user_ids', 'in', [user.id])" in _RULES


def test_shared_user_ids_search_turns_the_user_into_their_groups():
    own = _ownership()

    class _Users:
        def __init__(self, found):
            self.found = found

        def sudo(self):
            return self

        def browse(self, ids):
            # psycopg adapts a list of ints; a set (Odoo 19 OrderedSet) crashes.
            assert isinstance(ids, list) and all(isinstance(i, int) for i in ids), ids
            return self

        def exists(self):
            return self.found

        def __iter__(self):
            return iter(self.found)

    class _Model:
        def __init__(self, found):
            self.env = {'res.users': _Users(found)}

    assert own.search_shared_user_ids(_Model([ANA]), 'in', [1]) == [('required_group_ids', 'in', [10, 11])]
    # Odoo 19 hands the value as a set; a bare id arrives with '='.
    assert own.search_shared_user_ids(_Model([ANA]), 'in', {1}) == [('required_group_ids', 'in', [10, 11])]
    assert own.search_shared_user_ids(_Model([ANA]), '=', 1) == [('required_group_ids', 'in', [10, 11])]
    assert own.search_shared_user_ids(_Model([]), 'in', [7]) == [('id', '=', False)]
    assert own.search_shared_user_ids(_Model([ANA]), '!=', [1]) == [('id', '=', False)]


def test_both_models_carry_the_groups_and_the_searchable_users():
    for source in (_SKILL, _CONTEXT):
        assert "required_group_ids = fields.Many2many(" in source
        assert "search='_search_shared_user_ids'" in source
        assert 'return search_shared_user_ids(self, operator, value)' in source
    assert 'return user_may_use(self, user or self.env.user)' in _SKILL.split('def user_may_run', 1)[1]
    assert 's.user_may_run()' in _SKILL.split('def list_for_agent', 1)[1].split(
        'def user_can_author_skills', 1)[0]
    assert _ENGINE.count('s.user_may_run()') >= 2
    assert '_required_groups_from_meta' in _SKILL
    assert "'required_groups' in meta" in _SKILL


def test_a_shared_context_leaves_the_agent_cache_and_goes_per_user():
    cache = _AGENT.split('def _shared_contexts_for_cache', 1)[1].split('\n    def ', 1)[0]
    assert 'not c.owner_id and not c.required_group_ids' in cache
    per_user = _AGENT.split('def _user_owned_contexts_for_user', 1)[1].split('\n    def ', 1)[0]
    assert '(c.owner_id or c.required_group_ids)' in per_user
    assert 'filter_visible_for_user(per_user, user=user)' in per_user
