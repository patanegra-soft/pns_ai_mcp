# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Unit tests for host identity injection into the system prompt."""

from __future__ import annotations

from _load_addon import addon_file, load_module

ident = load_module('agent_identity', 'utils', 'agent_identity.py')
mcp_ident = load_module('mcp_identity', 'utils', 'mcp_identity.py')


def test_apply_injects_one_name_and_one_vendor():
    out = ident.apply_resolved_identity(
        'Protocol body',
        product_name='MCP Server',
        vendor='PATANEGRA Soft',
        vendor_place='Seville (Spain)',
        vendor_years='1996–2026',
        vendor_url='https://www.patanegra.com',
    )
    assert out.count(ident.AUTHORSHIP_HEADING) == 1
    assert out.count(ident.IDENTITY_HEADING) == 1
    assert 'PATANEGRA Soft' in out
    assert 'MCP Server' in out
    assert 'Protocol body' in out
    assert out.index(ident.AUTHORSHIP_HEADING) < out.index(ident.IDENTITY_HEADING)
    assert 'who are you' not in out
    assert 'at most once' not in out
    assert 'Chatboo' not in out


def test_apply_is_idempotent():
    once = ident.apply_resolved_identity(
        'Body', product_name='MCP Server', vendor='PATANEGRA Soft',
    )
    twice = ident.apply_resolved_identity(
        once, product_name='MCP Server', vendor='PATANEGRA Soft',
    )
    assert once == twice


def test_empty_facts_leave_prompt():
    assert ident.apply_resolved_identity('Only protocol') == 'Only protocol'


def test_system_prompt_has_no_product_brand():
    xml = addon_file(
        'ai', 'contexts', 'core', 'system_prompt.xml',
    ).read_text(encoding='utf-8')
    assert 'Chatboo' not in xml
    assert 'PATANEGRA' not in xml
    assert 'injected `self`' not in xml
    assert 'injected self' not in xml
    assert 'host UI lists' in xml
    assert 'NOT data requests' in xml
    assert 'CAPABILITY / IDENTITY QUESTIONS' in xml
    assert 'who made you' in xml
    assert 'system://info' not in xml
    assert 'skill.<code>' not in xml
    assert 'own trigger phrases (one match)' in xml
    assert 'Slash procedures run only via /command' not in xml


def test_self_mcp_pack_is_exclusive():
    xml = addon_file(
        'ai', 'contexts', 'domain', 'self_mcp', 'self_mcp.xml',
    ).read_text(encoding='utf-8')
    assert '<code>self_mcp</code>' in xml
    assert '<agent_codes>pns_ai_mcp</agent_codes>' in xml
    assert 'Chatboo' not in xml
    assert 'You are not' not in xml
    assert 'present yourself as' not in xml
    assert '<product_name>' not in xml
    assert '<display_name>' not in xml
    assert '<vendor>' not in xml
    assert "This endpoint gives that model the\ninstance's knowledge and tools." in xml.replace('\r\n', '\n')
    assert 'system://info' not in xml
    assert 'Do not mention vendor' in xml
    assert 'who created you' in xml
    assert 'who made you' in xml
    assert 'vendor block only' in xml


def test_mcp_registry_has_only_mcp_code():
    reg = mcp_ident.mcp_host_identity_registry()
    assert list(reg) == ['pns_ai_mcp']
    assert 'pns_ai_chatboo' not in reg
    assert reg['pns_ai_mcp']['product_name'] == 'MCP Server'
    assert 'display_name' not in reg['pns_ai_mcp']


def test_apply_accepts_display_name_alias():
    out = ident.apply_resolved_identity(
        'Body', display_name='Legacy Name', vendor='Acme',
    )
    assert 'Legacy Name' in out
    assert ident.IDENTITY_HEADING in out


def test_first_identity_text():
    assert ident.first_identity_text(None, '', '  Chatboo  ') == 'Chatboo'
    assert ident.first_identity_text('', None) == ''


def test_own_self_pack_code():
    assert ident.own_self_pack_code('pns_ai_mcp') == 'self_mcp'
    assert ident.own_self_pack_code('pns_ai_chatboo') == 'self_chatboo'
    assert ident.own_self_pack_code('pns_secretary') == 'self_secretary'
    assert ident.own_self_pack_code('') == ''


def test_retired_self_is_foreign_for_every_agent():
    assert ident.is_retired_self_pack_code('self')
    assert ident.is_retired_self_pack_code('self_es_ES')
    assert ident.is_retired_self_pack_code('self_en_US')
    assert ident.is_retired_self_pack_code('self_retired')
    assert not ident.is_retired_self_pack_code('self_chatboo')
    assert not ident.is_retired_self_pack_code('self_secretary')
    assert not ident.is_retired_self_pack_code('self_mcp')
    assert ident.is_retired_self_source_path('contexts/domain/self/self.xml')
    assert ident.is_retired_self_source_path('contexts/domain/self/self_es_ES.xml')
    assert not ident.is_retired_self_source_path(
        'contexts/domain/self_chatboo/self_chatboo.xml',
    )
    assert ident.is_identity_pack_code('self')
    assert ident.is_identity_pack_code('self_chatboo')
    assert not ident.is_identity_pack_code('geo')
    assert ident.is_foreign_identity_pack('pns_ai_mcp', 'self')
    assert ident.is_foreign_identity_pack('pns_ai_mcp', 'self_chatboo')
    assert not ident.is_foreign_identity_pack('pns_ai_mcp', 'self_mcp')
    assert ident.is_foreign_identity_pack('pns_ai_chatboo', 'self_mcp')
    assert not ident.is_foreign_identity_pack('pns_ai_chatboo', 'self_chatboo')
    assert ident.foreign_identity_on_demand_message(
        'pns_ai_mcp', 'self_chatboo',
    )
    assert ident.foreign_identity_on_demand_message(
        'pns_ai_mcp', 'self_mcp',
    ) is None


def test_scrub_pin_drops_retired_self_without_mixing():
    chatboo = ident.ensure_pin_token(
        ident.drop_pin_tokens(
            'self\npresentation_grids\nui_focus', {'self'},
        ),
        'self_chatboo',
    )
    assert ident.parse_pin_tokens(chatboo) == [
        'presentation_grids', 'ui_focus', 'self_chatboo',
    ]
    mcp = ident.drop_pin_tokens('self\nself_mcp', {'self', 'self_chatboo'})
    assert ident.parse_pin_tokens(mcp) == ['self_mcp']
