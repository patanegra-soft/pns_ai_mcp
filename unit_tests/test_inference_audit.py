# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Transparent LLM usage logging gate."""
from __future__ import annotations

from pathlib import Path

import pytest
from _load_addon import engine_source

_ROOT = Path(__file__).resolve().parents[1]


def test_inference_audit_module_exports_context_manager():
    src = (_ROOT / 'common' / 'utils' / 'inference_audit.py').read_text(encoding='utf-8')
    assert 'def inference_audit' in src
    assert 'def record_inference_usage' in src
    assert 'def flush' in src
    assert "log_mode == 'accumulate'" in src
    flush = src.split('def flush')[1].split('def get_inference_audit')[0]
    assert 'new_turn_id' in flush
    assert 'turn_step=1' in flush


def test_spoken_fields_opens_its_own_turn():
    src = (_ROOT / 'common' / 'utils' / 'spoken_fields.py').read_text(encoding='utf-8')
    body = src.split('def split_sentence')[1]
    assert 'inference_audit' in body
    assert "endpoint='spoken_fields'" in body


def test_a_photo_is_parts_on_the_user_message():
    src = engine_source()
    assert 'def llm_completion_for_agent' in src
    helper = src.split('def llm_completion_for_agent')[1].split(
        'def _resolve_direct_return',
    )[0]
    assert 'json_mode=False' in helper
    assert 'disable_thinking=disable_thinking' in helper
    short = src.split('def llm_json_completion_result')[1].split(
        'def llm_json_completion(',
    )[0]
    assert 'chat_completion' in short
    assert 'disable_thinking' in short
    assert "protocol == 'anthropic'" not in short
    driver = (
        _ROOT / 'common' / 'lib' / 'llm' / 'drivers' / 'openai_driver.py'
    ).read_text(encoding='utf-8')
    assert 'image_url' in driver.split('def _with_images')[1].split('def _stt_model')[0]


def test_llm_json_completion_hooks_audit():
    src = engine_source()
    assert 'def _audit_llm_json_result' in src
    assert 'record_inference_usage' in src


def test_log_row_is_the_turn_door_without_llm():
    """Hosts write door events here. They do not call create_log_entry."""
    src = engine_source()
    body = src.split('def log_row')[1].split('\n    def ')[0]
    assert '_begin_turn' in body
    assert '_mcp_log' in body
    assert 'run_stream' not in body
    assert 'chat_completion' not in body
    assert 'self.env[\'ai.log\']' not in body


def test_ai_log_has_cost_usd_field():
    src = (_ROOT / 'common' / 'models' / 'ai_log.py').read_text(encoding='utf-8')
    assert 'cost_usd = fields.Float' in src
    assert 'cost_display = fields.Char' in src
    assert 'def _compute_cost_display' in src
    assert 'format_cost_label' in src
    assert 'usage=None' in src


def test_ai_log_user_usage_summary_method():
    src = (_ROOT / 'common' / 'models' / 'ai_log.py').read_text(encoding='utf-8')
    assert 'def get_user_usage_summary' in src
    assert 'domain=None' in src
    assert 'expression.AND' in src
    assert 'read_group' in src
    assert 'spend_label' in src
    assert "'filtered'" in src
    assert '_USAGE_SUMMARY_EXCLUDE_ENDPOINTS' in src
    # Extract the exclude tuple body and check round endpoints only.
    block = src.split('_USAGE_SUMMARY_EXCLUDE_ENDPOINTS = (', 1)[1].split(')', 1)[0]
    assert 'llm_orchestration' in block
    assert 'llm_response' in block
    assert 'orchestration_summary' not in block


def test_metering_doc_no_child_rows_rule():
    path = _ROOT / 'docs' / 'llm_usage_metering.md'
    if not path.is_file():
        pytest.skip('internal docs are not in this tree')
    doc = path.read_text(encoding='utf-8')
    assert 'sin filas hijas' in doc.lower() or 'no child' in doc.lower()
    assert '_accumulate_side_usage' in doc
    assert 'orchestration_summary' in doc
    assert 'inference_audit' in doc


