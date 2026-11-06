# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Known-format file export: parser, serialization, download banner."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from _load_addon import engine_source, export_source, load_module, render_source

ae = load_module('artifact_export', 'utils', 'artifact_export.py')


def _use_formatters(monkeypatch, fake):
    """Each ``artifact_export*`` file reads its own ``_load_formatters``."""
    for name, mod in list(sys.modules.items()):
        if (name == ae.__name__ or name.startswith(ae.__name__ + '_')) and hasattr(
            mod, '_load_formatters',
        ):
            monkeypatch.setattr(mod, '_load_formatters', lambda: fake)


def _has_chip(result):
    return bool(ae.export_result_chips(result))


def _xlsx_one_sheet(rows, title='Export', labels=None, caption=None,
                    widths=None, formulas=None, number_style=None):
    """One sheet through the stdlib writer the engine falls back to."""
    specs = ae._normalize_xlsx_sheets([{
        'title': title,
        'rows': rows,
        'labels': labels,
        'caption': caption,
        'widths': widths,
        'formulas': formulas,
    }])
    if not specs:
        return None
    style = number_style or ae.xlsx_number_style()
    for spec in specs:
        spec['number_style'] = spec.get('number_style') or style
    return ae._as_xlsx_ooxml_book(specs)

_ROWS = [
    {'Name': 'Alpha', 'Total': 10, '_row_color': '#eef2f8'},
    {'Name': 'Beta', 'Total': 20, '_hidden': True},
]


def test_serialize_rows_markdown_skips_private_keys():
    raw = ae.serialize_rows(_ROWS, 'md')
    text = raw.decode('utf-8')
    assert '| Name | Total |' in text
    assert 'Alpha' in text
    assert '_row_color' not in text
    assert '_hidden' not in text


def test_serialize_rows_txt_and_html():
    txt = ae.serialize_rows(_ROWS, 'txt').decode('utf-8')
    assert txt.splitlines()[0] == 'Name\tTotal'
    assert 'Alpha\t10' in txt
    html = ae.serialize_rows(_ROWS, 'html').decode('utf-8')
    assert '<table>' in html
    assert 'Beta' in html
    assert '_row_color' not in html


def test_serialize_xlsx_bytes():
    raw = ae.serialize_rows(_ROWS, 'xlsx')
    assert raw is not None
    assert raw[:2] == b'PK'


def test_xlsx_ooxml_stdlib_does_not_need_openpyxl():
    raw = _xlsx_one_sheet(_ROWS, 'Export')
    assert raw[:2] == b'PK'
    import io
    import zipfile
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        names = set(zf.namelist())
        assert 'xl/worksheets/sheet1.xml' in names
        sheet = zf.read('xl/worksheets/sheet1.xml').decode('utf-8')
    assert 'Alpha' in sheet
    assert 'Total' in sheet
    assert '_row_color' not in sheet
    assert 'state="frozen"' in sheet
    assert 'ySplit="1"' in sheet
    assert 'topLeftCell="A2"' in sheet


def test_as_xlsx_uses_stdlib_when_openpyxl_missing(monkeypatch):
    class BoomFmt:
        @staticmethod
        def format_data_as_excel(*_a, **_k):
            raise Exception('openpyxl is not installed')

    _use_formatters(monkeypatch, BoomFmt)
    import builtins
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == 'openpyxl' or (
            isinstance(name, str) and name.startswith('openpyxl.')
        ):
            raise ImportError('no openpyxl')
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, '__import__', fake_import)
    raw = ae._as_xlsx(_ROWS, 'Export')
    assert raw[:2] == b'PK'


def test_xlsx_ooxml_strips_control_chars():
    raw = _xlsx_one_sheet(
        [{'Name': 'A\x00B', 'Note': 'ok'}],
        'Q:report*',
    )
    assert raw[:2] == b'PK'
    import io
    import zipfile
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        book = zf.read('xl/workbook.xml').decode('utf-8')
        sheet = zf.read('xl/worksheets/sheet1.xml').decode('utf-8')
    assert 'name="Q report"' in book
    assert 'AB' in sheet
    assert '\x00' not in sheet


def test_serialize_pdf_bytes():
    raw = ae.serialize_rows(_ROWS, 'pdf')
    if raw is None:
        pytest.skip('reportlab not installed')
    assert raw.startswith(b'%PDF')


def test_word_serializes_office_html():
    captured = {}

    def persist(raw, filename, mimetype):
        captured['raw'] = raw
        captured['filename'] = filename
        captured['mimetype'] = mimetype
        return {'name': filename, 'url': '#', 'mimetype': mimetype}

    out = ae.apply_requested_exports(
        'pásame el informe en word',
        rows=_ROWS,
        persist=persist,
    )
    assert out['acted']
    assert out['parsed'] and not out['parsed']['refused']
    assert out['parsed']['kind'] == 'doc'
    assert captured['filename'].endswith('.doc')
    assert captured['mimetype'] == 'application/msword'
    text = captured['raw'].decode('utf-8')
    assert 'xmlns:w="urn:schemas-microsoft-com:office:word"' in text
    assert '#eceff1' in text
    assert 'Alpha' in text
    assert 'Beta' in text
    assert '_row_color' not in text


def test_odt_with_leading_dot_is_refused():
    """The period is not the bug: ``.odt`` already matched _REFUSE_RE."""
    msg = 'pues entonces un .odt con los mejores clientes de sevilla'
    parsed = ae.parse_requested_export(msg)
    assert parsed and parsed['refused']
    assert parsed.get('format') is None
    assert ae.is_refused_export(msg)
    assert ae.requested_named_format(msg) is None
    assert not ae.apply_requested_exports(msg, rows=_ROWS)['acted']


def test_unknown_dotted_ext_is_refused_domain_is_not():
    assert ae.is_refused_export('pásame un .rtf por favor')
    assert ae.is_refused_export('un .csv con el ranking')
    assert not ae.is_refused_export(
        'el portal de acmeelevadores.com',
    )
    assert not ae.is_refused_export('lista de clientes de Sevilla')
    named = ae.parse_requested_export('ahora un .pdf por favor')
    assert named and named['format'] == 'pdf' and not named['refused']


def test_engine_short_circuits_refused_export():
    src = engine_source()
    assert 'is_refused_export' in src
    assert 'REFUSED_EXPORT_REPLY' in src
    assert 'That file type is not available' in ae.REFUSED_EXPORT_REPLY
    assert 'merge_refused_note' in src
    assert ae.REFUSED_PARTIAL_REPLY in src
    assert '_stamp_refused_note' in src
    assert 'apply_requested_exports' in src


def test_excel_utterance_persists_without_rewriting_the_bubble():
    captured = {}

    def persist(raw, filename, mimetype):
        captured['raw'] = raw
        captured['filename'] = filename
        captured['mimetype'] = mimetype
        return {
            'name': filename,
            'url': '/web/content/1',
            'mimetype': mimetype,
            'size': len(raw),
        }

    out = ae.apply_requested_exports(
        'pásame el informe en excel',
        rows=_ROWS,
        persist=persist,
    )
    assert out['acted']
    assert 'file_only' not in out
    assert 'replace_html' not in out
    assert 'show_on_screen' not in (out['parsed'] or {})
    assert captured['filename'].endswith('.xlsx')
    assert captured['raw'].startswith(b'PK')
    assert out['chip']['url'] == '/web/content/1'


def test_see_phrasing_does_not_change_engine_export():
    """Table vs card is the pack, not a verb list in Python."""
    named = ae.parse_requested_export('send me an excel')
    see = ae.parse_requested_export('show me the table and send me an excel')
    assert named['format'] == see['format'] == 'excel'
    assert 'show_on_screen' not in named
    assert 'file_only' not in named
    out = ae.apply_requested_exports(
        'show me the table and send me an excel',
        rows=_ROWS,
    )
    assert out['acted']
    assert out['chip']


