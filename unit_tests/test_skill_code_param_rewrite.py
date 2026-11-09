# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Rewrite Code so it reads param_schema keys — AST + NameError gate."""
from __future__ import annotations

from _load_addon import load_module

sr = load_module('skill_runtime', 'utils', 'skill_runtime.py')

_HARDCODED = (
    "partners = env['res.partner'].search([])\n"
    "result = {'data': [], '__return_direct__': True}\n"
)

_READS_LOCATIONS = (
    'try:\n'
    '    locations = locations\n'
    'except NameError:\n'
    '    locations = None\n'
    "partners = env['res.partner'].search([])\n"
    "if locations:\n"
    "    partners = partners.filtered(lambda p: True)\n"
    "result = {'data': [], '__return_direct__': True}\n"
)

_SCHEMA = {
    'locations': {
        'type': 'string',
        'desc': 'CSV of places.',
        'default': '*',
    },
}
_SCHEMA_OPTIONAL = {'locations': {'type': 'string', 'desc': 'CSV of places.'}}


def test_unread_keys_from_hardcoded_code():
    assert sr.schema_keys_unread_by_code(_SCHEMA, _HARDCODED) == ['locations']
    assert sr.schema_keys_unread_by_code(_SCHEMA, _READS_LOCATIONS) == []
    assert sr.schema_keys_unread_by_code(
        '{"locations":{"type":"string","default":"*"}}', _HARDCODED,
    ) == ['locations']
    assert sr.schema_keys_unread_by_code({}, _HARDCODED) == []
    assert sr.schema_keys_unread_by_code(_SCHEMA_OPTIONAL, _HARDCODED) == []


def test_parse_strips_markdown_fences():
    fenced = '```python\n%s```' % _READS_LOCATIONS
    assert sr.parse_rewritten_skill_code(fenced) == _READS_LOCATIONS.strip()
    assert sr.parse_rewritten_skill_code('') == ''


def test_accept_requires_nameerror_and_ast():
    assert sr.accept_rewritten_code(_READS_LOCATIONS, _SCHEMA)
    assert sr.accept_rewritten_code(
        '```python\n%s```' % _READS_LOCATIONS, _SCHEMA,
    )
    assert sr.accept_rewritten_code(_HARDCODED, _SCHEMA) == ''
    assert sr.accept_rewritten_code('def (', _SCHEMA) == ''
    assert sr.accept_rewritten_code(
        'try:\n    other = other\nexcept NameError:\n    other = None\n',
        _SCHEMA,
    ) == ''


def test_inject_unread_param_reads_prepends_nameerror():
    out = sr.inject_unread_param_reads(_HARDCODED, _SCHEMA)
    assert out.startswith('try:\n    locations = locations\nexcept NameError:')
    assert sr.schema_keys_unread_by_code(_SCHEMA, out) == []
    assert sr.inject_unread_param_reads(_READS_LOCATIONS, _SCHEMA) == _READS_LOCATIONS


def test_turn_literal_assign_does_not_keep_the_sandbox_out():
    code = (
        'try:\n'
        '    yearall = yearall\n'
        'except NameError:\n'
        '    yearall = None\n'
        'yearall = 2026\n'
        'months = 12\n'
        "result = {'data': [], '__return_direct__': True}\n"
    )
    schema = {
        'yearall': {'type': 'integer', 'default': '{year}'},
        'months': {'type': 'integer', 'default': '12'},
    }
    out = sr.bind_code_to_schema_params(code, schema)
    assert 'yearall = yearall' in out
    assert 'yearall = None' in out
    assert 'yearall = 2026' not in out
    assert 'months = 12' not in out
    assert sr.drop_schema_literal_assigns(
        "yearall = yearall\nyearall = 2026\n", ['yearall'],
    ) == 'yearall = yearall\n'


def test_split_page_html_keeps_query_head():
    query = "date_from = '2025-10-21'\nresult = {'data': []}\n"
    tail = (
        '\n_page_template = "<html>huge</html>"\n'
        'page_html(_page_template, result, "T")\n'
    )
    head, rest = sr.split_page_html_skill_code(query + tail)
    assert 'date_from' in head
    assert 'huge' not in head
    assert '_page_template' in rest
    assert sr.split_page_html_skill_code(query) == (query, '')


def test_page_url_is_not_a_slash_param():
    schema = {
        'page_url': {'type': 'string', 'desc': 'Empty if absent.'},
        'year': {'type': 'integer', 'default': '{year}'},
    }
    assert sr.drop_result_param_keys(schema) == {
        'year': {'type': 'integer', 'default': '{year}'},
    }
    assert sr.schema_keys_unread_by_code(schema, _HARDCODED) == ['year']


