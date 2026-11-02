# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""A router's «Provider returned error» carries the reason of the model behind."""
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / 'common'))

from lib.llm.drivers.openai_driver import _http_error_message  # noqa: E402


class _Resp:
    def __init__(self, code, body):
        self.status_code = code
        self._body = body
        self.text = json.dumps(body)

    def json(self):
        return self._body


def test_router_error_keeps_what_the_model_behind_said():
    raw = json.dumps({'error': {'message': "Unsupported format 'webm'"}})
    resp = _Resp(400, {'error': {
        'code': 400,
        'message': 'Provider returned error',
        'metadata': {'raw': raw, 'provider_name': 'OpenAI'},
    }})
    assert _http_error_message(resp) == (
        "Provider returned error: Unsupported format 'webm' (OpenAI)"
    )


def test_raw_that_is_not_json_is_kept_as_text():
    resp = _Resp(502, {'error': {
        'message': 'Provider returned error',
        'metadata': {'raw': 'upstream timeout'},
    }})
    assert _http_error_message(resp) == 'Provider returned error: upstream timeout'


def test_plain_error_is_unchanged():
    resp = _Resp(401, {'error': {'message': 'Invalid key'}})
    assert _http_error_message(resp) == 'Invalid key'
