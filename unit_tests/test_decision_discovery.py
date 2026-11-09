# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Decision Choice for discovery: unique winner, accept bar, step summary."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from _load_addon import engine_source, load_module

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / 'common'))

di = load_module('domain_index', 'utils', 'domain_index.py')
dc = load_module('decision_choice', 'utils', 'decision_choice.py')


def _entries():
    return [
        {'code': 'hr_payroll', 'score': 2, 'soft_depends': ['hr_payroll_accounting_present']},
        {'code': 'custom_acme_staffhr', 'score': 1, 'soft_depends': []},
    ]


def test_unique_winner_skips_decision():
    assert di.sentence_has_unique_winner(_entries()) is True


def test_empty_and_tie_need_decision():
    assert di.sentence_has_unique_winner([]) is False
    tied = [
        {'code': 'hr_payroll', 'score': 1},
        {'code': 'custom_acme_staffhr', 'score': 1},
    ]
    assert di.sentence_has_unique_winner(tied) is False


def test_choice_none_or_low_confidence_keeps_word_list():
    criteria = di.build_pack_choice_criteria(
        _entries(),
        {'hr_payroll': 'Payslips and salary'},
    )
    assert criteria['none'].startswith('The message does not')
    assert di.accept_pack_choice(
        {'choice': 'none', 'confidence': 0.9}, criteria, 0.7,
    ) is None
    assert di.accept_pack_choice(
        {'choice': 'hr_payroll', 'confidence': 0.4}, criteria, 0.7,
    ) is None


def test_accepted_choice_keeps_soft_depends():
    criteria = di.build_pack_choice_criteria(_entries(), {})
    chosen = di.accept_pack_choice(
        {'choice': 'hr_payroll', 'confidence': 0.81}, criteria, 0.7,
    )
    assert chosen == 'hr_payroll'
    assert di.codes_for_pack_choice(_entries(), chosen) == [
        'hr_payroll', 'hr_payroll_accounting_present',
    ]


def test_over_cap_does_not_truncate():
    entries = [{'code': 'p%s' % i} for i in range(255)]
    assert di.build_pack_choice_criteria(entries, {}) is None


def test_step_summary_names_the_route():
    det = di.discovery_step_summary('deterministic', 'Domains: hr_payroll', 0.05)
    assert det.startswith('words · Domains: hr_payroll')
    ok = di.discovery_step_summary(
        'decision', 'Domains: hr_payroll', 120.0,
        choice='hr_payroll', confidence=0.81,
    )
    assert ok.startswith('decision · choice=hr_payroll confidence=0.81')
    declined = di.discovery_step_summary(
        'decision', 'Domains: (none)', 80.0, declined=True,
    )
    assert declined.startswith('decision · declined · Domains')


def test_parse_choice_response():
    parsed = dc.parse_choice_response({
        'model': 'decision-model',
        'answers': {
            'pack': {
                'type': 'choice',
                'choice': 'hr_payroll',
                'confidence': 0.81,
                'probabilities': {'hr_payroll': 0.9, 'none': 0.1},
            },
        },
        'usage': {'input_tokens': 10, 'output_tokens': 4},
    })
    assert parsed['choice'] == 'hr_payroll'
    assert parsed['usage']['input_tokens'] == 10


def test_systemone_choose_reads_the_body(monkeypatch):
    class _Resp:
        def read(self):
            return json.dumps({
                'model': 'decision-model',
                'answers': {'pack': {'choice': 'none', 'confidence': 0.2}},
                'usage': {},
            }).encode('utf-8')

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    import lib.llm.drivers.systemone_driver as systemone_driver
    monkeypatch.setattr(
        systemone_driver.urllib.request, 'urlopen', lambda req, timeout=None: _Resp(),
    )
    driver = systemone_driver.SystemOneDriver()
    driver.initialize({
        'endpoint': 'https://example.test/v1/systemone',
        'api_key': 'k',
        'model_name': 'decision-model',
    })
    parsed = driver.choose(
        'quién ganaba más',
        {'hr_payroll': 'salary', 'none': 'no pack'},
        'Which pack?',
    )
    assert parsed['choice'] == 'none'


