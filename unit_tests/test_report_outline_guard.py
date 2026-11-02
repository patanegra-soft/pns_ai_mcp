# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Unit tests for report_outline_guard."""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from common.utils.report_outline_guard import (
    closing_present,
    contract_from_payload,
    ensure_report_completion,
    followup_note_after_tables,
    heading_present,
    is_report_closer,
    missing_outline_headings,
    recover_turn_report_body,
    report_body_started,
    stub_section_heading,
)


def test_heading_present_and_missing():
    text = '## Análisis\n### Fortalezas\nhola\n'
    assert heading_present(text, '## Análisis')
    assert heading_present(text, '### Fortalezas')
    assert not heading_present(text, '## Recomendaciones')
    missing = missing_outline_headings(text, [
        '## Análisis', '## Conclusión', '## Recomendaciones',
    ])
    assert missing == ['## Conclusión', '## Recomendaciones']


def test_ensure_appends_recommendations_and_closing():
    text = '## Análisis\n### Fortalezas\nok\n'
    out, changed = ensure_report_completion(
        text,
        outline=[
            '## Análisis',
            '### Fortalezas',
            '## Conclusión',
            '## Recomendaciones',
        ],
        closing='Línea recomendada de actuación: vigilar cobros.',
        recommendations_stub=['Acelerar cobro vencido.'],
    )
    assert changed
    assert '## Conclusión' in out
    assert '## Recomendaciones' in out
    assert 'Acelerar cobro vencido.' in out
    assert closing_present(out, 'Línea recomendada de actuación: vigilar cobros.')


def test_ensure_neutral_stub_without_skill_recommendations():
    text = '## Análisis\nok\n'
    out, changed = ensure_report_completion(
        text,
        outline=['## Análisis', '## Recomendaciones'],
    )
    assert changed
    assert out.rstrip().endswith('## Recomendaciones')
    assert '- ' not in out
    assert 'cobros' not in out
    assert 'pólizas' not in out
    assert 'liquidez' not in out


def test_ensure_noop_when_complete():
    text = (
        '## Análisis\n## Conclusión\n## Recomendaciones\n'
        'Línea recomendada de actuación: ok.\n'
    )
    out, changed = ensure_report_completion(
        text,
        outline=['## Análisis', '## Conclusión', '## Recomendaciones'],
        closing='Línea recomendada de actuación: ok.',
    )
    assert not changed
    assert out.strip() == text.strip()


_OUTLINE = [
    '## Analysis',
    '## Strengths',
    '## Weaknesses and risks',
    '## Conclusion',
    '## Recommendations',
]


def test_closer_is_not_a_started_report():
    closer = (
        'Si necesitas otro periodo, un recálculo o un seguimiento concreto '
        'sobre cobros o pólizas, dímelo y lo vemos.'
    )
    assert is_report_closer(closer, _OUTLINE)
    assert not report_body_started(closer, _OUTLINE)
    out, changed = ensure_report_completion(
        closer,
        outline=_OUTLINE,
        closing='Recommended action line: keep monitoring.',
    )
    assert not changed
    assert out.strip() == closer


def test_headingless_prose_is_not_replaced_with_stubs():
    prose = (
        'Sales softened versus the prior window and cash conversion '
        'lengthened. Facilities remain available; no urgent action.'
    )
    out, changed = ensure_report_completion(prose, outline=_OUTLINE)
    assert not changed
    assert out.strip() == prose


def test_truncated_skeleton_still_gets_stubs():
    text = '# Financial health\n## Analysis\nSales fell 7%.\n'
    out, changed = ensure_report_completion(text, outline=_OUTLINE)
    assert changed
    assert '## Strengths' in out
    assert '## Recommendations' in out
    assert out.count('\n') - text.count('\n') <= 2 * len(_OUTLINE)


def test_recover_reuses_earlier_assistant_narrative():
    report = (
        '# Financial health over the last 12 months\n\n'
        '## Analysis\nNet sales 1,848,171.02 vs 1,985,469.20 (−6.92%).\n\n'
        '## Strengths\nCash buffer holds.\n\n'
        '## Weaknesses and risks\nCollections stretched.\n\n'
        '## Conclusion\nWatch liquidity.\n\n'
        '## Recommendations\n- Keep monitoring liquidity.\n'
        'Recommended action line: no urgent action; keep monitoring.\n'
    )
    closer = (
        'Si necesitas otro periodo, un recálculo o un seguimiento concreto '
        'sobre cobros o pólizas, dímelo y lo vemos.'
    )
    messages = [
        {'role': 'user', 'content': '/financial-health'},
        {'role': 'assistant', 'content': report, 'tool_calls': [{'id': '1'}]},
        {'role': 'tool', 'content': '{"data_rendered": true}'},
        {'role': 'assistant', 'content': closer},
    ]
    recovered = recover_turn_report_body(messages, closer, _OUTLINE)
    assert report.strip() in recovered
    assert closer in recovered
    out, changed = ensure_report_completion(
        recovered,
        outline=_OUTLINE,
        closing='Recommended action line: no urgent action; keep monitoring.',
    )
    assert not changed


def test_recover_ignores_prior_turn_when_slice_excludes_it():
    old = '# Old report\n## Analysis\nYesterday.\n'
    closer = 'Here you go. If you need anything else, just tell me.'
    this_turn = [
        {'role': 'assistant', 'content': closer},
    ]
    recovered = recover_turn_report_body(this_turn, closer, _OUTLINE)
    assert recovered == closer
    assert old not in recovered


def test_stub_goes_to_last_outline_heading_not_lexicon():
    assert stub_section_heading(
        ['## Analysis', '## Next steps'],
    ) == '## Next steps'
    text = '# Report\n## Analysis\nok\n'
    out, changed = ensure_report_completion(
        text,
        outline=['## Analysis', '## Next steps'],
        recommendations_stub=['Review the prior tables.'],
        closing='Recommended action line: keep watching.',
    )
    assert changed
    assert '## Next steps' in out
    assert 'Review the prior tables.' in out
    assert '## Recomendaciones' not in out
    assert '## Recommendations' not in out


def test_closing_does_not_invent_a_heading():
    text = (
        '# Report\n## Analysis\nok\n## Next steps\n- done\n'
    )
    out, changed = ensure_report_completion(
        text,
        outline=['## Analysis', '## Next steps'],
        closing='Recommended action line: keep watching.',
    )
    assert changed
    assert 'Recommended action line: keep watching.' in out
    assert '## Recomendaciones' not in out


def test_free_text_outline_unlocks_figure_citations():
    assert contract_from_payload({'data': [{'a': 1}]}) is None
    assert contract_from_payload({'report_outline': ['  ', '']}) is None
    contract = contract_from_payload({
        'data': [{'name': 'A'}],
        'report_outline': ['## Hechos', '## Qué hacer'],
        'closing_required': 'Recommended action line: wait.',
    })
    assert contract['report_outline'] == ['## Hechos', '## Qué hacer']
    listing = followup_note_after_tables(3, None)
    assert 'FORBIDDEN' in listing
    assert 'figures' in listing
    report = followup_note_after_tables(3, contract)
    assert '## Hechos' in report
    assert '## Qué hacer' in report
    assert 'Cite only figures' in report
    assert 'FORBIDDEN' not in report


def test_system_prompt_paints_report_tables():
    text = (
        _ROOT / 'common' / 'ai' / 'contexts' / 'core' / 'system_prompt.xml'
    ).read_text(encoding='utf-8')
    assert 'report_outline' in text
    assert 'Do NOT push a multi-row table' not in text
    assert 'return_mode=inspect_result, then write a clear Markdown report' not in text
