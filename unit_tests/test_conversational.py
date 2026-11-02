# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Conversational door: agent flag + user group. No product names in the helper."""
from __future__ import annotations

from pathlib import Path

from _load_addon import engine_source, load_module

_ROOT = Path(__file__).resolve().parents[1]
conv = load_module('conversational', 'utils', 'conversational.py')


class _User:
    def __init__(self, ok):
        self._ok = ok

    def sudo(self):
        return self

    def has_group(self, xmlid):
        return bool(self._ok and xmlid == conv.GROUP_AI_CONVERSATIONAL)


class _Agent:
    def __init__(self, flag):
        self.is_agent_conversational = flag


def test_closed_agent_allows_anyone():
    assert conv.user_may_use_conversational_agent(
        None, _User(False), agent=_Agent(False),
    )
    assert conv.user_may_use_conversational_agent(
        None, _User(True), agent=_Agent(False),
    )


def test_open_agent_needs_the_group():
    assert not conv.user_may_use_conversational_agent(
        None, _User(False), agent=_Agent(True),
    )
    assert conv.user_may_use_conversational_agent(
        None, _User(True), agent=_Agent(True),
    )


def test_missing_agent_is_not_the_dialogue_door():
    assert not conv.agent_is_conversational(None, agent_code='anything')
    assert conv.user_may_use_conversational_agent(
        None, _User(False), agent_code='anything',
    )


def test_helper_does_not_name_products():
    src = (_ROOT / 'common' / 'utils' / 'conversational.py').read_text(
        encoding='utf-8',
    )
    for needle in ('Chatboo', 'Secretary', 'pns_ai_chatboo', 'pns_secretary'):
        assert needle not in src


def test_mcp_seed_is_conversational_admin_is_not():
    xml = (_ROOT / 'common' / 'data' / 'ai_agent_data.xml').read_text(
        encoding='utf-8',
    )
    mcp = xml.split('id="ai_agent_mcp"')[1].split('<record')[0]
    admin = xml.split('id="ai_agent_admin"')[1]
    assert 'is_agent_conversational' in mcp
    assert 'eval="True"' in mcp
    assert 'is_agent_conversational' not in admin


def test_stamp_rewrites_existing_rows():
    stamp = (
        _ROOT / 'common' / 'data' / 'ai_agent_conversational.xml'
    ).read_text(encoding='utf-8')
    assert 'noupdate="1"' not in stamp
    assert 'ai_agent_mcp' in stamp
    assert 'is_agent_conversational' in stamp
    assert 'eval="True"' in stamp
    assert 'ai_agent_admin' not in stamp


def test_admin_does_not_imply_conversational():
    for stack in ('owl1', 'owl2'):
        xml = (
            _ROOT / 'stacks' / stack / 'pns_ai_mcp' / 'security'
            / 'security_groups.xml'
        ).read_text(encoding='utf-8')
        assert 'group_ai_conversational' in xml
        admin = xml.split('id="group_ai_admin"')[1]
        implied = admin.split('implied_ids')[1].split('/>')[0]
        assert 'group_ai_conversational' not in implied
        conv_block = xml.split('id="group_ai_conversational"')[1].split(
            '<record',
        )[0]
        assert "ref('base.group_user')" in conv_block
        assert 'AI Conversational' in conv_block


def test_user_form_lists_the_flag_after_external_api():
    for stack in ('owl1', 'owl2'):
        xml = (
            _ROOT / 'stacks' / stack / 'pns_ai_mcp' / 'views'
            / 'mcp_user_views.xml'
        ).read_text(encoding='utf-8')
        form = xml.split('view_mcp_user_form')[1]
        assert form.index('is_ai_external_api') < form.index(
            'is_ai_conversational',
        )


def test_agent_form_and_list_show_the_flag():
    for stack in ('owl1', 'owl2'):
        xml = (
            _ROOT / 'stacks' / stack / 'pns_ai_mcp' / 'views'
            / 'ai_agent_views.xml'
        ).read_text(encoding='utf-8')
        tree = xml.split('view_ai_agent_tree')[1].split('view_ai_agent_form')[0]
        form = xml.split('view_ai_agent_form')[1]
        assert 'is_agent_conversational' in tree
        assert 'is_agent_conversational' in form
        assert 'readonly="1"' in tree.split('is_agent_conversational')[1].split('/>')[0]
        assert 'readonly="1"' in form.split('is_agent_conversational')[1].split('/>')[0]
        assert tree.index('agent_type') < tree.index('is_agent_conversational')
        assert form.index('agent_type') < form.index('is_agent_conversational')


def test_factory_seed_declares_mcp_conversational():
    src = (_ROOT / 'common' / 'models' / 'ai_agent.py').read_text(
        encoding='utf-8',
    )
    blob = src.split('def _module_factory_seed')[1].split('def _default_context_tokens')[0]
    assert "'is_agent_conversational': True" in blob


def test_init_stamps_conversational_from_factory_seed():
    src = (_ROOT / 'common' / 'models' / 'ai_agent.py').read_text(
        encoding='utf-8',
    )
    assert 'def _stamp_conversational_from_factory_seed' in src
    assert '_stamp_conversational_from_factory_seed()' in src.split('def init')[1].split(
        'def _clear_admin_auto_link_all_fossil',
    )[0]


def test_factory_seed_declares_mcp_conversational():
    src = (_ROOT / 'common' / 'models' / 'ai_agent.py').read_text(
        encoding='utf-8',
    )
    blob = src.split('def _module_factory_seed')[1].split('def _default_context_tokens')[0]
    assert "'is_agent_conversational': True" in blob


def test_engine_refuses_with_the_helper():
    src = engine_source()
    assert 'user_may_use_conversational_agent' in src
    assert 'REFUSED_MESSAGE' in src
    assert 'if not user_may_use_conversational_agent' in src
    assert 'closed_job' not in src


def test_mcp_controller_checks_after_the_key():
    src = (_ROOT / 'common' / 'controllers' / 'main.py').read_text(
        encoding='utf-8',
    )
    assert '_mcp_conversational_denied' in src
    assert src.count('_mcp_conversational_denied') >= 5


def test_manifests_load_the_stamp():
    import re
    versions = set()
    for stack in ('owl1', 'owl2'):
        text = (
            _ROOT / 'stacks' / stack / 'pns_ai_mcp' / '__manifest__.py'
        ).read_text(encoding='utf-8')
        assert 'ai_agent_conversational.xml' in text
        assert text.index('ai_agent_data.xml') < text.index(
            'ai_agent_conversational.xml',
        )
        found = re.search(r"'version':\s*'(\d+\.\d+\.\d+)'", text)
        assert found, stack
        versions.add(found.group(1))
    # One number for both stacks. Which number is not the test's business.
    assert len(versions) == 1
