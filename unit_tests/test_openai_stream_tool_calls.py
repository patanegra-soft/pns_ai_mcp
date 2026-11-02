# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Streamed tool calls come back whole, with what the provider asked to get back."""
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / 'common'))

from lib.llm.drivers.openai_driver import (  # noqa: E402
    OpenAIDriver,
    openai_max_output_tokens_key,
)

_SIG = {'google': {'thought_signature': 'c2ln'}}


def _calls(monkeypatch, deltas):
    import requests

    class _Stream:
        status_code = 200
        text = ''

        def iter_lines(self):
            for delta in deltas:
                yield b'data: ' + json.dumps({'choices': [{'delta': {'tool_calls': delta}}]}).encode()
            yield b'data: [DONE]'

        def close(self):
            return None

    monkeypatch.setattr(requests, 'post', lambda *a, **k: _Stream())
    driver = OpenAIDriver()
    driver.initialize({
        'protocol': 'openai',
        'endpoint': 'https://example.test/v1/chat/completions',
        'api_key': 'k',
        'model_name': 'm',
    })
    pieces = list(driver.iter_chat([{'role': 'user', 'content': 'hola'}], tools=[{'type': 'function'}]))
    return pieces[-1]['message'].get('tool_calls')


def test_a_whole_call_without_index_keeps_its_signature(monkeypatch):
    calls = _calls(monkeypatch, [[{
        'id': 'call_1', 'type': 'function', 'extra_content': _SIG,
        'function': {'name': 'relaxaicode', 'arguments': '{"code": "x"}'},
    }]])
    assert calls == [{
        'id': 'call_1', 'type': 'function', 'extra_content': _SIG,
        'function': {'name': 'relaxaicode', 'arguments': '{"code": "x"}'},
    }]


def test_a_classic_chunked_call_is_unchanged(monkeypatch):
    calls = _calls(monkeypatch, [
        [{'index': 0, 'id': 'call_1', 'type': 'function', 'function': {'name': 'relax', 'arguments': ''}}],
        [{'index': 0, 'function': {'name': 'aicode', 'arguments': '{"co'}}],
        [{'index': 0, 'function': {'arguments': 'de": 1}'}}],
    ])
    assert calls == [{
        'id': 'call_1', 'type': 'function',
        'function': {'name': 'relaxaicode', 'arguments': '{"code": 1}'},
    }]


def test_a_signature_in_a_later_delta_is_kept(monkeypatch):
    calls = _calls(monkeypatch, [
        [{'index': 0, 'id': 'call_1', 'function': {'name': 'relaxaicode', 'arguments': '{}'}}],
        [{'index': 0, 'extra_content': {'google': {'other': 1}}}],
        [{'index': 0, 'extra_content': _SIG}],
    ])
    assert calls[0]['id'] == 'call_1'
    assert calls[0]['function'] == {'name': 'relaxaicode', 'arguments': '{}'}
    assert calls[0]['extra_content'] == {'google': {'other': 1, 'thought_signature': 'c2ln'}}


def test_two_calls_without_index_stay_apart(monkeypatch):
    calls = _calls(monkeypatch, [
        [{'id': 'call_1', 'extra_content': _SIG, 'function': {'name': 'a', 'arguments': '{"x"'}}],
        [{'function': {'arguments': ': 1}'}}],
        [{'id': 'call_2', 'function': {'name': 'b', 'arguments': '{}'}}],
        [{'id': 'call_1', 'function': {'arguments': ''}}],
    ])
    assert [c['id'] for c in calls] == ['call_1', 'call_2']
    assert calls[0]['function'] == {'name': 'a', 'arguments': '{"x": 1}'}
    assert calls[0]['extra_content'] == _SIG
    assert calls[1]['function'] == {'name': 'b', 'arguments': '{}'}
    assert 'extra_content' not in calls[1]


def test_openai_max_output_tokens_key():
    assert openai_max_output_tokens_key('gpt-4o') == 'max_tokens'
    assert openai_max_output_tokens_key('gpt-5') == 'max_completion_tokens'
    assert openai_max_output_tokens_key('o1-mini') == 'max_completion_tokens'
    assert openai_max_output_tokens_key('o3') == 'max_completion_tokens'
