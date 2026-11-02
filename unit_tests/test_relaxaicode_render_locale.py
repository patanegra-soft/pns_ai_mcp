# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Reproducible contract: session locale + numeric grids (pytest / t.sh --unit-only).

Covers relaxaicode HTML render without Odoo: separators, string parse, and
o_ai_num / text-end classes. If this fails, Chatboo balances come
back with a wild locale or figures stuck to the edge.
"""
from __future__ import annotations

import re
import sys

from _load_addon import load_module, render_source

render = load_module('relaxaicode_render', 'utils', 'relaxaicode_render.py')

_ES = {
    'pk_decimal_sep': ',',
    'pk_thousands_sep': '.',
    'pk_date_format': '%d/%m/%Y',
    'user_lang': 'es_ES',
}
_EN = {
    'pk_decimal_sep': '.',
    'pk_thousands_sep': ',',
    'pk_date_format': '%Y-%m-%d',
    'user_lang': 'en_US',
}

# Same shape as the trial balance (Chatboo capture).
_BALANCE_ROWS = [
    {'codigo': 1, 'cuenta': 'Grupo 1', 'debe': 69960.48, 'haber': 402093.03, 'saldo': -332132.55},
    {'codigo': 2, 'cuenta': 'Grupo 2', 'debe': 512070.48, 'haber': 444004.12, 'saldo': 68066.36},
    {'codigo': 5, 'cuenta': 'Grupo 5', 'debe': 11148960.17, 'haber': 11391328.54, 'saldo': -242368.37},
]


def test_fmt_number_es_uses_dot_thousands_comma_decimal():
    assert render._fmt_number(11148960.17, ',', '.', decimals=2) == '11.148.960,17'
    assert render._fmt_number(-332132.55, ',', '.', decimals=2) == '-332.132,55'
    assert render._fmt_number(1493.745, ',', '.', decimals=2) == '1.493,75'


def test_fmt_number_en_uses_comma_thousands_dot_decimal():
    assert render._fmt_number(11148960.17, '.', ',', decimals=2) == '11,148,960.17'
    assert render._fmt_number(-332132.55, '.', ',', decimals=2) == '-332,132.55'


def test_parse_numeric_accepts_both_locale_strings():
    es_val, es_float = render._parse_numeric('11.148.960,17')
    en_val, en_float = render._parse_numeric('11,148,960.17')
    assert es_float and en_float
    assert abs(es_val - 11148960.17) < 0.001
    assert abs(en_val - 11148960.17) < 0.001
    assert render._parse_numeric(69960.48)[0] == 69960.48
    assert render._parse_numeric(True) is None


def test_column_is_numeric_for_money_and_codes():
    assert render._column_is_numeric(_BALANCE_ROWS, 'debe')
    assert render._column_is_numeric(_BALANCE_ROWS, 'saldo')
    assert render._column_is_numeric(_BALANCE_ROWS, 'codigo')
    assert not render._column_is_numeric(_BALANCE_ROWS, 'cuenta')


def test_table_headers_are_sortable_and_tfoot_stays():
    rows = [
        {'Área': 'B', 'Ingreso': 2},
        {'Área': 'A', 'Ingreso': 1},
        {
            'Área': 'Total',
            'Ingreso': 3,
            '_tfoot': True,
            '_row_class': 'font-weight-bold',
        },
    ]
    html = render._render_table(rows, _ES)
    assert 'o_ai_th_sort' in html
    assert 'data-ai-sort-col="0"' in html
    assert 'data-ai-sort="2"' in html
    assert '<tfoot>' in html
    assert html.index('<tfoot>') > html.index('</tbody>')
    assert html.index('Total') > html.index('</tbody>')


def _ranking_with_total():
    rows = [
        {'id': i, 'Cliente': 'C%d' % i, 'Rentabilidad': float(100 - i * 10)}
        for i in range(1, 7)
    ]
    rows.append({'Cliente': 'Total', 'Rentabilidad': 390.0, '_tfoot': True})
    return rows


def test_tfoot_row_is_not_tinted_and_bold():
    rows = _ranking_with_total()
    render._tint_section_rows(rows)
    assert rows[0].get('_row_color')
    assert '_row_color' not in rows[-1]
    html = render._render_table(rows, _ES)
    foot = html[html.index('<tfoot>'):]
    assert 'font-weight:700' in foot
    assert 'font-weight:700' not in html[:html.index('<tfoot>')]


def test_tfoot_rows_are_not_counted_as_records():
    result = {
        'tables': [
            {'title': 'Grupo 1', 'data': _ranking_with_total()},
            {'title': 'Grupo 2', 'data': _ranking_with_total()},
        ],
    }
    html = render.grouped_table_html(result, '', render_context=_ES)
    assert html.count('<tfoot>') == 2
    assert '12' in re.sub(r'<[^>]+>', ' ', html[html.rindex('text-muted small'):])


def test_dataset_keeps_tfoot_row_for_excel():
    rows = [
        {'Área': 'B', 'Ingreso': 2},
        {'Área': 'A', 'Ingreso': 1},
        {'Área': 'Total', 'Ingreso': 3, '_tfoot': True},
    ]
    dataset = render._chart_dataset_rows(rows)
    assert [row['Área'] for row in dataset] == ['B', 'A', 'Total']
    assert dataset[-1]['_tfoot'] is True


def test_render_table_es_locale_and_numeric_alignment_classes():
    html = render._render_table(_BALANCE_ROWS, _ES)
    assert 'o_ai_data_table' in html
    assert 'o_ai_num' in html
    assert 'text-end' in html
    assert '11.148.960,17' in html
    assert '-332.132,55' in html
    # US format must not leak into an ES context
    assert '11,148,960.17' not in html
    # Debe header also aligned to the end
    assert re.search(r'<th[^>]*o_ai_num[^>]*>Debe</th>', html, re.I)
    assert re.search(r'<td[^>]*o_ai_num[^>]*>11\.148\.960,17</td>', html)


def test_render_table_en_locale():
    html = render._render_table(_BALANCE_ROWS, _EN)
    assert '11,148,960.17' in html
    assert '-332,132.55' in html
    assert '11.148.960,17' not in html


def test_render_table_reformats_preformatted_numeric_strings():
    """If the AST left already formatted strings, they are re-parsed to the session locale."""
    rows = [
        {'cuenta': 'A', 'importe': '1.234,56'},
        {'cuenta': 'B', 'importe': '2.000,00'},
    ]
    html = render._render_table(rows, _ES)
    assert '1.234,56' in html
    assert 'o_ai_num' in html
    html_en = render._render_table(
        [{'cuenta': 'A', 'importe': '1,234.56'}, {'cuenta': 'B', 'importe': '2,000.00'}],
        _EN,
    )
    assert '1,234.56' in html_en


def test_fallback_table_html_includes_total():
    html = render.fallback_table_html(
        {'data': _BALANCE_ROWS, 'title': 'Balance 2025'},
        summary='Balance de sumas y saldos',
        render_context=_ES,
    )
    assert html
    assert 'Total: 3 records' in html
    assert '11.148.960,17' in html


def test_painted_text_follows_the_render_language(monkeypatch):
    """``_t`` hands Odoo's ``_`` the language of ``render_context`` as its caller's ``context``."""
    import inspect
    spanish = {'Total: %d records': 'Total: %d registros', 'Open map': 'Abrir mapa'}

    def odoo_underscore(source):
        lang = inspect.currentframe().f_back.f_locals['context']['lang']
        return spanish.get(source, source) if lang == 'es_ES' else source

    monkeypatch.setattr(sys.modules[render._t.__module__], '_odoo_translate', odoo_underscore)
    rows = {'data': _BALANCE_ROWS, 'title': 'Balance 2025'}
    assert 'Total: 3 registros' in render.fallback_table_html(rows, render_context=_ES)
    assert 'Total: 3 records' in render.fallback_table_html(rows, render_context=_EN)
    card = render.maybe_attach_formatted_text(
        {'map_url': 'https://www.google.com/maps/dir/1,2/3,4'}, render_context=_ES,
    )
    assert card


def test_renderer_writes_no_spanish():
    """English msgids through ``_t``; no language picked with an ``if``."""
    src = render_source()
    for word in ("'Abrir", '>Abrir', 'registros', 'Restaurar', 'Minimizar', 'Cerrar',
                 'Arrastrar', 'Bloque', 'Mapa de', 'Mapa compartido', 'Resultados',
                 'Copiar', 'Aviso', "startswith('es')", 'pinchitos', 'Coordenadas',
                 'Miniatura', 'Vista OSM', "'sí'"):
        assert word not in src, word


def test_shared_map_hides_geo_columns_by_their_cells():
    """The column name is the skill's; the ``__coords__`` / ``__map_thumb__`` cell decides."""
    result = {
        'map_url': 'https://www.google.com/maps/dir/1,2/3,4',
        'data': [{
            'Sede': 'A',
            'Dónde': {'__coords__': True, 'lat': 1, 'lon': 2, 'text': '1,2'},
            'Vista': {'__map_thumb__': True, 'lat': 1, 'lon': 2, 'href': 'https://x'},
            'Mapa': 'texto',
            'Lat': 1,
        }],
    }
    hide = render._geo_hide_column_keys(result)
    assert hide == {'Dónde', 'Vista', 'Lat'}
    assert render._geo_hide_column_keys(dict(result, geo_coords=True, geo_thumbs=True)) == set()
    assert render._is_provider_badge_alt('OSM (7)')
    assert not render._is_provider_badge_alt('Mapa compartido (7)')