def test_excel_and_word_are_two_kinds():
    parsed = ae.parse_requested_export('no lo quiero en word, pásame excel')
    assert not parsed['refused']
    kinds = [s['kind'] for s in parsed['formats']]
    assert kinds == ['doc', 'xlsx'] or set(kinds) == {'doc', 'xlsx'}
    assert 'word' not in [t.lower().lstrip('.') for t in parsed.get('refused_tokens') or []]
    assert not ae.is_refused_export('no lo quiero en word, pásame excel')


def test_no_format_is_none():
    assert ae.parse_requested_export('lista de clientes de Madrid') is None


def test_engine_has_no_show_verb_list():
    assert not hasattr(ae, '_SHOW_RE')


def test_pdf_utterance_persists_via_callback():
    captured = {}

    def persist(raw, filename, mimetype):
        captured['filename'] = filename
        captured['mimetype'] = mimetype
        captured['raw'] = raw
        return {
            'name': filename,
            'url': '/web/content/2',
            'mimetype': mimetype,
            'size': len(raw),
        }

    out = ae.apply_requested_exports(
        'crea un pdf con los 20 mejores clientes',
        rows=_ROWS,
        persist=persist,
    )
    if not out['acted']:
        pytest.skip('pdf serialization unavailable')
    assert captured['filename'].endswith('.pdf')
    assert captured['mimetype'] == 'application/pdf'
    assert captured['raw'].startswith(b'%PDF')
    assert out['chip']['url'] == '/web/content/2'


def test_session_file_propose_orphan_create():
    assert ae.is_session_file_propose([
        {
            'op': 'create',
            'model': 'ir.attachment',
            'values': {
                'name': '20mejoresclientes_sevilla.pdf',
                'datas': 'AAAA',
            },
        },
    ])
    assert not ae.is_session_file_propose([
        {
            'op': 'create',
            'model': 'ir.attachment',
            'values': {'name': 'report.pdf', 'res_model': 'res.partner'},
        },
    ])


def test_session_file_propose_business_attachment_is_false():
    assert not ae.is_session_file_propose([
        {
            'op': 'create',
            'model': 'ir.attachment',
            'values': {
                'name': 'invoice.pdf',
                'datas': 'AAAA',
                'res_model': 'res.partner',
                'res_id': 12,
            },
        },
    ])
    assert not ae.is_session_file_propose([
        {'op': 'create', 'model': 'res.partner', 'values': {'name': 'Acme'}},
    ])
    assert not ae.is_session_file_propose([])
    assert not ae.is_session_file_propose(None)


def test_named_format_and_protocol_are_english():
    parsed = ae.requested_named_format(
        'me creas un pdf con los 20 mejores clientes en apaisado',
    )
    assert parsed['format'] == 'pdf'
    assert 'landscape' not in parsed
    assert ae.requested_named_format('pásame el informe') is None
    assert 'reportlab' in ae.SESSION_FILE_PROTOCOL
    assert 'openpyxl' in ae.SESSION_FILE_PROTOCOL
    assert 'ir.attachment' in ae.SESSION_FILE_PROTOCOL
    assert 'safe_plan_request' in ae.SESSION_FILE_PROTOCOL
    assert '__show_table__' in ae.SESSION_FILE_PROTOCOL
    assert 'assembled by the chat client' in ae.SESSION_FILE_PROTOCOL
    assert 'mirror this turn' in ae.SESSION_FILE_PROTOCOL
    assert 'Excel and Markdown stay server tables' in ae.SESSION_FILE_PROTOCOL
    assert '__landscape__' in ae.SESSION_FILE_PROTOCOL
    assert '__excel_formulas__' in ae.SESSION_FILE_PROTOCOL
    assert 'Derived columns' in ae.SESSION_FILE_PROTOCOL
    assert 'one card per format' in ae.SESSION_FILE_PROTOCOL
    assert 'mostrar' not in ae.SESSION_FILE_PROTOCOL
    assert 'caja B' in ae.SESSION_FILE_PROPOSE_ERROR
    assert 'FULL report' in ae.SESSION_FILE_REPORT_NOTE
    assert 'pointer to the card' in ae.SESSION_FILE_REPORT_NOTE
    assert 'mostrar' not in ae.SESSION_FILE_REPORT_NOTE


def test_pdf_orientation_is_not_a_locale_catalog():
    """Orientation is a flag or a shape heuristic; no ES/IT/JA word list."""
    assert not hasattr(ae, 'parse_pdf_landscape')
    assert not hasattr(ae, '_LANDSCAPE_RE')
    assert not hasattr(ae, '_PORTRAIT_RE')
    src = export_source()
    assert 'apaisado' not in src
    assert 'retrato' not in src
    assert 'orizzontale' not in src
    for msg in (
        'crea un pdf apaisado',
        'crea un PDF in orizzontale per favore',
        'PDFを横向きで作って',
    ):
        parsed = ae.parse_requested_export(msg)
        assert parsed and parsed['format'] == 'pdf'
    assert ae.pdf_landscape(None) is True
    assert ae.pdf_landscape({}) is True
    assert ae.pdf_landscape({'data': _ROWS}) is False
    assert ae.pdf_landscape({'__landscape__': False}) is False
    assert ae.pdf_landscape({'__landscape__': True}) is True
    assert ae.pdf_landscape({'data': _ROWS, '__landscape__': True}) is True
    assert ae.pdf_landscape({'data': _ROWS, '__landscape__': False}) is False
    assert ae.pdf_landscape({'data': _ROWS, '__orientation__': 'landscape'}) is True
    assert ae.pdf_landscape({'data': _ROWS, '__orientation__': 'portrait'}) is False
    assert ae.pdf_landscape({
        'data': _ROWS,
        '__landscape__': False,
        '__orientation__': 'landscape',
    }) is False
    wide = [{('Col%d' % i): i for i in range(8)}]
    assert ae.pdf_landscape({'data': wide}) is True
    assert ae.pdf_landscape({'data': wide, '__landscape__': False}) is False
    portrait = ae.apply_requested_exports(
        'PDF', wide, payload={'data': wide, '__landscape__': False},
    )
    landscape = ae.apply_requested_exports(
        'PDF', wide, payload={'data': wide},
    )
    if portrait.get('raw') and landscape.get('raw'):
        assert portrait['raw'] != landscape['raw']


def test_pdf_style_matches_chatboo_not_legacy_purple():
    raw = ae.serialize_rows(_ROWS, 'pdf')
    if raw is None:
        pytest.skip('reportlab not installed')
    assert raw.startswith(b'%PDF')
    assert b'Sistema MCP Odoo' not in raw
    assert b'667eea' not in raw
    fmt = (
        Path(ae.__file__).resolve().parents[1] / 'controllers' / 'formatters.py'
    ).read_text(encoding='utf-8')
    assert 'KeepTogether' in fmt
    assert 'splitByRow=1' in fmt
    assert 'repeatRows=1' in fmt
    assert 'apaisado' not in fmt
    assert '#eceff1' in fmt


def test_pdf_image_cell_embeds_bytes_not_url():
    png_b64 = (
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQ'
        'DwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
    )
    rows = [{
        'Name': 'Alpha',
        'image_128': 'data:image/png;base64,' + png_b64,
    }]
    raw = ae.serialize_rows(rows, 'pdf')
    if raw is None:
        pytest.skip('reportlab not installed')
    assert raw.startswith(b'%PDF')
    assert b'/web/image/' not in raw
    assert b'data:image/png' not in raw
    missing = ae.serialize_rows(
        [{'Name': 'X', 'image_128': '/web/image/res.partner/1/image_128'}],
        'pdf',
    )
    if missing:
        assert b'/web/image/res.partner/1/image_128' not in missing


