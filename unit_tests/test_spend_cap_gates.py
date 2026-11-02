# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Monthly provider spend cap: fields, gates, no mid-turn cut, Test Connection free."""
from pathlib import Path

from _load_addon import addon_file, engine_source

_ROOT = Path(__file__).resolve().parents[1]


def test_spend_helper_is_shape_only():
    src = (_ROOT / 'common' / 'utils' / 'provider_spend.py').read_text(
        encoding='utf-8',
    )
    assert 'def spend_cap_hit' in src
    assert 'def cap_is_set' in src
    assert 'import odoo' not in src
    assert 'from odoo' not in src


def test_provider_has_monthly_caps_and_wizard():
    src = (_ROOT / 'common' / 'models' / 'ai_provider.py').read_text(
        encoding='utf-8',
    )
    assert 'spend_cap_usd' in src
    assert 'spend_cap_tokens' in src
    assert 'def month_usage' in src
    assert 'def assert_spend_cap' in src
    assert 'def action_open_usage' in src
    test = src.split('def test_connection', 1)[1].split('\n    def ', 1)[0]
    assert 'assert_spend_cap' not in test


def test_engine_skips_a_capped_key_then_tries_the_next():
    src = (_ROOT / 'common' / 'models' / 'ai_execution_engine.py').read_text(
        encoding='utf-8',
    )
    block = src.split('def get_providers_for_agent', 1)[1].split(
        '\n    def ', 1,
    )[0]
    assert 'self._without_capped(' in block
    assert 'def _without_capped' in src
    assert 'spend_cap_reached()' in src
    assert 'No AI provider has available quota this month.' in block
    assert 'if not chain and fitted and not uncapped:' in block
    driver = src.split('def _driver_for_provider', 1)[1].split(
        '\n    def ', 1,
    )[0]
    assert 'provider.assert_spend_cap()' in driver
    choose = src.split('def _choose(', 1)[1].split('\n    def ', 1)[0]
    # The engine loop catches Exception; the provider _choose asserts.
    assert 'provider._choose(' in choose
    log = src.split('def _log_llm_inference', 1)[1].split('\n    def ', 1)[0]
    assert 'provider_id=provider.id if provider else False' in log


def test_provider_choose_and_light_calls_assert_before_the_driver():
    src = (_ROOT / 'common' / 'models' / 'ai_provider.py').read_text(
        encoding='utf-8',
    )
    choose = src.split('def _choose(', 1)[1].split('\n    def ', 1)[0]
    assert 'self.assert_spend_cap()' in choose
    engine = engine_source()
    short = engine.split('def llm_json_completion_result', 1)[1].split(
        'def llm_json_completion(',
    )[0]
    assert 'provider.assert_spend_cap()' in short
    for_agent = engine.split('def llm_json_completion_for_agent', 1)[1].split(
        'def llm_completion_for_agent', 1,
    )[0]
    assert 'except UserError' in for_agent
    assert 'No AI provider has available quota this month.' not in for_agent
    stream = engine.split('def _tool_loop_provider_config', 1)[1].split(
        '\n    def ', 1,
    )[0]
    assert 'provider.assert_spend_cap()' in stream
    assert 'ProviderConnectionError' in stream


def test_log_row_keeps_the_provider():
    src = (_ROOT / 'common' / 'models' / 'ai_log.py').read_text(encoding='utf-8')
    assert "provider_id = fields.Many2one(" in src
    create = src.split('def _create_log_entry', 1)[1]
    assert "'provider_id': provider_id" in create
    for rel in (
        'stacks/owl1/pns_ai_mcp/views/ai_provider_views.xml',
        'stacks/owl2/pns_ai_mcp/views/ai_provider_views.xml',
    ):
        view = (_ROOT / rel).read_text(encoding='utf-8')
        assert 'name="action_open_usage"' in view
        assert 'name="spend_cap_usd"' in view
        assert 'name="spend_cap_tokens"' in view
    wizard = addon_file('wizard', 'ai_provider_usage_wizard_views.xml').read_text(
        encoding='utf-8',
    )
    assert 'action_open_log' in wizard
    for rel in (
        'stacks/owl1/pns_ai_mcp/__manifest__.py',
        'stacks/owl2/pns_ai_mcp/__manifest__.py',
    ):
        man = (_ROOT / rel).read_text(encoding='utf-8')
        assert 'wizard/ai_provider_usage_wizard_views.xml' in man