def test_systemone_chooses_and_does_not_chat():
    import lib.llm.drivers as drivers
    driver = drivers.get_llm_driver('systemone')
    assert driver.chooses is True
    assert driver.chats is False
    try:
        driver.chat_completion([{'role': 'user', 'content': 'hi'}])
    except RuntimeError as exc:
        assert 'does not complete chat' in str(exc)
    else:
        raise AssertionError('systemone completed chat')
    chat = drivers.get_llm_driver('openai')
    assert chat.chats is True
    assert chat.chooses is False


def test_a_decision_tick_keeps_the_provider_out_of_a_text_turn():
    fit = load_module('provider_fit', 'utils', 'provider_fit.py')
    flags = {'decision': True}
    assert fit.provider_fits(flags, None) is False
    assert fit.provider_fits(flags, 'conversation') is False
    assert fit.provider_fits(flags, 'decision') is True
    assert fit.provider_fits({}, 'decision') is False


def test_design_is_a_fit_not_a_second_chain():
    engine = (_ROOT / 'common' / 'models' / 'ai_execution_engine.py').read_text(
        encoding='utf-8',
    )
    assert 'def get_design_providers' not in engine
    block = engine.split('def get_providers_for_agent', 1)[1].split(
        '\n    def ', 1,
    )[0]
    assert "if not chain and need and need != 'conversation' and failovers:" in block
    assert 'Link.sudo().create' not in block
    assert "sudo().search" in block
    src = (_ROOT / 'common' / 'models' / 'ai_provider.py').read_text(encoding='utf-8')
    assert 'cannot complete a chat' not in src
    seed = (_ROOT / 'common' / 'data' / 'ai_provider_role_data.xml').read_text(
        encoding='utf-8',
    )
    assert '<field name="code">design</field>' in seed
    for rel in (
        'stacks/owl1/pns_ai_mcp/views/ai_provider_views.xml',
        'stacks/owl2/pns_ai_mcp/views/ai_provider_views.xml',
    ):
        view = (_ROOT / rel).read_text(encoding='utf-8')
        field = view.split('<field name="role_ids"', 1)[1].split('/>', 1)[0]
        assert 'systemone' not in field


def test_the_decision_chain_is_the_tick_not_the_protocol():
    engine = (_ROOT / 'common' / 'models' / 'ai_execution_engine.py').read_text(
        encoding='utf-8',
    )
    block = engine.split('def get_providers_for_agent', 1)[1].split(
        '\n    def ', 1,
    )[0]
    assert "'protocol'" not in block
    assert '.protocol' not in block
    assert 'if not need:\n            return found' not in block
    fail = engine.split('def get_failovers', 1)[1].split('\n    def ', 1)[0]
    assert 'protocol' not in fail
    assert 'def get_decision_providers' not in engine
    choose = engine.split('def _choose(', 1)[1].split('\n    def ', 1)[0]
    assert "need='decision'" in choose
    assert 'pns_ai_decision' not in choose
    assert 'agent_code' in choose
    src = engine_source()
    assert 'pns_ai_decision' not in src
    assert 'get_decision_providers' not in src
    assert "need='decision'" in src
    agent_py = (_ROOT / 'common' / 'models' / 'ai_agent.py').read_text(encoding='utf-8')
    assert '_drop_decision_agent_fossil' not in agent_py
    consumer = (_ROOT / 'common' / 'models' / 'ai_agent_consumer.py').read_text(
        encoding='utf-8',
    )
    unlink = consumer.split('def unlink', 1)[1].split('\n    def ', 1)[0]
    assert '_module_ships_agent' in unlink
    assert 'pns_ai_decision' not in agent_py
    assert '_active_decision_provider' not in src
    registry = (_ROOT / 'common' / 'lib' / 'llm' / 'drivers' / 'registry.py').read_text(
        encoding='utf-8',
    )
    assert "== 'decision'" not in registry


