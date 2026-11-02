# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Anchor: the engine module never names a product skill.

Inventory (Chatboo system skills — domain lives in THAT repo, not here):

  annual-billing, billing, credit-facility, customer-risk-analysis,
  dashboard, financial-health, flota, forecast, payroll, polizas,
  sys-info, users-all, users-logged.

Generic stems (billing, forecast, dashboard, payroll) are engine vocabulary
too (show_mode, weather-as-data). This test forbids *identity* needles:
slash, skill.<cmd>, hyphenated commands, underscored catalog ids.
"""
from __future__ import annotations

from pathlib import Path
from _load_addon import context_source, engine_source, skill_source
from _tenant_needles import names_tenant

_MCP = Path(__file__).resolve().parents[1]
_COMMON = _MCP / 'common'
_MODULES = _MCP.parent

# Distinctive identities even if sibling skill trees are absent.
_FALLBACK_PAIRS = (
    ('annual-billing', 'annual_billing'),
    ('billing', 'billing'),
    ('credit-facility', 'credit_facility'),
    ('customer-risk-analysis', 'customer_risk_analysis'),
    ('dashboard', 'dashboard'),
    ('financial-health', 'financial_health'),
    ('flota', 'flota'),
    ('forecast', 'forecast'),
    ('payroll', 'payroll'),
    ('polizas', 'polizas'),
    ('sys-info', 'sys_info'),
    ('users-all', 'users_all'),
    ('users-logged', 'users_logged'),
)


def _pairs_from_skill_tree(root):
    pairs = []
    if not root.is_dir():
        return pairs
    for md in root.rglob('*.md'):
        text = md.read_text(encoding='utf-8')
        command = ''
        for line in text.splitlines()[:20]:
            if line.startswith('skill:'):
                command = line.split(':', 1)[1].strip()
                break
        code = md.stem
        if command or code:
            pairs.append((command or code.replace('_', '-'), code))
    return pairs


def _product_pairs():
    pairs = list(_FALLBACK_PAIRS)
    seen = {(c, k) for c, k in pairs}
    for tree in sorted(_MODULES.glob('*/common/ai/skills')):
        if tree.parents[2] == _MCP:
            continue
        for pair in _pairs_from_skill_tree(tree):
            if pair not in seen:
                seen.add(pair)
                pairs.append(pair)
    return pairs


def _needles(pairs):
    out = [
        'Análisis financiero',
        'Analisis financiero',
    ]
    for command, code in pairs:
        if command:
            out.append('/%s' % command)
            out.append('skill.%s' % command)
            if '-' in command:
                out.append(command)
        if code and '_' in code:
            out.append(code)
    # Unique, longest first so reports are readable
    return sorted(set(out), key=len, reverse=True)


def _iter_engine_files():
    tests_root = _COMMON / 'tests'
    for path in _COMMON.rglob('*'):
        if not path.is_file():
            continue
        if path.suffix.lower() not in ('.py', '.md', '.xml'):
            continue
        # Host tests may assert sibling catalog codes (Chatboo pin, etc.).
        if tests_root in path.parents:
            continue
        yield path


_FIRST_INSTALL_DATA = (
    'data/url_whitelist_data.xml',
    'data/instance_defaults_data.xml',
)
_BANNED_FIRST_INSTALL = (
    'data/external_server_data.xml',
    'data/external_server_openapi_data.xml',
)


def test_first_install_shells_not_in_manifest_data():
    """Placeholders are post_init only. A -u must not create extra xmlids."""
    hooks = (_COMMON / 'hooks.py').read_text(encoding='utf-8')
    assert '_load_first_install_data' in hooks
    for banned in (
        'pre_init_hook',
        '_ensure_provider_failovers',
        '_reload_module_translations',
        '_disable_execute_confirmed_cron',
        '_migrate_display_currency',
        '_purge_legacy_disc_leftovers',
        '_fill_empty_factory_seeds',
    ):
        assert banned not in hooks, banned
    for rel in _FIRST_INSTALL_DATA:
        assert (_COMMON / rel).is_file(), rel
    for rel in _BANNED_FIRST_INSTALL:
        assert not (_COMMON / rel).is_file(), rel
    hooks_files = hooks[hooks.find('files ='):hooks.find('sig =')]
    assert 'external_server' not in hooks_files
    for stack in ('owl1', 'owl2'):
        text = (
            _MCP / 'stacks' / stack / 'pns_ai_mcp' / '__manifest__.py'
        ).read_text(encoding='utf-8')
        for rel in _FIRST_INSTALL_DATA:
            assert rel not in text, '%s still in %s manifest data' % (rel, stack)
        assert 'external_server_data.xml' not in text
        assert 'data/mcp_data.xml' in text


def test_no_legacy_schema_heal_in_init():
    """init/_auto_init are not leftover column copies. owl1 assets stay."""
    ctx = context_source()
    assert 'load_odoo14_assets_if_needed' in ctx
    assert '_purge_legacy_disc_leftovers' not in ctx
    skill = skill_source()
    assert 'def init(' not in skill
    assert '_migrate_kebab_catalog_ids' not in skill
    provider = (_COMMON / 'models' / 'ai_provider.py').read_text(encoding='utf-8')
    assert 'def init(' not in provider
    assert 'laconic_mode' not in provider
    server = (_COMMON / 'models' / 'external_server.py').read_text(encoding='utf-8')
    assert 'def _auto_init(' not in server
    assert 'def init(' not in server
    assert '_ensure_id_sequence' not in server
    whitelist = (_COMMON / 'models' / 'url_whitelist.py').read_text(encoding='utf-8')
    assert 'def _auto_init(' not in whitelist
    agent = (_COMMON / 'models' / 'ai_agent.py').read_text(encoding='utf-8')
    assert '_fill_empty_factory_seeds' not in agent


def test_no_llm_provider_ships_with_the_engine():
    """The instance adds its own providers. Install and -u seed none."""
    assert not (_COMMON / 'data' / 'ai_provider_data.xml').is_file()
    for xml in (_COMMON / 'data').glob('*.xml'):
        assert 'model="ai.provider"' not in xml.read_text(encoding='utf-8'), xml.name
    hooks = (_COMMON / 'hooks.py').read_text(encoding='utf-8')
    assert 'ai_provider_data' not in hooks


def test_change_journal_menu_is_admin_only():
    """Security → Applied changes is AI admin only (writers hit Access Error)."""
    for stack in ('owl1', 'owl2'):
        text = (
            _MCP / 'stacks' / stack / 'pns_ai_mcp' / 'views'
            / 'ai_change_journal_views.xml'
        ).read_text(encoding='utf-8')
        assert 'menu_ai_change_journal' in text
        assert 'group_ai_admin' in text
        assert 'group_ai_writer' not in text
        assert 'base.group_system' not in text
        action_chunk = text.split('<menuitem', 1)[0]
        assert '<field name="groups_id"' not in action_chunk
        assert 'model="ir.ui.menu"' in text
        menu_chunk = text.split('<menuitem', 1)[1]
        if stack == 'owl2':
            assert 'name="group_ids"' in menu_chunk
            assert 'name="groups_id"' not in menu_chunk
        else:
            assert 'name="groups_id"' in menu_chunk
        assert 'name="Applied changes"' in text
        assert 'name="Journal"' not in text
        assert 'name="Changes"' not in text


def test_knowledge_menu_is_discovery_not_domain_discovery():
    for stack in ('owl1', 'owl2'):
        text = (
            _MCP / 'stacks' / stack / 'pns_ai_mcp' / 'views'
            / 'ai_domain_index_views.xml'
        ).read_text(encoding='utf-8')
        assert 'name="Discovery"' in text
        assert 'Domain Discovery' not in text


def test_engine_factory_seed_is_own_module_only():
    """Motor seed is nameless: this addon + system drawer, no tenant."""
    xml = (_COMMON / 'data' / 'mcp_data.xml').read_text(encoding='utf-8')
    assert 'import_from_files' not in xml
    assert "import_from_module" in xml
    assert "'pns_ai_mcp'" in xml
    assert "['system']" in xml
    assert not names_tenant(xml)


def test_factory_surface_names_no_tenant_apis():
    """data/ + ai/ + wizard: factory install must not teach tenant APIs."""
    roots = (
        _COMMON / 'data',
        _COMMON / 'ai',
        _COMMON / 'wizard',
    )
    hits = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.rglob('*'):
            if not path.is_file():
                continue
            if path.suffix.lower() not in ('.py', '.md', '.xml', '.json'):
                continue
            needle = names_tenant(path.read_text(encoding='utf-8'))
            if needle:
                hits.append('%s: %s' % (
                    path.relative_to(_MCP).as_posix(), needle,
                ))
    assert hits == [], 'Factory surface names tenant APIs:\n  %s' % (
        '\n  '.join(hits)
    )


def test_engine_common_does_not_name_product_skills():
    needles = _needles(_product_pairs())
    hits = []
    for path in _iter_engine_files():
        text = path.read_text(encoding='utf-8')
        for needle in needles:
            if needle in text:
                rel = path.relative_to(_MCP).as_posix()
                hits.append('%s: %s' % (rel, needle))
    assert hits == [], (
        'Engine common/ names product skills (fix the skill or a nameless '
        'generic mechanism; do not patch the addon):\n  %s'
        % '\n  '.join(hits)
    )


def test_report_outline_guard_has_no_section_lexicon():
    src = (_COMMON / 'utils' / 'report_outline_guard.py').read_text(
        encoding='utf-8',
    )
    for token in (
        "'recomendaciones'",
        "'recommendations'",
        "'acciones prioritarias'",
        "'priority actions'",
    ):
        assert token not in src


def test_handoff_prompt_has_no_finance_example():
    src = engine_source()
    assert 'Análisis financiero' not in src
    assert 'Analisis financiero' not in src
    assert 'annual-billing' not in src
