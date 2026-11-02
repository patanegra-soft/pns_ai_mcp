# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""OpenRouter is its own protocol. Voice reports spend. Chat stays completions."""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / 'common'))

from lib.llm.drivers import get_llm_driver, list_llm_driver_types  # noqa: E402
from lib.llm.drivers.base import LLMDriver  # noqa: E402
from lib.llm.drivers.anthropic_driver import AnthropicDriver  # noqa: E402
from lib.llm.drivers.openai_driver import OpenAIDriver  # noqa: E402
from lib.llm.drivers.openrouter_driver import OpenRouterDriver  # noqa: E402


class _Resp:
    def __init__(self, code, body, text=''):
        self.status_code = code
        self._body = body
        self.text = text or str(body)

    def json(self):
        return self._body


def _driver(stt='chat'):
    driver = OpenRouterDriver()
    driver.initialize({
        'protocol': 'openrouter',
        'endpoint': 'https://gateway.example/api/v1/chat/completions',
        'api_key': 'k',
        'model_name': 'whisper-1',
        'stt_support': stt,
    })
    return driver


def test_the_reply_arrives_in_pieces(monkeypatch):
    import requests

    class _Stream:
        status_code = 200
        text = ''

        def iter_lines(self):
            yield b'data: {"choices":[{"delta":{"content":"Miro "}}]}'
            yield b'data: {"choices":[{"delta":{"content":"el ticket"}}]}'
            yield b'data: [DONE]'

        def close(self):
            return None

    monkeypatch.setattr(requests, 'post', lambda *a, **k: _Stream())
    driver = OpenAIDriver()
    driver.initialize({
        'protocol': 'openai',
        'endpoint': 'https://example.test/v1/chat/completions',
        'api_key': 'k',
        'model_name': 'gpt-4o-mini',
    })
    pieces = list(driver.iter_chat(
        [{'role': 'user', 'content': 'hola'}],
    ))
    assert [p.get('text') for p in pieces if p.get('text')] == ['Miro ', 'el ticket']
    assert pieces[-1]['done'] is True
    assert pieces[-1]['message']['content'] == 'Miro el ticket'


def test_reasoning_deltas_are_not_the_user_reply(monkeypatch):
    import requests

    class _Stream:
        status_code = 200
        text = ''

        def iter_lines(self):
            yield b'data: {"choices":[{"delta":{"reasoning":"plan interno"}}]}'
            yield b'data: {"choices":[{"delta":{"reasoning_content":" mas"}}]}'
            yield b'data: {"choices":[{"delta":{"content":[{"type":"thinking","text":"oculto"},{"type":"text","text":"Hola"}]}}]}'
            yield b'data: [DONE]'

        def close(self):
            return None

    monkeypatch.setattr(requests, 'post', lambda *a, **k: _Stream())
    driver = OpenAIDriver()
    driver.initialize({
        'protocol': 'openai',
        'endpoint': 'https://example.test/v1/chat/completions',
        'api_key': 'k',
        'model_name': 'gpt-4o-mini',
    })
    pieces = list(driver.iter_chat(
        [{'role': 'user', 'content': 'hola'}],
    ))
    assert [p.get('text') for p in pieces if p.get('text')] == ['Hola']
    assert [p.get('reasoning') for p in pieces if p.get('reasoning')] == [
        'plan interno', ' mas', 'oculto',
    ]
    assert pieces[-1]['message']['content'] == 'Hola'


def test_stt_does_not_invent_a_model():
    src = (
        _ROOT / 'common' / 'lib' / 'llm' / 'drivers' / 'openai_driver.py'
    ).read_text(encoding='utf-8')
    block = src.split('def _stt_model')[1].split('\n    def ')[0]
    assert 'whisper' not in block.lower()
    assert 'transcribe' not in block.lower()
    assert 'return (self.model_name or \'\').strip()' in block.replace('"', "'")
    probe = src.split('def probe_stt')[1].split('\n    def ')[0]
    assert 'whisper' not in probe.lower()
    init = src.split('def initialize')[1].split('def driver_name')[0]
    assert 'gpt-4o-mini' not in init


