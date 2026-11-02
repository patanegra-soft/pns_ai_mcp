# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Anchor: the 'discovery = index only' invariant lives in one place.

``utils/context_roles.py`` is the only source of truth for
``context_type`` roles. These tests fail if someone:
  * puts ``discovery`` on the inject/list/compose lists, or
  * scatters the literal ``('core', 'discovery')`` tuple in the code
    instead of asking the roles module.
"""
from __future__ import annotations

from _load_addon import addon_file, context_source, load_module

roles = load_module('pns_ctx_roles', 'utils', 'context_roles.py')


def test_discovery_is_never_injectable():
    assert roles.DISCOVERY not in roles.INJECTABLE_TYPES
    assert roles.is_discovery(roles.DISCOVERY) is True


def test_discovery_is_never_mcp_listed_nor_agent_composable():
    assert roles.DISCOVERY not in roles.MCP_LISTABLE_TYPES
    assert roles.DISCOVERY in roles.AGENT_LINK_EXCLUDED_TYPES
    assert roles.is_agent_composable(roles.DISCOVERY) is False


def test_core_is_injected_but_not_hand_composed():
    assert roles.CORE in roles.INJECTABLE_TYPES
    assert roles.CORE in roles.AGENT_LINK_EXCLUDED_TYPES
    assert roles.is_agent_composable(roles.CORE) is False


def test_domain_and_locale_are_injectable():
    assert roles.DOMAIN in roles.INJECTABLE_TYPES
    assert roles.LOCALE in roles.INJECTABLE_TYPES
    assert roles.is_agent_composable(roles.DOMAIN) is True
    assert roles.is_agent_composable(roles.LOCALE) is True


def test_canonical_type_has_no_legacy_aliases():
    assert roles.canonical_type('discovery') == roles.DISCOVERY
    assert roles.canonical_type('locale') == roles.LOCALE
    assert roles.canonical_type('core') == roles.CORE
    assert roles.canonical_type('domain') == roles.DOMAIN
    assert roles.canonical_type('translation') == roles.DOMAIN
    assert roles.canonical_type('protocol') == roles.DOMAIN
    assert roles.canonical_type('protocol', is_system=True) == roles.CORE
    assert roles.canonical_type('', discovery_folder=True) == roles.DISCOVERY


def test_canonical_discovery_code_rewrites_disc_prefix():
    assert roles.canonical_discovery_code('disc_acl_security') == 'discovery_acl_security'
    assert roles.canonical_discovery_code('disc_api_ext_es_ES') == (
        'discovery_api_ext_es_ES'
    )
    assert roles.canonical_discovery_code('discovery_geo') == 'discovery_geo'
    assert roles.canonical_discovery_code('acl_security') == 'acl_security'


def test_all_types_cover_every_role():
    assert set(roles.ALL_TYPES) == {
        roles.CORE, roles.DOMAIN, roles.LOCALE, roles.DISCOVERY,
    }


def _reads(*parts: str) -> str:
    if parts == ('models', 'ai_context.py'):
        return context_source()
    return addon_file(*parts).read_text(encoding='utf-8')


def test_no_scattered_core_discovery_tuple_literals():
    """The invariant sites must not list the tuple by hand again."""
    targets = (
        ('models', 'ai_context.py'),
        ('models', 'ai_agent.py'),
        ('wizard', 'bundle_compose_wizard.py'),
    )
    for parts in targets:
        src = _reads(*parts)
        assert "('core', 'discovery')" not in src, parts
        assert "('core','discovery')" not in src, parts
        assert 'from ..utils import context_roles' in src, parts