def test_pdf_chart_series_from_monthly_rows():
    rows = [
        {'Mes': 'Sep 2025', 'Importe': 93511.14, 'N facturas': 61},
        {'Mes': 'Oct 2025', 'Importe': 41200.0, 'N facturas': 38},
        {'Mes': 'Nov 2025', 'Importe': 50110.5, 'N facturas': 41},
        {'Mes': 'Dec 2025', 'Importe': 62340.0, 'N facturas': 44},
        {'Mes': 'Jan 2026', 'Importe': 38890.0, 'N facturas': 29},
        {'Mes': 'Feb 2026', 'Importe': 45500.0, 'N facturas': 33},
        {'Mes': 'Mar 2026', 'Importe': 71020.0, 'N facturas': 48},
        {'Mes': 'Apr 2026', 'Importe': 64010.0, 'N facturas': 46},
        {'Mes': 'May 2026', 'Importe': 81222.0, 'N facturas': 52},
        {'Mes': 'Jun 2026', 'Importe': 59000.0, 'N facturas': 40},
        {'Mes': 'Jul 2026', 'Importe': 47880.0, 'N facturas': 36},
        {'Mes': 'Aug 2026', 'Importe': 35012.0, 'N facturas': 27},
    ]
    spec = ae.pdf_chart_series(rows)
    assert ae.coerce_chart_number('93.511,14') == 93511.14
    # Dual-scale (€ vs count): do not improvise a one-axis chart.
    assert spec is None
    single = [{'Mes': row['Mes'], 'Importe': row['Importe']} for row in rows]
    only_amount = ae.pdf_chart_series(single)
    assert only_amount is not None
    assert only_amount['categories'][0] == 'Sep 2025'
    assert only_amount['kind'] == 'line'
    assert only_amount['series'][0]['name'] == 'Importe'
    assert only_amount['series'][0]['values'][0] == 93511.14
    assert ae.pdf_chart_series(_ROWS) is None
    assert ae.pdf_chart_series(rows[:2]) is None
    assert ae.payload_allows_charts({'__no_charts__': True}) is False
    assert ae.payload_allows_charts({'charts': False}) is False
    assert ae.payload_allows_charts({'data': rows}) is True
    assert 'gráfico' not in export_source()
    assert 'apaisado' not in export_source()


def test_pdf_includes_structural_chart_unless_opted_out():
    rows = [
        {'Month': 'M%02d' % idx, 'Amount': 1000.0 + idx * 80}
        for idx in range(1, 13)
    ]
    with_chart = ae.serialize_rows(rows, 'pdf', title='Seville')
    no_chart = ae.serialize_rows(rows, 'pdf', title='Seville', charts=False)
    if with_chart is None or no_chart is None:
        pytest.skip('reportlab not installed')
    assert with_chart.startswith(b'%PDF')
    assert no_chart.startswith(b'%PDF')
    assert with_chart != no_chart
    assert len(with_chart) > len(no_chart)
    refused = ae.apply_requested_exports(
        'PDF',
        rows=rows,
        payload={'data': rows, '__no_charts__': True, '__title__': 'Seville'},
    )
    if refused.get('raw'):
        assert refused['raw'] == no_chart or refused['raw'].startswith(b'%PDF')
        assert len(refused['raw']) < len(with_chart)
    fmt = (
        Path(ae.__file__).resolve().parents[1] / 'controllers' / 'formatters.py'
    ).read_text(encoding='utf-8')
    assert 'HorizontalLineChart' in fmt
    assert 'VerticalBarChart' in fmt
    chart_fn = fmt.split('def _pdf_chart_drawing', 1)[1].split('def format_data_as_pdf', 1)[0]
    assert '667eea' not in chart_fn
    assert 'gráfico' not in chart_fn


def test_clip_data_carries_landscape_flag():
    clip = ae.clip_data_from_payload({
        'data': _ROWS,
        '__title__': 'Lista',
        '__landscape__': False,
    })
    assert clip['landscape'] is False
    assert ae.clip_data_from_payload({'data': _ROWS})['landscape'] is False
    assert ae.clip_data_from_payload({
        'data': _ROWS, '__orientation__': 'landscape',
    })['landscape'] is True
    bare = ae.clip_data_from_payload({'data': _ROWS})
    assert bare['include_table'] is True
    assert bare['include_chart'] is False
    chart_only = ae.clip_data_from_payload({
        'data': _ROWS, 'show_mode': 'show-chart',
    })
    assert chart_only['include_table'] is False
    assert chart_only['include_chart'] is True
    both = ae.clip_data_from_payload({
        'data': _ROWS,
        '__show_table__': True,
        'show_mode': 'chart-table',
    })
    assert both['include_table'] is True
    assert both['include_chart'] is True


def test_export_hides_table_unless_flag():
    msg = 'crea un pdf con los 20 mejores clientes'
    assert ae.export_hides_on_screen_table(msg, {'data': _ROWS})
    assert not ae.export_hides_on_screen_table(
        msg, {'data': _ROWS, '__show_table__': True},
    )
    assert not ae.export_hides_on_screen_table(
        'lista de clientes', {'data': _ROWS},
    )
    assert not ae.wants_on_screen_table({'data': _ROWS})
    assert ae.wants_on_screen_table({'__show_table__': True})
    assert ae.wants_on_screen_table({
        'data': _ROWS,
        'show_mode': 'show-table',
    })
    assert not ae.wants_on_screen_table({
        'data': _ROWS,
        '__show_table__': False,
        'show_mode': 'show-chart',
    })
    assert ae.export_hides_on_screen_table(
        msg, {'data': _ROWS, 'show_mode': 'show-chart'},
    )
    assert ae.wants_on_screen_blocks({
        'data': _ROWS, 'show_mode': 'show-chart',
    })
    assert not ae.clip_include_table({
        'data': _ROWS, 'show_mode': 'show-chart',
    })
    assert ae.clip_include_chart({
        'data': _ROWS, 'show_mode': 'show-chart',
    })


def test_has_export_chip_requires_acted_and_url():
    assert not _has_chip(None)
    assert not _has_chip({'acted': True})
    assert not _has_chip({'acted': False, 'chip': {'url': '/x'}})
    assert _has_chip({
        'acted': True,
        'chip': {'name': 'a.pdf', 'url': '/web/content/2'},
    })
    assert _has_chip({
        'acted': True,
        'chips': [{'name': 'a.pdf', 'url': '/web/content/2'}],
    })


def test_engine_done_carries_assistant_files():
    src = engine_source()
    assert "['assistant_files']" in src or '"assistant_files"' in src
    assert 'coalesce_download_chips' in src
    assert 'export_chips' in src


def test_title_flag_names_file_and_interior_heading():
    prompt = 'creas mejores clientes sevilla en pdf'
    payload = {
        'data': _ROWS,
        '__title__': 'Mejores clientes de Sevilla',
    }
    out = ae.apply_requested_exports(
        'un markdown con el ranking',
        rows=_ROWS,
        payload=payload,
        prompt=prompt,
    )
    assert out['acted']
    assert out['filename'] == 'mejores_clientes_de_sevilla.md'
    assert 'creas' not in out['filename']
    text = out['raw'].decode('utf-8')
    assert text.startswith('# Mejores clientes de Sevilla')
    assert 'Export' not in text.split('\n', 1)[0]
    html = ae.serialize_rows(
        _ROWS, 'html', title=ae.export_title(payload),
    ).decode('utf-8')
    assert '<h1>Mejores clientes de Sevilla</h1>' in html
    assert '<h1>Export</h1>' not in html
    pdf = ae.apply_requested_exports(
        prompt, rows=_ROWS, payload=payload,
    )
    if pdf.get('raw'):
        assert pdf['filename'] == 'mejores_clientes_de_sevilla.pdf'
        other = ae.apply_requested_exports(
            prompt, rows=_ROWS,
            payload={'data': _ROWS, '__title__': 'Otro listado'},
        )
        fallback = ae.apply_requested_exports('pdf', rows=_ROWS)
        if other.get('raw'):
            assert pdf['raw'] != other['raw']
        if fallback.get('raw'):
            assert pdf['raw'] != fallback['raw']