def test_rewrite_prompt_names_unread_keys_only():
    system, user = sr.build_code_param_rewrite_prompt(
        _HARDCODED, _SCHEMA, 'incluir / excluir places',
    )
    assert 'locations' in system
    assert 'does not read yet' in system
    assert 'NameError' in system
    assert 'else 12' in system
    assert '_page_title' in system
    assert 'incluir / excluir places' in user
    assert _HARDCODED.strip() in user
    assert 'mejores-clientes' not in system
    assert 'customer_rank' not in system
    assert 'customer_rank' not in user


def test_bind_gives_params_a_place_in_query_and_title():
    code = (
        'from dateutil.relativedelta import relativedelta\n'
        'from datetime import date\n'
        'end = date.today()\n'
        'start = end + relativedelta(months=-12)\n'
        'year_from = date(2026, 1, 1)\n'
        "result = {'data': []}\n"
        '\n_page_template = "<html>huge</html>"\n'
        '_page_title = "Informe 12 meses"\n'
        'page_html(_page_template, result, _page_title)\n'
    )
    schema = {
        'yearall': {'type': 'integer', 'default': '{year}'},
        'months': {'type': 'integer', 'default': '12'},
    }

    class _Env(object):
        user = type('U', (), {'name': 'Ada'})()
        company = type('C', (), {'name': 'PNS', 'vat': ''})()

    out = sr.bind_code_to_schema_params(code, schema, _Env())
    assert 'months = months' in out
    assert 'yearall = yearall' in out
    assert 'relativedelta(months=-months)' in out
    assert 'date(yearall, 1, 1)' in out
    assert 'huge' in out
    assert '% (months,)' in out
    assert '_page_title = "Informe 12 meses"' not in out
    assert sr.schema_params_need_place(code, schema, _Env())
    assert not sr.schema_params_need_place(out, schema, _Env())


def test_unused_keys_without_default_are_ignored():
    schema = {
        'locations': {'type': 'string', 'desc': 'CSV of places.'},
        'months': {'type': 'integer', 'default': '12'},
        'notes': {'type': 'string'},
    }
    assert sr.schema_keys_that_need_place(schema, _HARDCODED) == ['months']
    out = sr.inject_unread_param_reads(_HARDCODED, schema)
    assert 'months = months' in out
    assert 'locations = locations' not in out
    assert 'notes = notes' not in out
    assert sr.accept_rewritten_code(_HARDCODED, _SCHEMA_OPTIONAL)


def test_count_literal_only_in_its_slot_not_every_twelve():
    code = (
        'from dateutil.relativedelta import relativedelta\n'
        'end = date.today()\n'
        'start = end + relativedelta(months=-12)\n'
        'if n > 12:\n'
        '    n = 12\n'
        'm = int(months) if months else 12\n'
        '_page_title = "Informe 12 meses"\n'
    )
    schema = {'months': {'type': 'integer', 'default': '12'}}
    out = sr.bind_code_to_schema_params(code, schema)
    assert 'relativedelta(months=-months)' in out
    assert 'if n > 12:' in out
    assert 'n = 12' in out
    assert 'else months' in out
    assert '_page_title = "Informe 12 meses"' not in out


def test_query_head_keeps_title_out_of_the_html():
    query = "rows = []\nresult = {'data': rows}\n"
    tail = (
        '_page_template = "<html>huge</html>"\n'
        '_page_title = "Informe"\n'
        'page_html(_page_template, result, _page_title)\n'
    )
    head, rest = sr.query_head_for_param_rewrite(query + tail)
    assert 'rows' in head
    assert '_page_title' in head
    assert 'huge' not in head
    assert '_page_template' in rest


def test_bind_turns_iso_window_into_the_months_param():
    code = (
        "date_from = '2025-11-01'\n"
        "date_to = '2026-10-31'\n"
        "lines = env['account.analytic.line'].search([\n"
        "    ('date', '>=', date_from),\n"
        "    ('date', '<=', date_to),\n"
        "])\n"
        "result = {\n"
        "    'data': [],\n"
        "    'title': 'Rentabilidad (Últimos 12 meses)',\n"
        "}\n"
        '_page_title = "Rentabilidad (Últimos 12 meses)"\n'
    )
    schema = {
        'year': {'type': 'integer', 'default': '{year}'},
        'months': {'type': 'integer', 'default': '12'},
    }
    out = sr.bind_code_to_schema_params(code, schema)
    assert 'months = months' in out
    assert "date_from = '2025-11-01'" not in out
    assert "date_to = '2026-10-31'" not in out
    assert 'int(months)' in out
    assert 'if year:' in out
    assert 'int(year)' in out
    assert '_end = today' in out
    assert "title': 'Rentabilidad (Últimos 12 meses)'" not in out
    assert '% (months,)' in out
    assert 'if n > 12' not in out
    again = sr.bind_code_to_schema_params(out, schema)
    assert again == out
    assert not sr.schema_params_need_place(out, schema)