def test_empty_match_asks_topic_not_which_pack():
    """Miss + leftover state: same subject? Pack Choice does not run there."""
    src = engine_source()
    hint = src.split('def _domain_index_runtime_hint', 1)[1].split(
        '\n    def ', 1,
    )[0]
    assert 'needs_topic_continuity(' in hint
    assert 'self._maybe_topic_continuity(' in hint
    assert hint.index('needs_topic_continuity(') < hint.index(
        'self._maybe_decision_pack(',
    )
    assert 'self._prior_domain_codes = []' in hint
    assert "if prior_before and mode == 'injected' and not carried:" in hint
    run = src.split('def _run_stream_with_provider', 1)[1].split(
        '\n    def ', 1,
    )[0]
    assert 'if not getattr(self, \'_reuse_prior_query\', True):' in run
    assert 'prior_query_data = None' in run
    mono = src.split('def _topic_continuity_without_inject', 1)[1].split(
        '\n    def ', 1,
    )[0]
    assert 'needs_topic_continuity(' in mono
    assert 'self._maybe_topic_continuity(' in mono
    assert '_maybe_decision_pack(' not in mono
    assert 'self._reuse_prior_query = False' in mono
    assert hint.split('if not self._domain_index_inject_enabled()', 1)[1].split(
        'from .domain_index import', 1,
    )[0].count('_topic_continuity_without_inject(') == 1


def test_the_topic_choice_sees_the_previous_message():
    """HDDN: «add three filter buttons» was judged alone and called new."""
    history = [
        {'role': 'user', 'content': 'a pretty page with the whole fleet'},
        {'role': 'assistant', 'content': '<div>card</div>'},
    ]
    text = di.topic_choice_text('add three buttons that filter vans', history)
    assert text == (
        'Previous message:\na pretty page with the whole fleet\n\n'
        'This message:\nadd three buttons that filter vans'
    )
    listed = [{'role': 'user', 'content': [
        {'type': 'image_url', 'image_url': {'url': 'x'}},
        {'type': 'text', 'text': 'the fleet'},
    ]}]
    assert di.topic_choice_text('sort it', listed).startswith(
        'Previous message:\nthe fleet\n',
    )
    assert di.topic_choice_text('hello', []) == 'hello'
    assert 'previous message' in di.TOPIC_CHOICE_INSTRUCTIONS
    src = engine_source()
    topic = src.split('def _maybe_topic_continuity', 1)[1].split('\n    def ', 1)[0]
    assert "topic_choice_text(message, getattr(self, '_turn_history', None))" in topic
    run = src.split('def run_stream(', 1)[1].split('\n    def ', 1)[0]
    assert 'self._turn_history = list(history or [])' in run


def test_another_pack_with_rows_left_asks_before_dropping_them():
    """EUXR: «why no page?» named page_tab, so the 563 trial-balance rows went."""
    assert di.needs_topic_switch_check(
        ['page_tab'], ['trial_balance'], has_prior_query=True,
    ) is True
    assert di.needs_topic_switch_check(
        ['page_tab'], ['trial_balance'], has_prior_query=False,
    ) is False
    assert di.needs_topic_switch_check(
        ['page_tab', 'trial_balance'], ['trial_balance'], has_prior_query=True,
    ) is False
    assert di.needs_topic_switch_check([], ['trial_balance'], True) is False
    assert di.needs_topic_switch_check(['page_tab'], [], True) is False
    kept = di.union_domain_codes(['page_tab'], ['trial_balance'], keep_disjoint=True)
    assert kept['codes'] == ['page_tab', 'trial_balance']
    assert kept['carried'] == ['trial_balance']
    src = engine_source()
    for name in ('_domain_index_runtime_hint', '_topic_continuity_without_inject'):
        body = src.split('def %s' % name, 1)[1].split('\n    def ', 1)[0]
        assert 'needs_topic_switch_check(' in body
        assert 'keep_disjoint=same_subject' in body
        assert body.index('needs_topic_switch_check(') < body.index(
            'keep_disjoint=same_subject',
        )


def test_topic_continuity_helpers():
    assert di.needs_topic_continuity([], ['page_tab']) is True
    assert di.needs_topic_continuity([], [], has_prior_query=True) is True
    assert di.needs_topic_continuity(['partners'], ['page_tab']) is False
    assert di.needs_topic_continuity([], []) is False
    assert di.accept_topic_same({'choice': 'yes', 'confidence': 0.9}, 0.7)
    assert not di.accept_topic_same({'choice': 'none', 'confidence': 0.9}, 0.7)
    assert not di.accept_topic_same({'choice': 'yes', 'confidence': 0.4}, 0.7)
    assert not di.accept_topic_same(None, 0.7)
    line = di.discovery_step_summary(
        'topic', 'Domains: (none)', 40.0, declined=True,
    )
    assert line.startswith('topic · new · Domains: (none)')
    same = di.discovery_step_summary('topic', 'Domains: geo (2)', 20.0)
    assert same.startswith('topic · same · Domains: geo')