def test_filename_stem_optional_override():
    payload = {
        'data': _ROWS,
        '__title__': 'Titulo demasiado largo para un fichero',
        '__filename_stem__': 'ranking-sevilla',
    }
    out = ae.apply_requested_exports(
        'markdown please', rows=_ROWS, payload=payload,
    )
    assert out['filename'].startswith('ranking')
    assert out['filename'].endswith('.md')
    assert 'titulo' not in out['filename']


def test_apply_without_title_still_serializes_fallback():
    assert not ae.has_export_meta({'data': _ROWS})
    assert ae.has_export_meta({'__title__': 'Hola'})
    assert ae.has_export_meta({'__filename_stem__': 'foo'})
    out = ae.apply_requested_exports('excel', rows=_ROWS)
    assert out['acted']
    assert out['filename'].endswith('.xlsx')
    assert out['raw'][:2] == b'PK'
    md = ae.serialize_rows(_ROWS, 'md', title='').decode('utf-8')
    assert not md.startswith('#')


def test_xlsx_ooxml_cols_and_optional_caption():
    raw = _xlsx_one_sheet(_ROWS, 'Export')
    import io
    import zipfile
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        sheet = zf.read('xl/worksheets/sheet1.xml').decode('utf-8')
    assert '<cols>' in sheet
    assert 'customWidth="1"' in sheet
    assert 'mergeCells' not in sheet
    labelled = _xlsx_one_sheet(
        _ROWS, 'Ranking',
        labels={'Name': 'Nombre'},
        caption='Clientes 2024',
        widths=ae.column_widths(_ROWS, {'Name': 'Nombre', 'Total': 'Total'}),
    )
    with zipfile.ZipFile(io.BytesIO(labelled)) as zf:
        sheet = zf.read('xl/worksheets/sheet1.xml').decode('utf-8')
        book = zf.read('xl/workbook.xml').decode('utf-8')
    assert 'Clientes 2024' in sheet
    assert 'Nombre' in sheet
    assert 'mergeCells' in sheet
    assert 'ySplit="2"' in sheet
    assert 'topLeftCell="A3"' in sheet
    assert 'name="Ranking"' in book
    wide = ae.column_widths([{'Name': 'A' * 40, 'N': 1}])
    assert wide[0] >= 20
    assert wide[0] <= 50


def test_serialize_xlsx_sheets_keeps_two_tabs():
    raw = ae.serialize_xlsx_sheets([
        {'title': 'Murcia', 'rows': _ROWS},
        {
            'title': 'Barcelona',
            'rows': [{'Name': 'Gamma', 'Total': 5}],
            'labels': {'Name': 'Nombre', 'Total': 'Total'},
        },
    ])
    assert raw[:2] == b'PK'
    import io
    import zipfile
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        names = set(zf.namelist())
        book = zf.read('xl/workbook.xml').decode('utf-8')
        sheet1 = zf.read('xl/worksheets/sheet1.xml').decode('utf-8')
        sheet2 = zf.read('xl/worksheets/sheet2.xml').decode('utf-8')
    assert 'xl/worksheets/sheet1.xml' in names
    assert 'xl/worksheets/sheet2.xml' in names
    assert 'name="Murcia"' in book
    assert 'name="Barcelona"' in book
    assert 'ySplit="1"' in sheet1
    assert 'ySplit="1"' in sheet2
    assert 'Nombre' in sheet2


def test_sheets_from_aoa_and_icon_payload():
    sections = [
        {
            'title': 'Murcia',
            'aoa': [['Name', 'Total'], ['Alpha', 10], ['Beta', 20]],
        },
        {
            'title': 'Barcelona',
            'aoa': [['Name', 'Total'], ['Gamma', 5]],
        },
    ]
    sheets = ae.sheets_from_aoa_sections(sections)
    assert [s['title'] for s in sheets] == ['Murcia', 'Barcelona']
    assert sheets[0]['rows'][0]['Name'] == 'Alpha'
    payload = ae.icon_xlsx_payload(sections, filename='../mejores.xlsx')
    assert payload['filename'] == 'mejores.xlsx'
    assert payload['mimetype'] == ae._XLSX_MIME
    assert payload['datas']
    import base64
    raw = base64.b64decode(payload['datas'])
    assert raw[:2] == b'PK'


def test_xlsx_writes_numbers_not_strings():
    assert ae._excel_number(10) == 10
    assert ae._excel_number(10.5) == 10.5
    assert ae._excel_number('12') is None
    assert ae._excel_number('12.5') is None
    assert ae._excel_number('01') is None
    assert ae._excel_typed('01') == '01'
    assert ae._excel_typed('12') == '12'
    assert ae._excel_number(True) is None
    try:
        from openpyxl import load_workbook
    except ImportError:
        pytest.skip('openpyxl not installed')
    import io
    raw = ae._as_xlsx(
        [{'Name': 'Alpha', 'Total': 10, 'Rate': '12.5', 'Code': '01'}],
        'Export',
    )
    wb = load_workbook(io.BytesIO(raw))
    ws = wb.active
    assert ws['B2'].value == 10
    assert isinstance(ws['B2'].value, (int, float))
    assert ws['C2'].value == '12.5'
    assert ws['D2'].value == '01'
    aoa = ae.serialize_xlsx_sheets(ae.sheets_from_aoa_sections([{
        'title': 'T',
        'aoa': [['N', 'Qty'], ['A', 3], ['B', '3']],
    }]))
    wb2 = load_workbook(io.BytesIO(aoa))
    assert wb2.active['B2'].value == 3
    assert wb2.active['B3'].value == '3'
    ooxml = _xlsx_one_sheet([{'Name': 'A', 'Total': 10}], 'Export')
    import zipfile
    with zipfile.ZipFile(io.BytesIO(ooxml)) as zf:
        sheet = zf.read('xl/worksheets/sheet1.xml').decode('utf-8')
    assert '<v>10</v>' in sheet


def test_as_xlsx_freezes_header_row():
    fmt = (
        Path(ae.__file__).resolve().parents[1] / 'controllers' / 'formatters.py'
    ).read_text(encoding='utf-8')
    assert 'ws.freeze_panes' in fmt
    try:
        from openpyxl import load_workbook
    except ImportError:
        pytest.skip('openpyxl not installed')
    import io
    raw = ae._as_xlsx(_ROWS, 'Export')
    assert raw[:2] == b'PK'
    wb = load_workbook(io.BytesIO(raw))
    assert wb.active.freeze_panes == 'A2'
    captioned = ae._as_xlsx(_ROWS, 'Export', caption='Hello')
    wb2 = load_workbook(io.BytesIO(captioned))
    assert wb2.active.freeze_panes == 'A3'


def test_session_file_meta_protocol_one_nudge():
    assert '__title__' in ae.SESSION_FILE_PROTOCOL
    assert '__filename_stem__' in ae.SESSION_FILE_PROTOCOL
    assert 'JSON' not in ae.SESSION_FILE_PROTOCOL
    assert '__title__' in ae.SESSION_FILE_META_PROTOCOL
    assert 'SAME data' in ae.SESSION_FILE_META_PROTOCOL
    assert 'assembled by the chat client' in ae.SESSION_FILE_META_PROTOCOL
    src = engine_source()
    assert 'SESSION_FILE_META_PROTOCOL' in src
    assert 'export_meta_nudged' in src
    assert 'has_export_meta' in src
    assert 'waiting_meta' in src