def test_direct_turn_writes_its_side_spend_once():
    pres = (_ROOT / 'common' / 'utils' / 'engine_presentation.py').read_text(encoding='utf-8')
    done = pres.split('def _done_event(', 1)[1].split('\n    def ', 1)[0]
    assert '_log_side_usage_close(' in done
    close = pres.split('def _log_side_usage_close(', 1)[1].split('\n    def ', 1)[0]
    assert "tool_name='orchestration_summary'" in close
    assert '_side_close_logged_turn' in close


def test_skill_param_trace_row_carries_no_spend():
    src = (_ROOT / 'common' / 'utils' / 'engine_skills.py').read_text(encoding='utf-8')
    row = src.split("tool_name='skill_param_hybrid'", 1)[1].split('except Exception', 1)[0]
    assert 'prompt_tokens' not in row
    assert 'total_tokens' not in row


def test_execution_engine_usage_display_context():
    src = (_ROOT / 'common' / 'models' / 'ai_execution_engine.py').read_text(encoding='utf-8')
    assert 'def get_usage_display_context' in src


def test_llm_response_row_keeps_the_tool_call_arguments():
    import ast
    import json

    src = (_ROOT / 'common' / 'models' / 'ai_execution_engine.py').read_text(encoding='utf-8')
    tree = ast.parse(src)
    fn = next(
        n for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == '_logged_tool_calls'
    )
    scope = {'json': json}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), 'x', 'exec'), scope)
    code = "rows = env['res.partner'].search([])\nresult = rows"
    calls = scope['_logged_tool_calls']([
        {'id': 'a', 'function': {'name': 'relaxaicode',
                                 'arguments': json.dumps({'code': code})}},
        {'id': 'b', 'function': {'name': 'other', 'arguments': '{broken'}},
    ])
    assert calls == [
        {'name': 'relaxaicode', 'arguments': {'code': code}},
        {'name': 'other', 'arguments': '{broken'},
    ]
    row = src.split('def _log_provider_llm_response', 1)[1].split('\n    def ', 1)[0]
    assert "result_data['tool_calls'] = calls" in row
    assert 'preview[:400]' not in row
    inference = src.split('def _log_provider_inference', 1)[1].split('\n    def ', 1)[0]
    assert 'tool_calls=tool_calls,' in inference
    loop = (_ROOT / 'common' / 'utils' / 'engine_tool_loop.py').read_text(encoding='utf-8')
    assert 'tool_calls=list(tool_calls_buffer.values()),' in loop


def test_single_llm_row_keeps_what_was_sent_and_answered():
    src = (_ROOT / 'common' / 'models' / 'ai_execution_engine.py').read_text(encoding='utf-8')
    body = src.split('def _log_llm_inference', 1)[1].split('\n    def ', 1)[0]
    assert 'prompt_data=None' in body and 'result_data=None' in body
    assert 'prompt_data=prompt_data' in body
    assert 'result_data=result_data' in body


def test_execution_engine_log_llm_inference_gate():
    src = (_ROOT / 'common' / 'models' / 'ai_execution_engine.py').read_text(encoding='utf-8')
    assert 'def _log_llm_inference' in src
    assert 'usage=piece' in src
    assert 'OpenAPI gen %s' not in src
    assert '%d tok' not in src
    assert 'USD %.4f' not in src
    assert 'content_preview' in src.split('def _log_llm_inference', 1)[1][:1800]
    assert '[:5000]' in src.split('def _log_llm_inference', 1)[1][:2200]
    audit = (_ROOT / 'common' / 'utils' / 'inference_audit.py').read_text(
        encoding='utf-8')
    assert "content_preview or '')[:5000]" in audit
    assert "content_preview or '')[:400]" not in audit


def test_usage_log_fields_helper():
    from _load_addon import load_module

    u = load_module('llm_usage', 'utils', 'llm_usage.py')
    pt, ct, tt, cost = u.usage_log_fields({
        'prompt_tokens': 10,
        'completion_tokens': 5,
        'cost': 0.001,
    })
    assert pt == 10
    assert ct == 5
    assert tt == 15
    assert cost == 0.001
