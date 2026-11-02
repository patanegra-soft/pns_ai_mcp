# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Skill parameter inference walks the agent's provider chain."""
from __future__ import annotations

import json
import sys
from types import ModuleType

from _load_addon import load_module

es = load_module('engine_skills', 'utils', 'engine_skills.py')
_PKG = es.__name__.rsplit('.', 1)[0]


class _Prov:
    def __init__(self, pid, name, reply, needs=('conversation',)):
        self.id = pid
        self.name = name
        self.reply = reply
        self.needs = needs


class _Engine:
    def __init__(self, provs):
        self.provs = provs

    def get_providers_for_agent(self, agent_code, need=None):
        return [p for p in self.provs if (need or 'conversation') in p.needs]


class _Env(dict):
    def __contains__(self, key):
        return dict.__contains__(self, key)


class _Skill:
    code = 'billing'
    args_policy = None
    arg_hint = ''
    param_schema = json.dumps({
        'periodo': {'type': 'string', 'desc': 'YYYY=year, YYYY-YYYY=range.'},
    })


class _Host(es.SkillsMixin):
    def __init__(self, provs):
        self.env = _Env({'ai.execution.engine': _Engine(provs)})
        self.side = []
        self.rows = []

    def _resolve_user_locale(self):
        return 'es_ES'

    def _accumulate_side_usage(self, usage, provider=None):
        self.side.append((usage, getattr(provider, 'name', None)))

    def _mcp_log(self, **kwargs):
        self.rows.append(kwargs)


def _fake_llm(calls):
    mod = ModuleType(_PKG + '.agent_engine')
    mod.HYBRID_PARAM_MAX_TOKENS = 64

    def llm_json_completion_result(prov, system, user, max_tokens=0):
        calls.append(prov.name)
        return {'content': prov.reply, 'usage': {'prompt_tokens': 10, 'completion_tokens': 2}}

    mod.llm_json_completion_result = llm_json_completion_result
    return mod


def _run(turn_provider, provs, args='el año pasado'):
    calls = []
    saved = sys.modules.get(_PKG + '.agent_engine')
    sys.modules[_PKG + '.agent_engine'] = _fake_llm(calls)
    try:
        host = _Host(provs)
        out = host._normalize_skill_params(
            _Skill(), args, 'chatboo', provider=turn_provider,
        )
    finally:
        if saved is None:
            sys.modules.pop(_PKG + '.agent_engine', None)
        else:
            sys.modules[_PKG + '.agent_engine'] = saved
    return out, calls, host


def test_empty_reply_goes_to_the_next_provider():
    first = _Prov(1, 'A', '')
    second = _Prov(2, 'B', '{"periodo": "2025"}')
    out, calls, host = _run(first, [second, first])
    assert out['periodo'] == '2025'
    assert calls == ['A', 'B']
    assert len(host.side) == 2
    trace = [r for r in host.rows if r.get('tool_name') == 'skill_param_hybrid'][0]
    assert trace['prompt_data']['tried'] == ['A (empty reply)', 'B']
    assert trace['prompt_data']['provider'] == 'B'
    assert trace['provider_id'] == 2
    assert 'prompt_tokens' not in trace
    # Each spend says who spent it; the row shows what was asked and answered.
    assert [who for _usage, who in host.side] == ['A', 'B']
    assert trace['user_prompt'] == 'el año pasado'
    assert trace['result_data']['reply'] == '{"periodo": "2025"}'
    assert trace['result_data']['params']['periodo'] == '2025'


def test_a_parsed_reply_stops_the_chain():
    first = _Prov(1, 'A', '{"periodo": "2024"}')
    second = _Prov(2, 'B', '{"periodo": "2025"}')
    out, calls, _host = _run(first, [first, second])
    assert out['periodo'] == '2024'
    assert calls == ['A']


def test_unnamed_formal_token_still_goes_to_inference():
    first = _Prov(1, 'A', '{"periodo": "2024"}')
    out, calls, _host = _run(first, [first], args='2025')
    assert out['periodo'] == '2024'
    assert calls == ['A']