def test_clip_data_from_payload_is_json_rows():
    payload = {
        'data': _ROWS,
        '__title__': 'Mejores clientes de Sevilla',
        '_secret': 'no',
    }
    clip = ae.clip_data_from_payload(payload)
    assert clip['title'] == 'Mejores clientes de Sevilla'
    assert clip['rows'] == [
        {'Name': 'Alpha', 'Total': 10},
        {'Name': 'Beta', 'Total': 20},
    ]
    assert ae.clip_data_from_payload({'data': []}) is None
    assert ae.clip_data_from_payload(None, rows=_ROWS)['rows'][0]['Name'] == 'Alpha'


def test_engine_done_carries_clip_data_not_canned_phrase():
    src = engine_source()
    assert 'clip_data_from_payload' in src
    assert "['clip_data']" in src or '"clip_data"' in src
    assert 'The download card is on this turn.' not in src
    assert 'export_clip_data' in src
    # C8N1: empty bubble + session chip is success; Chatboo must not paint
    # "The model returned no content" over a good PDF.
    assert 'assistant_files/clip_data' in src
    assert 'returned no content' in src
    # Fast-path table (icon, not «pásame excel») must ship clip so the
    # client can attach excel_formulas to HTML-scraped sheets.
    idx = src.find("tool_name='skill_fast_path'")
    assert idx != -1
    chunk = src[idx:idx + 3600]
    assert '_clip_data_from_payload' in chunk
    assert 'clip_data=' in chunk
    assert 'def _done_event(' in src
    assert 'clip_data=None' in src


def test_clip_from_tables_keeps_formula_map():
    clip = ae.clip_data_from_payload({
        'tables': [{'title': 'ABC', 'data': [
            {'Ingresos': 10, 'Mano de obra': 3, 'Resultado': 7},
        ]}],
        '__excel_formulas__': {'Resultado': '={Ingresos}-{Mano de obra}'},
    })
    assert clip['excel_formulas'] == {
        'Resultado': '={Ingresos}-{Mano de obra}',
    }
    assert clip['rows'][0]['Resultado'] == 7


def test_pdf_and_excel_two_kinds_xlsx_not_duplicated():
    parsed = ae.parse_requested_export('pdf y excel')
    assert parsed and not parsed['refused']
    assert [s['kind'] for s in parsed['formats']] == ['pdf', 'xlsx']
    parsed2 = ae.parse_requested_export('pdf, xlsx y excel')
    assert [s['kind'] for s in parsed2['formats']] == ['pdf', 'xlsx']
    assert parsed2['format'] == 'pdf'
    assert not ae.is_refused_export('pdf y excel')
    assert not ae.is_refused_export('pdf, xlsx y excel')


def test_client_fulfill_pending_word_pdf_html_not_excel():
    captured = []

    def persist(raw, filename, mimetype):
        captured.append(filename)
        return {
            'name': filename,
            'url': '/web/content/%s' % (len(captured) + 3),
            'mimetype': mimetype,
            'size': len(raw),
        }

    out = ae.apply_requested_exports(
        'un word y un excel',
        rows=_ROWS,
        persist=persist,
        payload={'data': _ROWS, '__title__': 'Ventas'},
        client_fulfill=True,
    )
    assert out['acted']
    pending = [c for c in out['chips'] if c.get('pending')]
    assert len(pending) == 1
    assert pending[0]['fulfill'] == 'doc'
    assert pending[0].get('url') in (None, '', '#')
    assert any(n.endswith('.xlsx') for n in captured)
    assert not any(n.endswith('.doc') for n in captured)
    html = ae.apply_requested_exports(
        'un html',
        rows=_ROWS,
        payload={'data': _ROWS},
        client_fulfill=True,
    )
    assert html['acted']
    assert html['chips'][0]['pending'] is True
    assert html['chips'][0]['fulfill'] == 'html'
    assert ae.CLIENT_ASSEMBLED_KINDS == frozenset(('doc', 'pdf', 'html'))


def test_pdf_and_word_two_chips():
    parsed = ae.parse_requested_export('pdf y word')
    assert parsed['format'] == 'pdf'
    assert not parsed['refused']
    assert [s['kind'] for s in parsed['formats']] == ['pdf', 'doc']
    assert not parsed.get('refused_tokens')
    assert not ae.is_refused_export('pdf y word')
    out = ae.apply_requested_exports('pdf y word', rows=_ROWS)
    assert out['acted']
    exts = [c['name'].rsplit('.', 1)[-1] for c in out['chips']]
    assert 'doc' in exts
    if 'pdf' not in exts:
        pytest.skip('pdf serialization unavailable')
    assert len(out['chips']) == 2


def test_odt_only_still_cuts_before_tools():
    msg = 'pues entonces un .odt con los mejores clientes de sevilla'
    assert ae.is_refused_export(msg)
    out = ae.apply_requested_exports(msg, rows=_ROWS)
    assert not out['acted']
    assert out['chips'] == []


def test_apply_requested_exports_two_persists_same_stem():
    captured = []

    def persist(raw, filename, mimetype):
        captured.append((filename, mimetype, raw[:4]))
        return {
            'name': filename,
            'url': '/web/content/%s' % (len(captured) + 10),
            'mimetype': mimetype,
            'size': len(raw),
        }

    payload = {'data': _ROWS, '__title__': 'Ranking Sevilla'}
    out = ae.apply_requested_exports(
        'txt y markdown',
        rows=_ROWS,
        persist=persist,
        payload=payload,
    )
    assert out['acted']
    assert len(captured) == 2
    names = [item[0] for item in captured]
    stems = [n.rsplit('.', 1)[0] for n in names]
    exts = [n.rsplit('.', 1)[-1] for n in names]
    assert len(set(stems)) == 1
    assert stems[0]
    assert exts == ['txt', 'md']
    assert len(out['chips']) == 2
    mixed = ae.apply_requested_exports(
        'pdf y excel',
        rows=_ROWS,
        persist=persist,
        payload=payload,
    )
    pdf_excel = [
        n for n, _mt, _raw in captured[2:]
        if n.endswith('.pdf') or n.endswith('.xlsx')
    ]
    if mixed.get('acted') and len(pdf_excel) >= 2:
        stems2 = [n.rsplit('.', 1)[0] for n in pdf_excel]
        assert len(set(stems2)) == 1
        assert set(n.rsplit('.', 1)[-1] for n in pdf_excel) == {'pdf', 'xlsx'}


def test_word_tokens_and_rich_flag():
    for msg in ('un word', 'un .doc', 'pásame un docx'):
        parsed = ae.parse_requested_export(msg)
        assert parsed and not parsed['refused']
        assert parsed['kind'] == 'doc'
    assert ae.parse_requested_export('un pptx')['refused']
    assert ae.is_refused_export('un pptx')
    assert not ae.wants_rich_doc({'data': _ROWS})
    assert not ae.wants_rich_doc({
        'data': _ROWS,
        'formatted_text': '<h1>Show</h1>',
    })
    assert ae.wants_rich_doc({'__rich_doc__': True})
    assert not ae.wants_rich_doc({
        '__rich_doc__': False,
        'formatted_text': '<p>x</p>',
    })
    src = export_source()
    assert 'espectacular' not in src
    assert 'bonita' not in src
    assert 'impress' not in src
    assert not hasattr(ae, '_RICH_DOC_RE')


