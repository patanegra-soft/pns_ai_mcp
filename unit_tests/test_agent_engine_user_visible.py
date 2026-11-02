# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Structural anti-noise: progress as status, dumps out of the chat bubble."""
from __future__ import annotations

from pathlib import Path

from _load_addon import load_module

text = load_module('agent_stream_text', 'utils', 'agent_stream_text.py')


def test_tool_round_never_writes_chat_bubble():
    assert text.user_visible_round_text('Comparando A y B', has_tool_calls=True) == ''
    assert text.user_visible_round_text('x' * 500, has_tool_calls=True) == ''


def test_short_progress_becomes_status():
    assert text.pretool_progress_status('Comparando A y B') == 'Comparando A y B'
    assert text.pretool_progress_status('  Buscando un patrón en ventas  ') == (
        'Buscando un patrón en ventas'
    )
    # A single sentence with a final period is still progress.
    assert text.pretool_progress_status('Comparando A y B.') == 'Comparando A y B.'


def test_dump_shaped_pretool_is_not_status():
    assert text.pretool_progress_status('{"data": [{"id": 1}]}') is None
    assert text.pretool_progress_status('```\nid,name\n1,a\n```') is None
    assert text.pretool_progress_status('a\nb\nc\nd') is None
    assert text.pretool_progress_status('x' * 200) is None
    # Several sentences = detail, not a progress line.
    assert text.pretool_progress_status(
        'Paso uno. Paso dos. Paso tres y más detalle.'
    ) is None


def test_final_answer_passes_through():
    answer = 'resultado útil para el usuario'
    assert text.user_visible_round_text(answer, has_tool_calls=False) == answer


def test_narrative_stub_is_progress_shaped():
    """A one-line «still writing» close must not pass as the user answer."""
    stub = 'En elaboración del relato \U0001F61E'
    assert text.pretool_progress_status(stub) == stub
    assert text.should_block_progress_as_final(
        stub,
        has_tool_calls=False,
        has_pending_retry=True,
        rounds_left=True,
    )
    assert text.should_block_progress_as_final(
        stub,
        has_tool_calls=False,
        has_pending_retry=False,
        rounds_left=True,
        has_hidden_reasoning=True,
    )
    assert not text.should_block_progress_as_final(
        stub,
        has_tool_calls=False,
        has_pending_retry=False,
        rounds_left=True,
        has_hidden_reasoning=False,
    )


def test_block_progress_as_final_after_tool_retry():
    """R5YZ: «vuelvo a generar el mapa» without tool_calls must not end the turn."""
    msg = (
        'Corrijo el orden de la ruta (claves de ordenación válidas) '
        'y vuelvo a generar el mapa.'
    )
    assert text.should_block_progress_as_final(
        msg,
        has_tool_calls=False,
        has_pending_retry=True,
        rounds_left=True,
    )
    # With tools, or without pending retry, or no rounds left → do not block.
    assert not text.should_block_progress_as_final(
        msg, has_tool_calls=True, has_pending_retry=True, rounds_left=True,
    )
    assert not text.should_block_progress_as_final(
        msg, has_tool_calls=False, has_pending_retry=False, rounds_left=True,
    )
    assert not text.should_block_progress_as_final(
        msg, has_tool_calls=False, has_pending_retry=True, rounds_left=False,
    )
    # Real final answer (not progress-shaped) after error may still close.
    longish = (
        'No he podido completar el mapa por un error de ordenación. '
        'Prueba de nuevo o pide menos paradas.'
    )
    assert text.pretool_progress_status(longish) is None
    assert not text.should_block_progress_as_final(
        longish,
        has_tool_calls=False,
        has_pending_retry=True,
        rounds_left=True,
    )