def test_openrouter_models_url_asks_for_every_output_shape():
    from utils.model_catalogue import listing_url
    wrapped = listing_url(
        OpenAIDriver().models_url(OpenRouterDriver.default_endpoint)
    )
    assert 'output_modalities=all' in wrapped
    assert 'limit=1000' in wrapped
    openai = listing_url(
        OpenAIDriver().models_url(
            'https://api.openai.com/v1/chat/completions',
        )
    )
    assert 'output_modalities' not in openai


def test_choosing_openrouter_fills_the_fixed_address():
    assert OpenRouterDriver.default_endpoint == (
        'https://openrouter.ai/api/v1/chat/completions'
    )
    src = (_ROOT / 'common' / 'models' / 'ai_provider.py').read_text(encoding='utf-8')
    onchange = src.split('def _onchange_protocol_ticks', 1)[1].split('\n    def ', 1)[0]
    assert 'default_endpoint' in onchange
    assert 'self.endpoint = fixed' in onchange
    guide = src.split('def _compute_endpoint_setup_guide', 1)[1].split('\n    def ', 1)[0]
    assert "provider.protocol == 'openrouter'" in guide
    assert 'OpenRouterDriver.default_endpoint' in guide


def test_openrouter_is_a_sibling_protocol():
    kinds = list_llm_driver_types()
    assert 'ollama' not in kinds
    for name in ('openai', 'openrouter', 'anthropic', 'systemone'):
        assert name in kinds
    assert isinstance(get_llm_driver('openrouter'), OpenRouterDriver)
    assert not isinstance(get_llm_driver('openai'), OpenRouterDriver)
    assert OpenRouterDriver.__mro__[1] is OpenAIDriver
    assert AnthropicDriver.transcribe is LLMDriver.transcribe


def test_transcription_returns_usage_in_one_call(monkeypatch):
    import requests
    calls = []

    def post(url, **kw):
        calls.append({'url': url, **kw})
        return _Resp(200, {
            'choices': [{'message': {'content': 'hola'}}],
            'usage': {'cost': 0.02, 'total_tokens': 4},
        })

    monkeypatch.setattr(requests, 'post', post)
    out = _driver().transcribe(
        b'abc', filename='audio.webm', mime='audio/webm;codecs=opus',
        language='es_ES',
    )
    assert out['body']['text'] == 'hola'
    assert out['body']['usage']['cost'] == 0.02
    assert len(calls) == 1
    sent = calls[0]['json']
    assert sent['model'] == 'whisper-1'
    audio = sent['messages'][0]['content'][-1]['input_audio']
    assert audio['format'] == 'webm'
    assert calls[0]['url'].endswith('/chat/completions')
    assert calls[0]['timeout'] == 60


def test_the_provider_model_is_sent_as_written(monkeypatch):
    import requests
    sent = {}

    def post(url, **kw):
        sent['url'] = url
        sent['model'] = kw['json']['model']
        return _Resp(200, {'choices': [{'message': {'content': 'hola'}}]})

    monkeypatch.setattr(requests, 'post', post)
    driver = _driver()
    driver.initialize({
        'protocol': 'openrouter',
        'endpoint': 'https://gateway.example/api/v1/chat/completions',
        'api_key': 'k',
        'model_name': 'openai/gpt-audio-mini',
        'stt_support': 'chat',
    })
    driver.transcribe(b'abc', filename='audio.webm', mime='audio/webm')
    assert sent['model'] == 'openai/gpt-audio-mini'
    assert sent['url'].endswith('/chat/completions')