def test_apply_pajama_coloring_unique_cycles_soft_pastels():
    rows = [{'cuenta': 'G%d' % i, 'saldo': float(i)} for i in range(5)]
    render.apply_pajama_coloring(rows, unique=True)
    colors = [r['_row_color'] for r in rows]
    assert colors == list(render.PASTEL_ROW_COLORS[:5])
    assert all(c.startswith('#') and len(c) == 7 for c in colors)
    html = render._render_table(rows, _ES)
    assert 'background-color:%s' % colors[0] in html


def test_apply_pajama_coloring_zebra_two_tones():
    rows = [{'n': i} for i in range(4)]
    render.apply_pajama_coloring(rows, unique=False)
    assert rows[0]['_row_color'] == render.PASTEL_ROW_COLORS[0]
    assert rows[1]['_row_color'] == render.PASTEL_ROW_COLORS[1]
    assert rows[2]['_row_color'] == render.PASTEL_ROW_COLORS[0]


def test_quartile_tiers_are_soft_pastels():
    """Band backgrounds: soft pastels, not loud traffic lights."""
    for hex_color in (render._TIER_RED, render._TIER_GREEN, render._TIER_BLUE):
        assert hex_color.startswith('#') and len(hex_color) == 7
        # Canales altos → fondo claro (no rojo/verde saturado).
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        assert min(r, g, b) >= 0xE8