def test_bind_turns_any_iso_window_into_the_months_param():
    """A captured Jan–Feb must not freeze the slash; months/year are the slot."""
    code = (
        "date_from = '2025-01-01'\n"
        "date_to = '2025-02-28'\n"
        "result = {'data': [], 'title': 'Rentabilidad 2025'}\n"
    )
    schema = {
        'year': {'type': 'integer', 'default': ''},
        'months': {'type': 'integer', 'default': '12'},
    }
    out = sr.bind_code_to_schema_params(code, schema)
    assert "date_from = '2025-01-01'" not in out
    assert "date_to = '2025-02-28'" not in out
    assert 'if year:' in out
    assert 'int(months)' in out
    assert 'int(year)' in out
    three = (
        "date_from = '2026-07-01'\n"
        "date_to = '2026-10-01'\n"
        "result = {'data': []}\n"
    )
    only_months = sr.bind_code_to_schema_params(
        three, {'months': {'type': 'integer', 'default': '12'}},
    )
    assert "date_from = '2026-07-01'" not in only_months
    assert 'int(months)' in only_months
    assert 'if year:' not in only_months


def test_bind_uses_year_for_a_calendar_year_iso_window():
    code = (
        "date_from = '2026-01-01'\n"
        "date_to = '2026-12-31'\n"
        "result = {'data': []}\n"
    )
    schema = {
        'year': {'type': 'integer', 'default': '{year}'},
        'months': {'type': 'integer', 'default': '12'},
    }

    class _Env(object):
        user = type('U', (), {'name': 'Ada'})()
        company = type('C', (), {'name': 'PNS', 'vat': ''})()

    out = sr.bind_code_to_schema_params(code, schema, _Env())
    assert "date_from = '2026-01-01'" not in out
    assert 'int(year)' in out
    assert '%04d-01-01' in out
    assert 'if year:' in out
    assert 'int(months)' in out


def test_bind_rewrites_inline_iso_search_dates():
    import ast

    code = (
        "lines = env['account.move'].search([\n"
        "    ('date', '>=', '2025-11-01'),\n"
        "    ('date', '<=', '2026-10-31'),\n"
        "])\n"
        "result = {'data': []}\n"
    )
    schema = {'months': {'type': 'integer', 'default': '12'}}
    out = sr.bind_code_to_schema_params(code, schema)
    assert "'2025-11-01'" not in out
    assert "'2026-10-31'" not in out
    assert 'int(months)' in out
    assert 'date_from' in out
    ast.parse(out)
    assert not out.startswith('    if ')
    assert out.split('lines = env', 1)[0].rstrip().endswith('date_to = _end.strftime(\'%Y-%m-%d\')')
    commented = (
        "teams = []\n"
        "# Analytic lines 2025-01-01 to 2026-10-31\n"
        "lines = env['account.analytic.line'].search([\n"
        "    ('date', '>=', '2025-01-01'),\n"
        "    ('date', '<=', '2026-10-31'),\n"
        "])\n"
        "result = {'data': []}\n"
    )
    both = {
        'year': {'type': 'integer', 'default': '{year}'},
        'months': {'type': 'integer', 'default': '12'},
    }
    out2 = sr.bind_code_to_schema_params(commented, both)
    ast.parse(out2)
    assert 'if year:' in out2
    assert "    if year:" not in out2.split('lines = env', 1)[0]
    assert out2.index('if year:') < out2.index('lines = env')
    assert "'2025-01-01'" not in out2


def test_rewrite_uses_conversation_not_decision():
    import re
    from pathlib import Path
    from _load_addon import skill_source
    skill = skill_source()
    block = re.split(
        r'\n    (?:@|def )', skill.split('def _rewrite_code_for_params', 1)[1], maxsplit=1,
    )[0]
    assert "need='conversation'" in block
    assert "need='decision'" not in block
    assert '._choose(' not in block
    assert 'fit_decision' not in block
    assert 'schema_params_need_place' in block
    assert 'query_head_for_param_rewrite' in block
    wiz = (
        Path(__file__).resolve().parents[1]
        / 'common' / 'wizard' / 'skill_capture_wizard.py'
    ).read_text(encoding='utf-8')
    resolve = wiz.split('def _resolve_param_provider', 1)[1].split(
        '\n    def ', 1,
    )[0]
    assert "need='conversation'" in resolve
