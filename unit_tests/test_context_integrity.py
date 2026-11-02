# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Context integrity: the same order must not live twice in opposite directions.

Pairs we already got bitten by. Not a reader of every rule.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from _load_addon import runtime_source, validators_source

_ROOT = Path(__file__).resolve().parents[1]


def _text(*parts):
    return (_ROOT.joinpath(*parts)).read_text(encoding='utf-8')


def _doc(*parts):
    path = _ROOT.joinpath('docs', *parts)
    if not path.is_file():
        pytest.skip('internal docs are not in this tree')
    return path.read_text(encoding='utf-8')


def test_skill_launch_matches_the_engine():
    prompt = _text('common', 'ai', 'contexts', 'core', 'system_prompt.xml')
    assert 'own trigger phrases (one match)' in prompt
    assert 'Slash procedures run only via /command' not in prompt
    # The reject texts the model reads after a sandbox refusal say the same.
    assert 'copy another skill' in prompt
    assert 'Query the business models' in prompt
    for engine in (validators_source(), _text('common', 'utils', 'error_ux.py')):
        assert 'run only via' not in engine
        assert "own trigger phrases; the model does not launch it" in engine
        assert 'copy another skill' in engine
        assert 'query the business models' in engine


def test_skill_launch_docs_match_the_engine():
    norma = _doc('skills_norma_creacion.md')
    assert 'triggers` está **obsoleto**' not in norma
    assert 'Una sola coincidencia corre el código' in norma
    decision = _doc('decisions', 'contexto_vs_datos_runtime.md')
    assert 'menú `/` en el chat Odoo; el endpoint MCP no las corre' not in decision
    modes = _doc('arquitectura_modos.md')
    assert 'Se invocan solo con `/comando`' not in modes
    assert 'frases `triggers` del propio skill' in modes


def test_short_answer_cap_yields_to_a_report_outline():
    prompt = _text('common', 'ai', 'contexts', 'core', 'system_prompt.xml')
    assert '150 words' in prompt
    assert 'unless the user asks for detail, or this turn has report_outline' in prompt


def test_unresolved_write_asks_instead_of_inspecting():
    """A missing name or an unstated choice is a question, not another probe."""
    prompt = _text('common', 'ai', 'contexts', 'core', 'system_prompt.xml')
    assert 'UNRESOLVED WRITE' in prompt
    assert 'Do not inspect more models' in prompt
    assert 'TARGET model of that op=create' in prompt
    assert 'not a license to inspect wizards' in prompt
    engine = _text('common', 'utils', 'error_ux.py')
    assert 'INSPECT_SPIN_AFTER = 2' in engine
    assert 'you already inspected' in engine
    loop = _text('common', 'utils', 'engine_tool_run.py')
    assert 'inspect_spin_nudge' in loop
    assert "return_mode') == 'inspect_result'" in loop


def test_captured_skills_always_have_parameters():
    """Prompt and rewrite say the same: always params, required never in Code."""
    prompt = _text('common', 'ai', 'contexts', 'core', 'system_prompt.xml')
    runtime = runtime_source()
    assert 'a captured skill always has parameters' in prompt
    assert 'Required keys never get a Code fallback' in prompt
    assert 'if the slash takes args, read them' not in prompt
    assert 'A required key has no fallback in the Code' in runtime
    assert 'second-level default in the Code' in runtime


def test_captured_skills_norma_matches_the_prompt():
    norma = _doc('skills_norma_creacion.md')
    assert 'se crean con parámetros' in norma
    assert 'rellenarse nunca en el Code' in norma


def test_delivery_doc_matches_the_prompt():
    prompt = _text('common', 'ai', 'contexts', 'core', 'system_prompt.xml')
    assert 'inspect_result is only for a probe' in prompt
    decision = _doc('decisions', 'retorno_directo.md')
    assert 'explicar / argumentar / recomendar / mail → `inspect_result`' not in decision
    assert 'report_outline' in decision