def test_table_drops_all_null_columns_and_flattens_nested_dicts():
    rows = [
        {
            'code': 1,
            'email': 'a@x.com',
            'company': {'id': 'c1', 'name': 'Acme SL', 'updatedAt': '2026-01-01'},
            'bic': None,
            'accountNumber': None,
        },
        {
            'code': 2,
            'email': 'b@x.com',
            'company': {'id': 'c1', 'name': 'Acme SL'},
            'bic': None,
            'accountNumber': None,
        },
    ]
    keys = render._table_display_keys(rows)
    assert 'id' not in keys
    assert '__model' not in keys
    assert 'bic' not in keys
    assert 'accountNumber' not in keys
    assert 'company' in keys
    assert 'email' in keys
    assert render._flatten_cell_value(rows[0]['company']) == 'Acme SL'
    html_out = render._render_table(rows, _ES)
    assert 'Acme SL' in html_out
    assert 'updatedAt' not in html_out
    assert 'BIC' not in html_out
    assert 'Accountnumber' not in html_out


def test_inline_chip_style_wraps_span_and_inherits_link_color():
    """Chip stays a badge; the description column gets the record link."""
    rows = [
        {
            'Área': 'COR',
            'Descripción': 'Correctivos',
            'Ingreso': 10,
            '__model': 'crm.team',
            'id': 35,
            '_style_Área': (
                'display:inline-block;padding:2px 6px;'
                'border:1px solid #666;border-radius:2px;'
                'font-size:0.85em;background-color:#37761D;color:#FFFFFF;'
            ),
        },
    ]
    html_out = render._render_table(rows, _ES)
    assert 'display:inline-block' in html_out
    assert 'background-color:#37761D' in html_out
    assert 'color:#FFFFFF' in html_out
    assert '<span style="' in html_out
    assert html_out.count('style="display:inline-block') == 1
    assert '>id<' not in html_out.lower()
    assert 'o_ai_namelink' in html_out
    assert 'Correctivos' in html_out
    chip_at = html_out.find('background-color:#37761D')
    link_at = html_out.find('o_ai_namelink')
    assert chip_at != -1 and link_at != -1
    # Link is not inside the chip span.
    span_end = html_out.find('</span>', chip_at)
    assert not (chip_at < link_at < span_end)