def test_rich_word_without_rows_uses_formatted_text():
    html = '<p>Quarterly brief with a photo.</p>'
    out = ae.apply_requested_exports(
        'word',
        rows=[],
        payload={'formatted_text': html, '__rich_doc__': True, '__title__': 'Brief'},
    )
    assert out['acted']
    text = out['raw'].decode('utf-8')
    assert 'Quarterly brief with a photo.' in text
    assert 'xmlns:w=' in text
    empty = ae.apply_requested_exports(
        'word',
        rows=[],
        payload={'formatted_text': html, '__title__': 'Brief'},
    )
    assert not empty['acted']
    no_html = ae.apply_requested_exports(
        'word',
        rows=[],
        payload={'__rich_doc__': True},
    )
    assert not no_html['acted']
    utterance = ae.apply_requested_exports(
        'un word espectacular',
        rows=_ROWS,
        payload={'data': _ROWS},
    )
    assert utterance['acted']
    table = utterance['raw'].decode('utf-8')
    assert 'Alpha' in table
    assert 'espectacular' not in table


def test_word_sanitize_strips_chart_tooltip():
    html = (
        '<div class="o_chatboo_md"><h1>Billing</h1>'
        '<div class="echarts-tooltip">'
        '<span>Importe</span><span>195,523.4</span></div>'
        '<table><tr><td>ok</td></tr></table></div>'
    )
    clean = ae._word_sanitize_html(html)
    assert 'Importe' not in clean
    assert '195,523.4' not in clean
    assert 'ok' in clean
    assert 'Billing' in clean


def test_word_image_cell_does_not_dump_url():
    raw = ae.serialize_rows(
        [{'Name': 'X', 'image_128': '/web/image/res.partner/1/image_128'}],
        'doc',
    )
    assert raw
    text = raw.decode('utf-8')
    assert '/web/image/res.partner/1/image_128' not in text


def test_skill_slash_is_not_a_named_export():
    assert ae.requested_named_format('/financial-health') is None
    assert ae.requested_named_format('/financial-health 12') is None
    assert ae.requested_named_format('/financial-health') is None
    named = ae.requested_named_format('/financial-health pdf')
    assert named and named['kind'] == 'pdf'


def test_handoff_text_is_not_the_export_utterance():
    """Engine-rewritten handoff names Markdown/HTML as medium, not a file ask."""
    class _Env:
        context = {'user_message': '/financial-health'}

    handoff = (
        'You compose the whole response UI: '
        "Markdown, HTML, the chat's native tables/charts"
    )
    trap = ae.parse_requested_export(handoff)
    assert trap and trap.get('format')
    uttered = ae.turn_export_utterance(_Env(), handoff)
    assert uttered == '/financial-health'
    assert ae.requested_named_format(uttered) is None


def test_report_outline_keeps_on_screen_when_user_asks_file():
    payload = {
        'data': _ROWS,
        'report_outline': ['## Analysis', '## Recommendations'],
    }
    assert ae.payload_has_report_outline(payload)
    assert ae.wants_on_screen_table(payload)
    assert not ae.export_hides_on_screen_table(
        '/financial-health pdf', payload,
    )
    assert not ae.payload_has_report_outline({'data': _ROWS})


def _xlsx_sheet_xml(raw):
    import io
    import zipfile
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        return zf.read('xl/worksheets/sheet1.xml').decode('utf-8')


def test_compile_excel_formula_a1_or_none():
    keys = ['a', 'b', 'c']
    assert ae.compile_excel_formula('={a}-{b}', keys, 2) == '=A2-B2'
    assert ae.compile_excel_formula('{a}-{b}', keys, 3) == '=A3-B3'
    assert ae.compile_excel_formula('=({analitica}-{mano})/2', [
        'analitica', 'mano', 'out',
    ], 2) == '=(A2-B2)/2'
    assert ae.compile_excel_formula('={missing}-{b}', keys, 2) is None
    assert ae.compile_excel_formula('=VLOOKUP({a},A:B,2)', keys, 2) is None
    assert ae.compile_excel_formula('={a}&{b}', keys, 2) is None
    assert ae.compile_excel_formula('={c}', keys, 2, target_key='c') is None
    assert ae.compile_excel_formula(
        '={Ingresos}-{Mano de obra}-{Km}',
        ['Ingresos', 'Mano de obra', 'Km', 'Resultado'],
        2,
    ) == '=A2-B2-C2'
    assert ae.compile_excel_formula(
        '={Resultado}/{Ingresos}*100',
        ['Ingresos', 'Resultado', 'Rentabilidad %'],
        3,
    ) == '=B3/A3*100'
    assert ae.excel_formulas_from_payload({
        '__excel_formulas__': {'c': '={a}-{b}', 'x': '=INDIRECT({a})'},
    }) == {'c': '={a}-{b}'}


def _assert_xlsx_formula(raw, ref, formula):
    try:
        from openpyxl import load_workbook
    except ImportError:
        assert formula.lstrip('=') in _xlsx_sheet_xml(raw)
        return
    import io
    assert load_workbook(io.BytesIO(raw)).active[ref].value == formula


def test_aoa_total_row_sums_month_columns():
    aoa = [
        ['Área', 'oct 25', 'nov 25', 'Total'],
        ['ING', 1, 10, 11],
        ['LYS', 4, 20, 24],
        ['Total', 5, 30, 35],
    ]
    formula = '={oct 25}+{nov 25}'
    payload = ae.icon_xlsx_payload([{
        'title': 'Creadas',
        'aoa': aoa,
        'formulas': {'Total': formula},
    }])
    import io
    from openpyxl import load_workbook
    raw = __import__('base64').b64decode(payload['datas'])
    ws = load_workbook(io.BytesIO(raw)).active
    assert ws['B4'].value == '=SUM(B2:B3)'
    assert ws['C4'].value == '=SUM(C2:C3)'
    assert ws['D4'].value == '=B4+C4'
    assert ws['B2'].value == 1


def test_xlsx_tfoot_sums_each_column_that_adds_up():
    rows = [
        {'a': 1, 'b': 10, 'c': 11, 'avg': 5},
        {'a': 3, 'b': 20, 'c': 23, 'avg': 7},
        {'a': 4, 'b': 30, 'c': 34, 'avg': 6, '_tfoot': True},
    ]
    formulas = {'c': '={a}+{b}'}
    xml = _xlsx_sheet_xml(_xlsx_one_sheet(rows, 'Export', formulas=formulas))
    assert '<f>SUM(A2:A3)</f><v>4.0</v>' in xml
    assert 'SUM(B2:B3)' in xml
    assert 'A4+B4' in xml
    assert 'SUM(D2:D3)' not in xml
    assert '<v>6</v>' in xml


def _cells(rows, formulas=None, caption=None):
    spec = ae._normalize_xlsx_sheets([{
        'title': 'T', 'rows': rows, 'formulas': formulas, 'caption': caption,
    }])[0]
    return {
        '%s%d' % (ae._xlsx_col_letter(col), r): (f, v)
        for (r, col), (f, v) in spec['cells'].items()
    }


_SALES = [
    {'Zona': 'N', 'Ventas': 100, 'Coste': 60, 'Margen': 40, 'Margen %': 40.0},
    {'Zona': 'S', 'Ventas': 200, 'Coste': 150, 'Margen': 50, 'Margen %': 25.0},
    {'Zona': 'E', 'Ventas': 80, 'Coste': 20, 'Margen': 60, 'Margen %': 75.0},
]


def test_derived_columns_become_formulas_without_declaring_them():
    cells = _cells([dict(r) for r in _SALES])
    assert cells['D2'] == ('=B2-C2', 40.0)
    assert cells['E4'][0] == '=D4/B4*100'
    assert cells['E4'][1] == pytest.approx(75.0)
    assert 'B2' not in cells and 'C3' not in cells


def test_total_row_is_found_by_its_numbers_in_any_language():
    rows = [dict(r) for r in _SALES] + [
        {'Zona': 'Gesamt', 'Ventas': 380, 'Coste': 230, 'Margen': 150,
         'Margen %': 39.47},
    ]
    cells = _cells(rows)
    assert cells['B5'] == ('=SUM(B2:B4)', 380.0)
    assert cells['C5'] == ('=SUM(C2:C4)', 230.0)
    assert cells['D5'][0] == '=B5-C5'
    assert cells['E5'][0] == '=D5/B5*100'


