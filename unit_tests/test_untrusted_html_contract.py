# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""HTML contract: sandbox vs server-side render."""
from __future__ import annotations

from _load_addon import load_module

contract = load_module(
    'untrusted_html_contract', 'utils', 'untrusted_html_contract.py',
)
reject = contract.reject_untrusted_formatted_text


def test_reject_llm_self_attested_server_side_python():
    result = {
        'formatted_text': '<table>evil</table>',
        '__fmt_type__': 'server_side_python',
    }
    assert reject(result) is True
    assert 'formatted_text' not in result
    assert result.get('__untrusted_html_preview__')


def test_preserve_server_rendered_html_after_attach():
    """maybe_attach + __return_direct__ must keep the server-rendered table."""
    result = {
        'data': [{'name': 'A'}],
        'summary': 'Test',
        'formatted_text': '<table>ok</table>',
        '__fmt_type__': 'server_side_python',
        '__return_direct__': True,
    }
    assert reject(result, after_server_render=True) is False
    assert result.get('formatted_text') == '<table>ok</table>'
    assert result.get('__return_direct__') is True
    assert '__untrusted_html_preview__' not in result
    assert not result.get('__force_continue__')