def test_block_no_tool_as_final_first_round():
    """NTU0/THKM: round 1 with tools and no tool_calls must not end the turn."""
    assert text.should_block_no_tool_as_final(
        has_tool_calls=False,
        is_first_round=True,
        rounds_left=True,
        has_tools=True,
    )
    # Progress one-liner on a work turn without a tool call still bounces.
    assert text.should_block_no_tool_as_final(
        has_tool_calls=False,
        is_first_round=True,
        rounds_left=True,
        has_tools=True,
        content='Looking the records up now.',
        user_message='list open invoices',
    )
    # Announced a schema tool name, never called it (NTU0).
    assert text.should_block_no_tool_as_final(
        has_tool_calls=False,
        is_first_round=True,
        rounds_left=True,
        has_tools=True,
        content='I will call safe_plan_request next.',
        tool_names=('safe_plan_request', 'relaxaicode'),
    )
    # Short finished prose (greeting / who-are-you) may close. No language list.
    assert not text.should_block_no_tool_as_final(
        has_tool_calls=False,
        is_first_round=True,
        rounds_left=True,
        has_tools=True,
        content='I am Chatboo, the assistant on this Odoo instance. '
                'PATANEGRA Soft created me.',
    )
    # Scope / limits list (under the 150-word protocol) must also close.
    # The old 500-char horn collapsed these to the greeting one-liner.
    scope = (
        'I can query this Odoo instance, list and summarise records, '
        'and offer PDF, Excel and Word from the turn icons. Slash skills '
        'run predefined procedures. Writes need your confirmation.\n\n'
        '- I stay inside your user permissions.\n'
        '- I do not invent records or amounts.\n'
        '- Off-topic requests get a short protest, then an answer.\n'
    ) * 3
    assert 500 < len(scope) < text._FINISHED_PROSE_MAX_CHARS
    assert not text.should_block_no_tool_as_final(
        has_tool_calls=False,
        is_first_round=True,
        rounds_left=True,
        has_tools=True,
        content=scope,
    )
    essay = 'Plan only. ' * 200
    assert len(essay) > text._FINISHED_PROSE_MAX_CHARS
    assert text.should_block_no_tool_as_final(
        has_tool_calls=False,
        is_first_round=True,
        rounds_left=True,
        has_tools=True,
        content=essay,
    )
    assert 'greeting one-liner' in text.NO_TOOL_FINAL_NUDGE
    assert 'scope/limits' in text.NO_TOOL_FINAL_NUDGE
    assert 'who-you-are' in text.NO_TOOL_FINAL_NUDGE
    assert 'agreed to what YOU just offered' in text.NO_TOOL_FINAL_NUDGE
    assert 'short assent' in text.NO_TOOL_FINAL_NUDGE
    assert 're-introduce' in text.NO_TOOL_FINAL_NUDGE
    hello = (
        'I am Chatboo, the assistant on this Odoo instance. '
        'PATANEGRA Soft created me.'
    )
    # Work-shaped utterance: greeting one-liner must not close the turn.
    assert text.user_turn_looks_like_work('sales last 12 months')
    assert text.user_turn_looks_like_work('export as pdf')
    assert text.user_turn_looks_like_work('/sys_info')
    assert text.user_turn_looks_like_work('list open invoices')
    assert not text.user_turn_looks_like_work('who are you?')
    assert not text.user_turn_looks_like_work('what can you do for me?')
    # Question-mark glyphs (inverted / fullwidth / Arabic), not only ASCII '?'.
    assert not text.user_turn_looks_like_work(
        'no entiendo ¿Qué es flattery en español¿'
    )
    assert not text.user_turn_looks_like_work('what is this？')
    assert not text.user_turn_looks_like_work('ما هذا؟')
    assert not text.should_block_no_tool_as_final(
        has_tool_calls=False,
        is_first_round=True,
        rounds_left=True,
        has_tools=True,
        content=(
            'Flattery is praise (sometimes excessive) to please or persuade. '
            'In the previous line, «flattery accepted» meant the compliment '
            'was taken.'
        ),
        user_message='no entiendo ¿Qué es flattery en español¿',
    )
    # Statement without a question glyph is still work-shaped.
    assert text.user_turn_looks_like_work(
        'esa empresa no la conoce nadie, eres demasiado bueno'
    )
    # Three tokens, no '?': work on its own — unless it answers the last ask.
    assert text.user_turn_looks_like_work('ah pues vale')
    assert not text.user_turn_looks_like_work(
        'ah pues vale',
        prior_assistant=['Want me to tell you about the mailbox?'],
    )
    assert text.user_turn_looks_like_work(
        'ah pues vale',
        prior_assistant=['Here is the partner list.'],
    )
    assert text.user_turn_looks_like_work(
        'sales last 12 months',
        prior_assistant=['What should I pull?'],
    )
    assert not text.should_block_no_tool_as_final(
        has_tool_calls=False,
        is_first_round=True,
        rounds_left=True,
        has_tools=True,
        content='Alright — I will start with what is in the mailbox.',
        user_message='ah pues vale',
        prior_assistant=['Want me to tell you about the mailbox?'],
    )
    assert text.should_block_no_tool_as_final(
        has_tool_calls=False,
        is_first_round=True,
        rounds_left=True,
        has_tools=True,
        content=hello,
        user_message='sales last 12 months',
    )
    # Same bubble as the previous assistant turn → parrot, bounce.
    assert text.is_prior_prose_echo(hello, [hello])
    assert text.should_block_no_tool_as_final(
        has_tool_calls=False,
        is_first_round=True,
        rounds_left=True,
        has_tools=True,
        content=hello,
        user_message='what can you do for me?',
        prior_assistant=[hello],
    )
    stream = Path(text.__file__).read_text(encoding='utf-8')
    assert 'quién' not in stream
    assert 'gráfico' not in stream
    assert 'apaisado' not in stream
    extract = (
        '## Offer 20898328\n\n'
        '| Field | Value |\n'
        '|---|---|\n'
        '| Issuer | Acme |\n\n'
        'Line 10 is the gantry. Line 20 is the hoist.\n'
    ) * 4
    assert len(extract) > text._STATUS_MAX_CHARS
    # File text already in the prompt: the extract is the answer, even if
    # the utterance cited pdf (work-shaped file token).
    assert not text.should_block_no_tool_as_final(
        has_tool_calls=False,
        is_first_round=True,
        rounds_left=True,
        has_tools=True,
        content=extract,
        user_message='transcribe the information in the pdf',
        inline_file_text=True,
    )
    assert not text.should_block_no_tool_as_final(
        has_tool_calls=False,
        is_first_round=True,
        rounds_left=True,
        has_tools=True,
        content=extract,
        user_message='what do you find in there?',
        inline_file_text=True,
    )
    # Without the flag, a pdf token still bounces (export / missing read).
    assert text.should_block_no_tool_as_final(
        has_tool_calls=False,
        is_first_round=True,
        rounds_left=True,
        has_tools=True,
        content=extract,
        user_message='export as pdf',
        inline_file_text=False,
    )
    # Progress one-liner with a file still bounces (announced work, no tool).
    assert text.should_block_no_tool_as_final(
        has_tool_calls=False,
        is_first_round=True,
        rounds_left=True,
        has_tools=True,
        content='Looking the records up now.',
        user_message='list open invoices',
        inline_file_text=True,
    )
    # Greeting + file is not a file answer; work utterance still bounces.
    assert text.should_block_no_tool_as_final(
        has_tool_calls=False,
        is_first_round=True,
        rounds_left=True,
        has_tools=True,
        content=hello,
        user_message='sales last 12 months',
        inline_file_text=True,
    )
    # T9JM: follow-up after a delivered body, no file on this turn.
    prior_offer = (
        'Commercial offer 20898328 for a mobile gantry. '
        'Capacity 3000 kg, span 4 m, height under beam 3.5 m. '
    ) * 20
    assert len(prior_offer) > text._FINISHED_PROSE_MAX_CHARS
    assert text.prior_turn_has_delivered_body([prior_offer])
    assert not text.prior_turn_has_delivered_body([hello])
    specs = (
        '**Mobile gantry under load** — ref. **PRC 3000kg-4m-3,5m**\n\n'
        '| Field | Value |\n'
        '|---|---|\n'
        '| Capacity | **3.000 kg** |\n'
        '| Span | **4.000 mm** |\n'
        '| Height under beam | **3.500 mm** |\n'
        '| Finish | **C2** interior, **RAL 1021** |\n'
        '| Wheels | Polyamide core; 2 swivel + 2 braked |\n'
        '| Design | FEM group 4 |\n'
        '| Documentation | CE declaration and user manual |\n'
    )
    assert len(specs) > text._STATUS_MAX_CHARS
    assert not text.should_block_no_tool_as_final(
        has_tool_calls=False,
        is_first_round=True,
        rounds_left=True,
        has_tools=True,
        content=specs,
        user_message='give me the technical specs of the mobile gantry',
        prior_assistant=[prior_offer],
        inline_file_text=False,
    )
    # Who-are-you prior does not unlock a work turn.
    assert text.should_block_no_tool_as_final(
        has_tool_calls=False,
        is_first_round=True,
        rounds_left=True,
        has_tools=True,
        content=specs,
        user_message='give me the technical specs of the mobile gantry',
        prior_assistant=[hello],
        inline_file_text=False,
    )
    closer = 'Tell me the next step when you want and we will look at it.'
    recovered = text.recover_displaced_turn_body(
        [{'role': 'assistant', 'content': specs},
         {'role': 'user', 'content': text.NO_TOOL_FINAL_NUDGE},
         {'role': 'assistant', 'content': closer}],
        closer,
    )
    assert specs in recovered
    assert closer in recovered
    # After a tool ran, prose (status, greeting round 2) may close.
    assert not text.should_block_no_tool_as_final(
        has_tool_calls=False,
        is_first_round=False,
        rounds_left=True,
        has_tools=True,
    )
    assert not text.should_block_no_tool_as_final(
        has_tool_calls=True,
        is_first_round=True,
        rounds_left=True,
        has_tools=True,
    )
    assert not text.should_block_no_tool_as_final(
        has_tool_calls=False,
        is_first_round=True,
        rounds_left=False,
        has_tools=True,
    )
    assert not text.should_block_no_tool_as_final(
        has_tool_calls=False,
        is_first_round=True,
        rounds_left=True,
        has_tools=False,
    )


def test_empty_content_stays_empty():
    assert text.user_visible_round_text('', has_tool_calls=False) == ''
    assert text.pretool_progress_status('') is None
    assert text.pretool_progress_status(None) is None


def test_strip_think_blocks():
    raw = 'Hola <think>plan interno</think> mundo'
    assert text.strip_think_blocks(raw) == 'Hola  mundo'