def test_a_catalog_model_is_left_as_written(monkeypatch):
    import requests
    driver = _driver()
    driver.initialize({
        'protocol': 'openrouter',
        'endpoint': 'https://gateway.example/api/v1/chat/completions',
        'api_key': 'k',
        'model_name': 'vendor/gpt-4o-mini-transcribe',
        'stt_support': 'chat',
    })
    sent = {}

    def post(url, **kw):
        sent['model'] = kw['json']['model']
        return _Resp(200, {'text': 'hola'})

    monkeypatch.setattr(requests, 'post', post)
    driver.transcribe(b'abc', filename='audio.webm', mime='audio/webm')
    assert sent['model'] == 'vendor/gpt-4o-mini-transcribe'


def test_a_timeout_is_not_a_second_call(monkeypatch):
    import requests
    calls = []

    def post(url, **kw):
        calls.append(1)
        raise requests.Timeout('slow')

    monkeypatch.setattr(requests, 'post', post)
    out = _driver().transcribe(b'abc', filename='audio.webm', mime='audio/webm')
    assert len(calls) == 1
    assert out.get('error')
    assert 'shape_rejected' not in out


def test_a_rejected_body_does_not_rewrite_the_url(monkeypatch):
    import requests
    calls = []

    def post(url, **kw):
        calls.append(url)
        return _Resp(400, {'error': {'message': 'Invalid request'}})

    monkeypatch.setattr(requests, 'post', post)
    out = _driver().transcribe(b'abc', filename='audio.webm', mime='audio/webm')
    assert len(calls) == 1
    assert calls[0].endswith('/chat/completions')
    assert 'transcriptions' not in calls[0]
    assert out.get('error')
    assert 'body' not in out


def test_the_probe_picks_file_transcriptions_when_chat_rejects(monkeypatch):
    import requests
    calls = []

    def post(url, **kw):
        calls.append('json' if 'json' in kw else 'file')
        if 'json' in kw:
            return _Resp(400, {'error': {'message': 'Invalid request'}})
        return _Resp(200, {'text': 'hola'})

    monkeypatch.setattr(requests, 'post', post)
    assert _driver('unknown').probe_stt(timeout=8) == 'transcriptions'
    assert calls == ['json', 'file']


def test_the_chat_verb_is_told_to_transcribe_not_to_answer(monkeypatch):
    import requests
    sent = {}

    def post(url, **kw):
        sent.update(kw['json'])
        return _Resp(200, {'choices': [{'message': {'content': 'hola'}}]})

    monkeypatch.setattr(requests, 'post', post)
    _driver().transcribe(
        b'abc', filename='audio.webm', mime='audio/webm',
        prompt='Friday breakfast colleagues',
    )
    content = sent['messages'][0]['content']
    assert content[0]['type'] == 'text'
    assert content[-1]['type'] == 'input_audio'
    text = content[0]['text']
    assert text.lower().startswith('transcribe')
    assert 'transcript only' in text
    # The vocabulary comes after the order, never as the only text.
    assert text.index('Friday breakfast') > text.index('transcript only')
    assert sent['temperature'] == 0


def test_the_probe_clip_is_long_enough_to_be_audio():
    from lib.llm.drivers.openai_driver import _silent_wav
    import struct
    clip = _silent_wav()
    rate = struct.unpack('<I', clip[24:28])[0]
    block = struct.unpack('<H', clip[32:34])[0]
    data_len = struct.unpack('<I', clip[40:44])[0]
    seconds = data_len / float(rate * block)
    # OpenAI-style transcribers reject < 0.1 s with a 400; the probe
    # would read that as "no speech API" and bench the provider.
    assert seconds >= 0.5
    assert len(clip) == 44 + data_len


def test_a_cached_file_verb_does_not_post_chat(monkeypatch):
    import requests
    calls = []

    def post(url, **kw):
        calls.append(url)
        return _Resp(200, {'text': 'hola'})

    monkeypatch.setattr(requests, 'post', post)
    out = _driver('transcriptions').transcribe(
        b'abc', filename='audio.webm', mime='audio/webm',
    )
    assert len(calls) == 1
    assert calls[0].endswith('/audio/transcriptions')
    assert out['body']['text'] == 'hola'
    assert out.get('stt') == 'transcriptions'
