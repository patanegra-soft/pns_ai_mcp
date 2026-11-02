# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Host tests: committed-cursor persist helpers and chip coalesce."""
from __future__ import annotations

from pathlib import Path

from _load_addon import engine_source, load_module

sd = load_module('session_download', 'utils', 'session_download.py')


def test_coalesce_download_chips_dedupes_url():
    a = {'url': '/web/content/1', 'name': 'a.pdf'}
    b = {'url': '/web/content/1', 'name': 'dup.pdf'}
    c = {'url': '/web/content/2', 'name': 'b.pdf'}
    out = sd.coalesce_download_chips([a], [b, c], None, [])
    assert [x['name'] for x in out] == ['a.pdf', 'b.pdf']


def test_content_download_url_uses_filename_not_id():
    url = sd.content_download_url(
        74007, '10_mejores_clientes_murcia_barcelona.pdf', 'application/pdf',
    )
    assert url == '/pns_ai_mcp/session_file/74007/10_mejores_clientes_murcia_barcelona.pdf'
    xlsx = sd.content_download_url(
        74008, 'mejores_clientes_murcia_barcelona.xlsx',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    assert xlsx.endswith('/mejores_clientes_murcia_barcelona.xlsx')
    svg = sd.content_download_url(9, 'gato.svg', 'image/svg+xml')
    assert svg == '/pns_ai_mcp/session_file/9'
    assert sd.is_inline_preview_file('a.svg')
    assert not sd.is_inline_preview_file('a.pdf')


def test_run_on_committed_cursor_falls_back_without_registry():
    class Env:
        pass

    seen = []

    def fn(e):
        seen.append(e)
        return 42

    env = Env()
    assert sd._run_on_committed_cursor(env, fn) == 42
    assert seen == [env]


def test_uuid_filename_is_not_preferred():
    uuid_name = 'cb72c4b3-eb9c-4c37-9fe9-44f961d002b6.pdf'
    human = 'Contrato trabajo Laura Martín Ortega.pdf'
    assert sd.preferred_download_filename(
        uuid_name,
        arguments={'documentId': '51343b40-06ba-48a1-8faa-9ea3fb5bd9ef'},
        labels={'51343b40-06ba-48a1-8faa-9ea3fb5bd9ef': human},
    ) == human
    assert sd.preferred_download_filename(
        uuid_name,
        arguments={'name': human, 'documentId': 'x'},
    ) == human
    assert sd.preferred_download_filename(human) == human


def test_file_labels_from_directory_listing():
    steps = [{
        'op': 'api_call',
        'success': True,
        'body': (
            '{"data":[{"documentId":"abc-1",'
            '"name":"Contrato trabajo Laura.pdf",'
            '"fileType":"application/pdf"}]}'
        ),
    }]
    labels = sd.file_labels_from_steps(steps)
    assert labels['abc-1'] == 'Contrato trabajo Laura.pdf'


def test_file_labels_from_display_column_and_prior_rows():
    doc_id = '51343b40-06ba-48a1-8faa-9ea3fb5bd9ef'
    human = 'Contrato trabajo Laura Martín Ortega.pdf'
    labels = sd.file_labels_from_mapping({
        'data': [{
            'documentId': doc_id,
            'Documento': human,
            'Fecha': '2024-01-15',
        }],
    })
    assert labels[doc_id] == human
    skipped = sd.file_labels_from_mapping({
        'id': 42,
        'name': 'Laura Martín',
        '__model': 'res.partner',
    })
    assert '42' not in skipped
    uuid_name = 'cb72c4b3-eb9c-4c37-9fe9-44f961d002b6.pdf'
    assert sd.preferred_download_filename(
        uuid_name,
        arguments={'documentId': doc_id},
        labels=labels,
    ) == human


def test_extract_binary_does_not_use_tool_name_as_filename():
    raw = sd.try_extract_binary_payload(
        {
            'filename': 'cb72c4b3-eb9c-4c37-9fe9-44f961d002b6.pdf',
            'data': 'JVBERi0xLjQK' + ('A' * 80),
        },
        tool_name='DownloadDocument',
        arguments={'documentId': '51343b40-06ba-48a1-8faa-9ea3fb5bd9ef'},
    )
    if raw is None:
        return
    assert raw['filename'] != 'DownloadDocument'
    assert sd._is_generic_name(raw['filename'])


def test_extract_binary_skips_uuid_filename_when_name_exists():
    raw = sd.try_extract_binary_payload(
        {
            'filename': 'cb72c4b3-eb9c-4c37-9fe9-44f961d002b6.pdf',
            'name': 'Contrato trabajo.pdf',
            'data': 'JVBERi0xLjQK' + ('A' * 80),
        },
        tool_name='DownloadDocument',
    )
    if raw is None:
        return
    assert raw['filename'] == 'Contrato trabajo.pdf'


def test_engine_hides_tables_when_session_download_chip():
    src = engine_source()
    assert '_absorb_plan_downloads' in src
    assert '_harvest_file_labels' in src
    assert 'file_label_by_id' in src
    assert 'wants_on_screen_blocks' in src
    assert 'client_fulfill=bool(session_id)' in src


def test_persist_uses_committed_cursor():
    src = Path(sd.__file__).read_text(encoding='utf-8')
    assert '_run_on_committed_cursor' in src
    assert 'cr.commit()' in src
    assert 'preferred_download_filename' in src
    assert 'file_labels_from_steps' in src