def test_subtotals_use_subtotal_so_the_grand_total_does_not_count_them_twice():
    rows = [
        {'Grupo': 'A', 'Importe': 10, 'Horas': 1},
        {'Grupo': 'A', 'Importe': 20, 'Horas': 2},
        {'Grupo': 'A', 'Importe': 30, 'Horas': 3},
        {'Grupo': '', 'Importe': 60, 'Horas': 6},
        {'Grupo': 'B', 'Importe': 5, 'Horas': 4},
        {'Grupo': 'B', 'Importe': 7, 'Horas': 1},
        {'Grupo': '', 'Importe': 12, 'Horas': 5},
        {'Grupo': '', 'Importe': 72, 'Horas': 11},
    ]
    cells = _cells(rows, caption='Partes')
    assert cells['B6'] == ('=SUBTOTAL(9,B3:B5)', 60.0)
    assert cells['B9'] == ('=SUBTOTAL(9,B7:B8)', 12.0)
    assert cells['B10'] == ('=SUBTOTAL(9,B3:B9)', 72.0)
    assert cells['C10'] == ('=SUBTOTAL(9,C3:C9)', 11.0)
    assert 'B3' not in cells


def test_a_row_that_only_happens_to_add_up_is_not_a_subtotal():
    rows = [
        {'n': 'a', 'qty': 1, 'amount': 10},
        {'n': 'b', 'qty': 2, 'amount': 20},
        {'n': 'c', 'qty': 3, 'amount': 30},
        {'n': 'd', 'qty': 4, 'amount': 40},
    ]
    cells = _cells(rows)
    assert not any(f.startswith('=SU') for f, _v in cells.values())


def test_ambiguous_or_short_columns_keep_their_values():
    two_rows = [{'a': 1, 'b': 2, 'c': 3}, {'a': 2, 'b': 3, 'c': 5}]
    assert ae.infer_excel_formulas(two_rows, ['a', 'b', 'c']) == {}
    sum_and_product = [
        {'a': 2, 'b': 2.0, 'c': 4.0},
        {'a': 3, 'b': 1.5, 'c': 4.5},
        {'a': 5, 'b': 1.25, 'c': 6.25},
    ]
    assert ae.infer_excel_formulas(sum_and_product, ['a', 'b', 'c']) == {}
    copy = [{'a': v, 'b': 0, 'c': v} for v in (1, 2, 3)]
    assert ae.infer_excel_formulas(copy, ['a', 'b', 'c']) == {}


def test_row_total_over_adjacent_month_columns():
    rows = [
        {'Área': 'X', 'ene': 1, 'feb': 2, 'mar': 3, 'Total': 6},
        {'Área': 'Y', 'ene': 4, 'feb': 0, 'mar': 1, 'Total': 5},
        {'Área': 'Z', 'ene': 2, 'feb': 2, 'mar': 2, 'Total': 6},
    ]
    assert ae.infer_excel_formulas(rows, list(rows[0])) == {
        'Total': '={ene}+{feb}+{mar}',
    }


def test_declared_formula_wins_over_inferred():
    rows = [dict(r) for r in _SALES]
    cells = _cells(rows, formulas={'Margen': '={Ventas}-{Coste}-0'})
    assert cells['D2'][0] == '=B2-C2-0'


def test_openpyxl_book_carries_the_python_result_in_each_formula_cell():
    pytest.importorskip('openpyxl')
    import io
    from openpyxl import load_workbook
    rows = [dict(r) for r in _SALES] + [
        {'Zona': 'T', 'Ventas': 380, 'Coste': 230, 'Margen': 150,
         'Margen %': 39.47},
    ]
    raw = ae._as_xlsx(rows, 'Ventas')
    live = load_workbook(io.BytesIO(raw)).active
    assert live['B5'].value == '=SUM(B2:B4)'
    assert live['D2'].value == '=B2-C2'
    seen = load_workbook(io.BytesIO(raw), data_only=True).active
    assert seen['B5'].value == 380
    assert seen['D2'].value == 40
    assert seen['E5'].value == pytest.approx(150 / 380 * 100)


def test_no_word_list_for_total_rows():
    src = export_source()
    assert "== 'Total'" not in src
    assert '_flag_total_footer' not in src


def test_xlsx_writes_declared_formula_or_value():
    rows = [{'a': 10, 'b': 3, 'c': 7}]
    formulas = {'c': '={a}-{b}'}
    ooxml = _xlsx_one_sheet(rows, 'Export', formulas=formulas)
    assert '<f>A2-B2</f>' in _xlsx_sheet_xml(ooxml)
    styled = ae._as_xlsx(rows, 'Export', formulas=formulas)
    _assert_xlsx_formula(styled, 'C2', '=A2-B2')
    broken = _xlsx_one_sheet(rows, 'Export', formulas={'c': '={missing}-{b}'})
    sheet_broken = _xlsx_sheet_xml(broken)
    assert '<f>' not in sheet_broken
    assert '<v>7</v>' in sheet_broken


def test_clip_and_icon_and_named_export_share_formula_map():
    payload = {
        'data': [{'a': 10, 'b': 3, 'c': 7}],
        '__excel_formulas__': {'c': '={a}-{b}'},
        '__title__': 'Calc',
    }
    clip = ae.clip_data_from_payload(payload)
    assert clip['excel_formulas'] == {'c': '={a}-{b}'}
    assert 'excel_formulas' not in (clip['rows'][0] or {})
    icon = ae.icon_xlsx_payload([{
        'title': 'Calc',
        'aoa': [['a', 'b', 'c'], [10, 3, 7]],
        'rows': clip['rows'],
        'formulas': clip['excel_formulas'],
    }])
    import base64
    _assert_xlsx_formula(base64.b64decode(icon['datas']), 'C2', '=A2-B2')
    captured = {}

    def persist(raw, filename, mimetype):
        captured['raw'] = raw
        return {'name': filename, 'url': '#', 'mimetype': mimetype}

    out = ae.apply_requested_exports(
        'pásame excel', payload=payload, persist=persist,
    )
    assert out['acted']
    _assert_xlsx_formula(captured['raw'], 'C2', '=A2-B2')


def test_public_rows_skip_excel_formulas_dunder():
    rows = [{
        'a': 1,
        '__excel_formulas__': {'a': '={b}'},
    }]
    public = ae.public_rows(rows)
    assert public == [{'a': 1}]


def test_xlsx_number_format_codes():
    assert ae.xlsx_number_format(2, True, 'int') == '#,##0'
    assert ae.xlsx_number_format(2, True, 'float') == '#,##0.00'
    assert ae.xlsx_number_format(2, False, 'int') == '0'
    assert ae.xlsx_number_format(2, False, 'float') == '0.00'
    assert ae.xlsx_number_format(0, True, 'float') == '#,##0'
    assert ae.xlsx_number_format(4, False, 'float') == '0.0000'
    assert ae.xlsx_number_format(99, True, 'float') == '#,##0.0000000000'
    assert ae.xlsx_number_format(-1, False, 'int') == '0'
    style = ae.xlsx_number_style()
    assert style['decimals'] == 2
    assert style['thousands'] is True
    assert style['int_format'] == '#,##0'
    assert style['float_format'] == '#,##0.00'


def test_xlsx_number_style_reads_icp():
    class Env:
        def __getitem__(self, name):
            return self

        def sudo(self):
            return self

        def get_param(self, key, default=None):
            return {
                ae.ICP_XLSX_FLOAT_DECIMALS: '4',
                ae.ICP_XLSX_THOUSANDS: 'False',
            }.get(key, default)

    style = ae.xlsx_number_style(Env())
    assert style['decimals'] == 4
    assert style['thousands'] is False
    assert style['int_format'] == '0'
    assert style['float_format'] == '0.0000'