def test_cell_title_tooltip_on_td():
    """_title_<col> becomes a styled data-tip on the cell (pastel tip in CSS)."""
    rows = [
        {
            'Empleado': 'Ada',
            '01/08': 'T',
            '_style_01/08': 'font-weight:800;',
            '_title_01/08': 'T — Trabajo confirmado',
        },
    ]
    html_out = render._render_table(rows, _ES)
    assert 'data-tip="T — Trabajo confirmado"' in html_out
    assert 'o_ai_tiptarget' in html_out
    assert 'title="' not in html_out or 'title="T' not in html_out
    assert '>T</td>' in html_out


def _sorted_money_ranking():
    amounts = [5000, 4000, 3000, 2000, 1000, 500]
    return [
        {'Partner': 'P%d' % i, 'Importe': amt}
        for i, amt in enumerate(amounts)
    ]


def _kpi_label_value_rows():
    # Monotonic values on purpose — still not a peer ranking.
    return [
        {'Indicador': 'Ratio liquidez', 'Valor': 2.5},
        {'Indicador': 'Ratio endeudamiento', 'Valor': 1.8},
        {'Indicador': 'Margen bruto %', 'Valor': 1.2},
        {'Indicador': 'ROA %', 'Valor': 0.9},
        {'Indicador': 'ROE %', 'Valor': 0.4},
        {'Indicador': 'Días cobro', 'Valor': 0.2},
    ]


def _assert_tiers(rows):
    colors = {r['_row_color'] for r in rows}
    assert render._TIER_RED in colors
    assert render._TIER_BLUE in colors
    assert render.SUBTLE_ZEBRA_COLORS[0] not in colors


def test_tint_auto_quartile_on_record_ranking():
    rows = _sorted_money_ranking()
    for i, r in enumerate(rows, 1):
        r.update({'__model': 'res.partner', 'id': i})
    assert render._is_comparable_series(rows)
    render._tint_section_rows(rows)
    _assert_tiers(rows)


def test_tint_auto_quartile_on_wider_sorted_table():
    rows = _sorted_money_ranking()
    for r in rows:
        r['Ciudad'] = 'X'
    render._tint_section_rows(rows)
    _assert_tiers(rows)