def test_all_named_skips_inference():
    first = _Prov(1, 'A', '{"periodo": "2024"}')
    out, calls, _host = _run(first, [first], args='periodo=2025')
    assert out['periodo'] == '2025'
    assert calls == []


def test_partly_named_goes_to_inference_and_the_name_wins():
    first = _Prov(1, 'A', '{"periodo": "2024"}')
    out, calls, _host = _run(first, [first], args='periodo=2025 algo')
    assert out['periodo'] == '2025'
    assert calls == ['A']


def test_no_provider_binds_by_shape():
    out, calls, _host = _run(None, [], args='2025')
    assert out['periodo'] == '2025'
    assert calls == []


def test_no_usable_reply_binds_by_shape():
    first = _Prov(1, 'A', '')
    out, calls, _host = _run(first, [first], args='2025')
    assert out['periodo'] == '2025'
    assert calls == ['A']


def test_turn_provider_leads_and_is_not_repeated():
    host = _Host([_Prov(2, 'B', ''), _Prov(1, 'A', '')])
    chain = host._param_provider_chain(_Prov(1, 'A', ''), 'chatboo')
    assert [p.name for p in chain] == ['A', 'B']


def test_parser_chain_goes_before_the_turn_provider():
    turn = _Prov(1, 'Chat', '')
    parser = _Prov(3, 'Light', '', needs=('parser',))
    both = _Prov(4, 'Both', '', needs=('parser', 'conversation'))
    host = _Host([parser, both, turn])
    chain = host._param_provider_chain(turn, 'chatboo')
    assert [p.name for p in chain] == ['Light', 'Both', 'Chat']


def test_parser_answers_and_the_chat_provider_is_not_asked():
    turn = _Prov(1, 'Chat', '{"periodo": "2024"}')
    parser = _Prov(3, 'Light', '{"periodo": "2023"}', needs=('parser',))
    out, calls, _host = _run(turn, [parser, turn])
    assert out['periodo'] == '2023'
    assert calls == ['Light']


def test_a_silent_parser_falls_back_to_the_conversation_chain():
    turn = _Prov(1, 'Chat', '{"periodo": "2024"}')
    parser = _Prov(3, 'Light', '', needs=('parser',))
    out, calls, _host = _run(turn, [parser, turn])
    assert out['periodo'] == '2024'
    assert calls == ['Light', 'Chat']


def test_a_turn_of_side_calls_only_is_charged_to_the_one_who_spent_it():
    """The close row carries the tokens; the provider's monthly spend reads it."""
    import ast
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / 'common' / 'utils'
    tree = ast.parse((root / 'agent_engine.py').read_text(encoding='utf-8'))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'AgentEngine')
    fns = [n for n in cls.body if isinstance(n, ast.FunctionDef)
           and n.name in ('_accumulate_side_usage', '_side_spender')]

    def add_usage(a, b):
        out = dict(a or {})
        for k, v in (b or {}).items():
            out[k] = (out.get(k) or 0) + v
        return out

    ns = {'normalize_usage': dict, 'note_turn_side_usage': lambda piece: None,
          'add_usage': add_usage}
    exec(compile(ast.Module(body=fns, type_ignores=[]), 'engine', 'exec'), ns)

    class Host:
        _accumulate_side_usage = ns['_accumulate_side_usage']
        _side_spender = ns['_side_spender']

    haiku = _Prov(17, 'Parser', '')
    host = Host()
    host._accumulate_side_usage({'prompt_tokens': 676, 'completion_tokens': 253}, provider=haiku)
    assert host._side_spender(host._turn_side_usage) is haiku
    # A spend nobody owns: the row cannot charge it to one provider.
    host._accumulate_side_usage({'prompt_tokens': 5, 'completion_tokens': 1})
    assert host._side_spender(host._turn_side_usage) is None
    close = (root / 'engine_presentation.py').read_text(encoding='utf-8')
    close = close.split('def _log_side_usage_close', 1)[1].split('\n    def ', 1)[0]
    assert 'provider_id=spender.id if spender is not None else None' in close