def test_xlsx_ooxml_writes_numfmt_and_formula_style():
    style = ae.xlsx_number_style()
    raw = _xlsx_one_sheet(
        [{'a': 10, 'b': 3.14159, 'c': 7.0}],
        'Export',
        formulas={'c': '={a}-{b}'},
        number_style=style,
    )
    import io
    import zipfile
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        assert 'xl/styles.xml' in zf.namelist()
        styles = zf.read('xl/styles.xml').decode('utf-8')
        sheet = zf.read('xl/worksheets/sheet1.xml').decode('utf-8')
        rels = zf.read('xl/_rels/workbook.xml.rels').decode('utf-8')
    assert 'formatCode="#,##0"' in styles
    assert 'formatCode="#,##0.00"' in styles
    assert 'styles.xml' in rels
    assert 's="1"' in sheet
    assert 's="2"' in sheet
    assert '<f>A2-B2</f>' in sheet


def test_xlsx_openpyxl_applies_number_format():
    try:
        from openpyxl import load_workbook
    except ImportError:
        pytest.skip('openpyxl not installed')
    import io
    raw = ae._as_xlsx(
        [{'Name': 'A', 'Qty': 10, 'Rate': 1.5}],
        'Export',
        number_style=ae.xlsx_number_style(),
    )
    wb = load_workbook(io.BytesIO(raw))
    assert wb.active['B2'].number_format == '#,##0'
    assert wb.active['C2'].number_format == '#,##0.00'
    formula_raw = ae._as_xlsx(
        [{'a': 10, 'b': 3, 'c': 7}],
        'Export',
        formulas={'c': '={a}-{b}'},
        number_style=ae.xlsx_number_style(),
    )
    wb2 = load_workbook(io.BytesIO(formula_raw))
    assert wb2.active['C2'].value == '=A2-B2'
    assert wb2.active['C2'].number_format == '#,##0.00'


@pytest.mark.parametrize('writer', ['styled', 'openpyxl_plain', 'stdlib'])
def test_xlsx_photo_is_a_picture_not_its_url(monkeypatch, writer):
    """«excel con fotos» wrote /web/image/hr.employee/47/image_128 as text.

    Odoo does not ship openpyxl, and the styled writer can fail: every
    writer the engine falls back to must embed the photo.
    """
    pytest.importorskip('openpyxl')
    pil = pytest.importorskip('PIL.Image')
    import builtins
    import io
    import zipfile
    from openpyxl import load_workbook

    buf = io.BytesIO()
    pil.new('RGB', (128, 128), (200, 30, 30)).save(buf, format='PNG')
    png = buf.getvalue()

    class _Rec:
        def __init__(self, rid):
            self.rid = rid

        def exists(self):
            return self.rid == 47

        def __getitem__(self, field):
            return png if field == 'image_128' else None

    class _Model:
        def browse(self, rid):
            return _Rec(rid)

    class _Env(dict):
        pass

    env = _Env({'hr.employee': _Model()})
    rows = [
        {'id': 47, 'image_128': '/web/image/hr.employee/47/image_128'},
        {'id': 67, 'image_128': False},
    ]
    if writer == 'openpyxl_plain':
        real_fmt = ae._load_formatters()

        class _PhotosOnly:
            _pdf_is_image_ref = staticmethod(real_fmt._pdf_is_image_ref)
            _excel_photo_png = staticmethod(real_fmt._excel_photo_png)
            _excel_put_photo = staticmethod(real_fmt._excel_put_photo)
            _excel_photo_col_chars = staticmethod(real_fmt._excel_photo_col_chars)
            _excel_photo_offsets = staticmethod(real_fmt._excel_photo_offsets)
            _XLSX_IMG_ROW_PT = real_fmt._XLSX_IMG_ROW_PT
            mark_ai_workbook = staticmethod(real_fmt.mark_ai_workbook)

        _use_formatters(monkeypatch, _PhotosOnly)
    if writer == 'stdlib':
        real_import = builtins.__import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if isinstance(name, str) and name.split('.')[0] == 'openpyxl':
                raise ImportError('no openpyxl')
            return real_import(name, globals, locals, fromlist, level)

        monkeypatch.setattr(builtins, '__import__', fake_import)
    raw = ae.serialize_rows(
        rows, 'xlsx', caption='Plantilla con fotografía', env=env,
    )
    monkeypatch.undo()
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        names = zf.namelist()
        texts = ''.join(
            zf.read(n).decode('utf-8', 'ignore')
            for n in names if n.endswith('.xml')
        )
    assert ('docProps/app.xml' in names) is (writer != 'stdlib')
    assert any(n.startswith('xl/media/') for n in names)
    assert '/web/image/' not in texts
    ws = load_workbook(io.BytesIO(raw)).active
    styled = ws['A2'].fill.fgColor.rgb == '00667eea'
    assert styled is (writer == 'styled')
    assert ws['B3'].value in (None, '')
    assert ws['B4'].value in (None, '')
    assert len(ws._images) == 1
    assert ws.row_dimensions[3].height == 40
    assert ws.row_dimensions[4].height == 40, 'a row without photo keeps the height'
    marker = ws._images[0].anchor._from
    assert (marker.col, marker.row) == (1, 2)
    assert marker.colOff > 0 and marker.rowOff > 0, 'the photo is centred'


_SUM_ROWS = [
    {'name': 'A', 'invoices': 63, 'base': 121296.19999999997, 'year': 2026},
    {'name': 'B', 'invoices': 4, 'base': 60000, 'year': 2026},
    {'name': 'C', 'invoices': 1, 'base': '12,50', 'year': 2025},
]


def test_printed_rows_carry_two_decimals_like_the_chat_table():
    out = ae._printed_rows(_SUM_ROWS)
    assert [r['base'] for r in out] == ['121,296.20', '60,000.00', '12,50']
    assert [r['invoices'] for r in out] == [63, 4, 1]
    assert [r['year'] for r in out] == [2026, 2026, 2025]
    assert _SUM_ROWS[0]['base'] == 121296.19999999997, 'the source rows stay'


def test_printed_rows_use_the_user_separators(monkeypatch):
    import sys
    render = sys.modules[ae.__name__.rsplit('.', 1)[0] + '.relaxaicode_render']
    monkeypatch.setattr(
        render, 'render_context_from_env',
        lambda env, **kw: {'pk_decimal_sep': ',', 'pk_thousands_sep': '.'},
    )
    out = ae._printed_rows(_SUM_ROWS, env=object())
    assert out[0]['base'] == '121.296,20'
    monkeypatch.setattr(
        render, 'render_context_from_env',
        lambda env, **kw: {'pk_float_decimals': 3},
    )
    out = ae._printed_rows(_SUM_ROWS, env=object())
    assert [r['base'] for r in out][:2] == ['121,296.200', '60,000.000']


def test_chat_table_reads_the_decimals_from_the_render_context():
    src = render_source()
    assert "'pk_float_decimals': float_decimals" in src
    assert "decimals = ctx.get('pk_float_decimals', 2)" in src


def test_pdf_and_word_print_the_rounded_amount(monkeypatch):
    seen = {}

    class _Fmt:
        @staticmethod
        def format_data_as_pdf(data, cfg, **kw):
            seen['rows'] = data
            return b'%PDF'

    _use_formatters(monkeypatch, _Fmt)
    assert ae._as_pdf(_SUM_ROWS, 'Sales', charts=False) == b'%PDF'
    assert seen['rows'][0]['base'] == '121,296.20'
    word = ae._word_table_html(_SUM_ROWS, 'Sales')
    assert '121,296.20' in word and '19999999' not in word