def test_tint_auto_zebra_on_label_value_whatever_the_names():
    """Label+value shape is a KPI card or a ranking: the name never decides."""
    for rows in (_kpi_label_value_rows(), _sorted_money_ranking()):
        assert not render._is_comparable_series(rows)
        render._tint_section_rows(rows)
        assert rows[0]['_row_color'] == render.SUBTLE_ZEBRA_COLORS[0]
        assert rows[1]['_row_color'] == render.SUBTLE_ZEBRA_COLORS[1]


def test_renderer_has_no_column_word_lists():
    import inspect
    src = inspect.getsource(render)
    for word in ('_MONEY_HINTS', '_LABEL_COL_HINTS', "'importe'", "'fecha'", "'indicador'"):
        assert word not in src


def test_cells_format_by_value_not_by_column_name():
    ctx = {'pk_decimal_sep': ',', 'pk_thousands_sep': '.', 'pk_date_format': '%d/%m/%Y'}
    assert render._render_cell('x', '2026-10-11', ctx) == '11/10/2026'
    assert render._render_cell('x', '2026-10-11T08:30:00', ctx) == '11/10/2026'
    assert render._render_cell('date', 'tomorrow', ctx) == 'tomorrow'
    html_out = render._render_table(
        [{'x': 1200}, {'x': 12.5}], ctx,
    )
    assert '1.200,00' in html_out and '12,50' in html_out
    assert '>1.200<' in render._render_table([{'x': 1200}, {'x': 3}], ctx)


def test_tint_override_none_zebra_quartile():
    ranking = _sorted_money_ranking()
    render._tint_section_rows(ranking, result={'tint': 'none'})
    assert not any('_row_color' in r for r in ranking)

    zebra_rows = _sorted_money_ranking()
    render._tint_section_rows(zebra_rows, result={'__row_tint__': 'zebra'})
    assert zebra_rows[0]['_row_color'] == render.SUBTLE_ZEBRA_COLORS[0]
    assert zebra_rows[1]['_row_color'] == render.SUBTLE_ZEBRA_COLORS[1]

    money = _sorted_money_ranking()
    render._tint_section_rows(money, group_opts={'tint': 'quartile'})
    _assert_tiers(money)

    unsorted = _sorted_money_ranking()
    unsorted[0]['Importe'], unsorted[3]['Importe'] = 10, 99999
    render._tint_section_rows(unsorted, group_opts={'tint': 'quartile'})
    # Asked, but nothing sorted to band → zebra.
    assert unsorted[0]['_row_color'] == render.SUBTLE_ZEBRA_COLORS[0]


def test_tint_report_subtle_zebra_still_forced():
    rows = _sorted_money_ranking()
    render._tint_section_rows(rows, result={'__subtle_zebra__': True})
    assert rows[0]['_row_color'] == render.SUBTLE_ZEBRA_COLORS[0]
    assert rows[1]['_row_color'] == render.SUBTLE_ZEBRA_COLORS[1]


def test_name_link_prefers_high_cardinality_over_bucket():
    """Grouping labels (low distinct ratio) must not steal the record link."""
    rows = [
        {'__model': 'account.move', 'id': 101, 'Bucket': '1 mes', 'Label': 'DOC/1', 'Due': '2026-09-01'},
        {'__model': 'account.move', 'id': 102, 'Bucket': '1 mes', 'Label': 'DOC/2', 'Due': '2026-09-05'},
        {'__model': 'account.move', 'id': 103, 'Bucket': '2 meses', 'Label': 'DOC/3', 'Due': '2026-10-01'},
        {'__model': 'account.move', 'id': 104, 'Bucket': '2 meses', 'Label': 'DOC/4', 'Due': '2026-10-10'},
    ]
    keys = list(rows[0].keys())
    numeric = {k for k in keys if render._column_is_numeric(rows, k)}
    selected = render._select_name_link_keys(keys, rows, numeric)
    assert selected == {'Label'}
    html = render.render_result_html({'data': rows})
    assert '>DOC/1</a>' in html
    assert '>1 mes</a>' not in html
    assert '>2 meses</a>' not in html
