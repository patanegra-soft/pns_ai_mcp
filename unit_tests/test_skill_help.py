# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Slash help cards + args_policy + ordinal bind (no Odoo runtime)."""
from __future__ import annotations

from _load_addon import engine_source, load_module

sh = load_module('skill_help', 'utils', 'skill_help.py')
sr = load_module('skill_runtime', 'utils', 'skill_runtime.py')


def test_normalize_args_policy():
    assert sh.normalize_args_policy('default') == 'default'
    assert sh.normalize_args_policy('ASK') == 'ask'
    assert sh.normalize_args_policy('none') == 'none'
    assert sh.normalize_args_policy('', has_params=True) == 'default'
    assert sh.normalize_args_policy(None, has_params=False) == 'default'


def test_help_markdown_includes_code_owner_and_params():
    md = sh.build_slash_help_markdown({
        'code': 'payroll',
        'name': 'Payroll',
        'description': 'Monthly payroll table',
        'arg_hint': 'mes=2026-06',
        'param_schema': (
            '{"mes": {"type": "string", "desc": "YYYY-MM", '
            '"default": "previous month"}}'
        ),
        'args_policy': 'default',
        'owner_kind': 'common',
    })
    assert '/payroll' in md
    assert 'Monthly payroll table' in md
    assert 'mes=2026-06' in md
    assert 'built-in default' in md
    assert '**Owner:**' in md
    assert 'Common' in md
    assert '**Parameters:**' in md
    assert '`mes`' in md
    assert 'YYYY-MM' in md
    assert 'previous month' in md
    assert '| Name |' not in md
    assert '**Examples:**' in md
    assert '`/payroll`' in md
    assert '`/payroll mes=2026-06`' in md
    assert 'mapped onto these parameters' in md
    assert 'o_chatboo_slash_help' not in md
    assert '<div' not in md


def test_help_markdown_shows_concept_label():
    md = sh.build_slash_help_markdown({
        'code': 'billing',
        'name': 'Billing',
        'description': 'Invoice table',
        'param_schema': (
            '{"desde_hasta": {"type": "string", "label": "Period", '
            '"desc": "YYYY or YYYY-YYYY", "default": ""}}'
        ),
        'args_policy': 'default',
        'owner_kind': 'common',
    })
    assert 'Period' in md
    assert '`desde_hasta`' in md
    assert 'YYYY or YYYY-YYYY' in md


def test_help_markdown_marks_required():
    md = sh.build_slash_help_markdown({
        'code': 'billing',
        'name': 'Billing',
        'param_schema': (
            '{"periodo": {"type": "string", "label": "Period", '
            '"desc": "YYYY", "required": true}}'
        ),
        'args_policy': 'default',
        'owner_kind': 'common',
    })
    assert 'Required' in md
    assert 'Period' in md


def test_help_markdown_splits_pipe_hints():
    md = sh.build_slash_help_markdown({
        'code': 'demo',
        'name': 'Demo',
        'arg_hint': 'ABC | ABC 2025-2026 | 2025-2026 | ?',
        'param_schema': '{"codes": {"type": "string", "desc": "CSV"}}',
        'args_policy': 'default',
        'owner_kind': 'common',
    })
    assert '`/demo`' in md
    assert '`/demo ABC`' in md
    assert '`/demo ABC 2025-2026`' in md
    assert '`/demo 2025-2026`' in md
    assert '`/demo ?`' in md
    assert '`/demo ABC | ABC 2025-2026' not in md


def test_help_html_alias_is_markdown():
    md = sh.build_slash_help_html({
        'code': 'payroll',
        'name': 'Payroll',
        'args_policy': 'default',
    })
    assert md.startswith('# /payroll')


def test_help_markdown_owner_user():
    md = sh.build_slash_help_markdown({
        'code': 'mine',
        'name': 'Mine',
        'args_policy': 'default',
        'owner_kind': 'user',
        'owner_name': 'Ada Lovelace',
    })
    assert 'Ada Lovelace' in md
    assert '**Owner:** Ada Lovelace' in md


def test_help_markdown_no_schema():
    md = sh.build_slash_help_markdown({
        'code': 'flota',
        'name': 'Fleet',
        'args_policy': 'none',
        'arg_hint': '',
    })
    assert 'No formal parameters' in md


def test_help_html_reject_and_ask():
    reject = sh.build_slash_help_html(
        {'code': 'flota', 'name': 'Fleet', 'args_policy': 'none'},
        rejected=True,
    )
    assert 'do not match' in reject
    ask = sh.build_slash_help_html(
        {'code': 'forecast', 'name': 'Forecast', 'args_policy': 'ask',
         'arg_hint': 'Seville tomorrow'},
        asking=True,
    )
    assert 'needs arguments' in ask


def test_skill_help_meta_from_record_like():
    class _Skill:
        code = 'sys_info'
        name = 'System info'
        description = 'Odoo version'
        arg_hint = ''
        param_schema = ''
        args_policy = 'none'
        owner_id = None

        def invoke_code(self):
            return 'sys-info'

    meta = sh.skill_help_meta(_Skill())
    assert meta['code'] == 'sys-info'
    assert meta['args_policy'] == 'none'
    assert meta['owner_kind'] == 'common'


def test_skill_help_meta_user_owner():
    class _User:
        name = 'Ada Lovelace'

    class _Skill:
        code = 'mine'
        name = 'Mine'
        description = ''
        arg_hint = ''
        param_schema = ''
        args_policy = 'default'
        owner_id = _User()

        def invoke_code(self):
            return 'mine'

    meta = sh.skill_help_meta(_Skill())
    assert meta['owner_kind'] == 'user'
    assert meta['owner_name'] == 'Ada Lovelace'
    assert 'Ada Lovelace' in sh.build_slash_help_markdown(meta)


def test_builtin_slash_help_meta():
    assert sh.builtin_slash_help_meta('compose-agent')['args_policy'] == 'none'
    assert sh.builtin_slash_help_meta('ayuda')['code'] == 'skills'
    assert sh.builtin_slash_help_meta('nope') is None
    assert sh.builtin_slash_help_meta('reload-skills') is None
    assert sh.builtin_slash_help_meta('mode')['code'] == 'mode'
    create = sh.builtin_slash_help_meta('create-skill')
    assert 'turn' in create['description'].lower()
    assert 'last turn' in create['description'].lower()
    assert 'wizard' in create['description'].lower()
    assert 'replaces' in create['description'].lower()
    assert 'slash-name' in create['arg_hint']
    assert 'VWVN' in create['arg_hint']
    assert 'not a skill parameter' in create['description'].lower()
    assert '? help' in create['arg_hint']
    assert create['args_policy'] == 'ask'
    delete = sh.builtin_slash_help_meta('delete-skill')
    assert '? help' in delete['arg_hint']
    rename = sh.builtin_slash_help_meta('rename-skill')
    assert '? help' in rename['arg_hint']
    edit = sh.builtin_slash_help_meta('edit-skill')
    assert edit['args_policy'] == 'ask'
    assert '? help' in edit['arg_hint']
    assert 'wizard' in edit['description'].lower()
    assert sh.builtin_slash_help_meta('set-skill-parameters') is None
    edit_md = sh.build_slash_help_markdown(edit)
    assert '`name`' in edit_md
    create_md = sh.build_slash_help_markdown(create)
    assert '`turn_id`' in create_md
    assert '`name`' in create_md
    assert '`description`' in create_md


def test_slash_list_origin_and_sort_key():
    assert sh.slash_list_origin(True, True, True) == 'mine'
    assert sh.slash_list_origin(False, True, True) == 'native'
    assert sh.slash_list_origin(False, True, False) == 'injected'
    assert sh.slash_list_origin(False, False, False) == 'extra'
    rows = [
        {'code': 'aa-sys', 'mine': False, 'factory': True, 'is_system': True},
        {'code': 'zz-inj', 'mine': False, 'factory': True, 'is_system': False},
        {'code': 'zz-mine', 'mine': True, 'factory': False, 'is_system': False},
        {'code': 'mm-extra', 'mine': False, 'factory': False, 'is_system': False},
        {'code': 'yy-mine', 'mine': True, 'factory': False, 'is_system': False},
    ]
    ordered = sorted(rows, key=sh.slash_list_sort_key)
    assert [r['code'] for r in ordered] == [
        'yy-mine', 'zz-mine', 'mm-extra', 'zz-inj', 'aa-sys',
    ]


def test_builtin_commands_markdown_walks_meta_not_skills():
    md = sh.build_builtin_commands_markdown()
    assert '**Slash commands**' in md
    for key, meta in sh.BUILTIN_SLASH_META.items():
        code = meta.get('code') or key
        assert ('`/%s`' % code) in md
        desc = (meta.get('description') or '').strip()
        if desc:
            assert desc in md
    assert 'Available skills' not in md
    assert 'list_for_agent' not in md
    assert 'ai.skill' not in md


def test_await_respects_args_policy():
    pres = {
        'formatted_text': '<div>ask</div>',
        '__return_direct__': True,
    }
    assert sr.should_await_skill_args(pres, arguments='', args_policy='ask') is True
    assert sr.should_await_skill_args(
        pres, arguments='', args_policy='default',
    ) is False
    assert sr.should_await_skill_args(
        pres, arguments='', args_policy='none',
    ) is False
    assert sr.should_await_skill_args(pres, arguments='') is False


def test_await_explicit_flag_wins_over_default_policy():
    pres = {
        'formatted_text': '<div>again</div>',
        '__await_skill_args__': True,
    }
    assert sr.should_await_skill_args(
        pres, arguments='x', args_policy='default',
    ) is True


def test_leftover_free_text_skips_kv_and_iso():
    assert sr.leftover_free_text('mes=2026-06') == ''
    assert sr.leftover_free_text('2026-06') == ''
    assert sr.leftover_free_text('año en curso') == 'año en curso'


def test_skill_args_unmapped_none_policy():
    assert sr.skill_args_unmapped('foo', {}, {}, 'none') is True
    assert sr.skill_args_unmapped('', {}, {}, 'none') is False
    assert sr.skill_args_unmapped('?', {}, {}, 'none') is False


def test_skill_args_unmapped_no_schema_is_not_a_miss():
    assert sr.skill_args_unmapped('foo bar', {}, {}, 'default') is False


def test_skill_args_unmapped_leftover_without_resolved():
    schema = {'mes': {'type': 'string'}}
    assert sr.skill_args_unmapped('asdf', {}, schema, 'default') is True
    assert sr.skill_args_unmapped(
        'mes=2026-06', {'mes': '2026-06'}, schema, 'default',
    ) is False


def test_parse_and_validate_params_reject():
    schema = {'mes': {'type': 'string'}}
    assert sr.parse_and_validate_params('{"_reject": true}', schema) == {
        '_skill_args_reject': True,
    }
    assert sr.parse_and_validate_params('{"mes": "2026-06"}', schema) == {
        'mes': '2026-06',
    }


def test_skill_args_unmapped_ignores_arguments_catch_all():
    schema = {
        'periodo': {'type': 'string'},
        'arguments': {'type': 'string'},
    }
    assert sr.skill_args_unmapped(
        'last 24 months',
        {'arguments': 'last 24 months'},
        schema,
        'default',
    ) is True
    assert sr.skill_args_unmapped(
        'last 24 months',
        {'periodo': '2024-2025', 'arguments': 'last 24 months'},
        schema,
        'default',
    ) is False


def test_skill_args_unmapped_arguments_only_schema_is_not_a_miss():
    schema = {'arguments': {'type': 'string'}}
    assert sr.skill_args_unmapped(
        'foo bar', {'arguments': 'foo bar'}, schema, 'default',
    ) is False


def test_merge_hybrid_params_reject_is_not_veto_when_formal_hit():
    schema = {
        'periodo': {'type': 'string'},
        'arguments': {'type': 'string'},
    }
    raw = 'last 24 months'
    assert sr.merge_hybrid_params(
        {'arguments': raw},
        {'_skill_args_reject': True},
        schema,
        raw,
    ) == {'_skill_args_reject': True}
    assert sr.merge_hybrid_params(
        {'periodo': '2025', 'arguments': raw},
        {'_skill_args_reject': True},
        schema,
        raw,
    ) == {'periodo': '2025', 'arguments': raw}
    merged = sr.merge_hybrid_params(
        {'arguments': raw},
        {'periodo': '2024-2025', 'arguments': None},
        schema,
        raw,
    )
    assert merged['periodo'] == '2024-2025'
    assert merged['arguments'] == raw


def test_explicit_nulls_mean_the_sentence_named_no_key():
    """All-null JSON is 'no parameter', not a failed parse. Defaults run."""
    schema = {
        'periodo': {'type': 'string', 'desc': 'YYYY. Empty = last 12 months.'},
        'codes': {'type': 'string', 'desc': 'CSV. Empty = all.'},
    }
    norm = sr.parse_and_validate_params(
        '{"periodo": null, "codes": null}', schema,
    )
    assert norm.get('_params_unset') is True
    raw = 'show every row in one table by month'
    merged = sr.merge_hybrid_params({}, norm, schema, raw)
    assert merged.get('_skill_args_reject') is not True
    assert '_params_unset' not in merged
    assert sr.merge_hybrid_params({}, None, schema, 'últimos 4 meses') == {
        '_skill_args_reject': True,
    }


def test_merge_does_not_let_defaults_mask_unmapped_leftover():
    schema = {
        'numero_de_meses': {'type': 'integer', 'default': 12},
        'anos': {'type': 'string', 'default': '(año actual)'},
    }
    raw = 'últimos 4 meses'
    assert sr.merge_hybrid_params({}, None, schema, raw) == {
        '_skill_args_reject': True,
    }
    assert sr.merge_hybrid_params({}, {}, schema, raw) == {
        '_skill_args_reject': True,
    }
    ok = sr.merge_hybrid_params({}, {'numero_de_meses': 4}, schema, raw)
    assert ok['numero_de_meses'] == 4
    assert ok['anos'] == '(año actual)'


def test_param_extraction_prompt_is_output_contract_only():
    schema = {
        'periodo': {
            'type': 'string',
            'desc': 'YYYY | YYYY-YYYY | YYYY-MM-DD..YYYY-MM-DD',
        },
        'codes': {'type': 'string', 'desc': 'CSV codes. Empty = all.'},
    }
    hint = '6 | 2025 | 2024-2025 | ytd'
    system, user = sr.build_param_extraction_prompt(
        schema, 'last 24 months', locale='es_ES', arg_hint=hint,
    )
    assert user == 'last 24 months'
    assert hint not in system
    assert 'arg_hint' not in system
    assert 'closest accepted formal value' not in system
    assert 'Output contract:' in system
    assert '"periodo"' in system
    assert '"codes"' in system
    assert 'YYYY-MM-DD..YYYY-MM-DD' in system
    assert '{"_reject": true}' in system
    assert 'day → YYYY-MM-DD' not in system
    assert 'Fill every key the leftover names' in system
    assert 'including none' not in system
    assert 'None is required' not in system
    assert 'do not copy informal' not in system
    assert 'área' not in system
    assert 'negocio' not in system


def test_param_extraction_prompt_keeps_schema_desc():
    schema = {'fecha': {'type': 'string', 'desc': 'Day YYYY-MM-DD'}}
    system, user = sr.build_param_extraction_prompt(schema, 'tomorrow')
    assert user == 'tomorrow'
    assert '"fecha"' in system
    assert 'Day YYYY-MM-DD' in system


def test_attach_schema_choices_from_named_model():
    class _Rec(object):
        def __init__(self, **kw):
            self._d = kw

        def __getitem__(self, key):
            return self._d[key]

    class _Model(object):
        def search(self, domain, limit=200):
            assert domain == [['code', '!=', False]]
            return [
                _Rec(code='ABC', name='Alpha extra', group='[ABC] Alpha group'),
                _Rec(code='XYZ', name='XYZ', group='Other long'),
                _Rec(code='LV', name='LV', group=''),
            ]

    env = {'demo.item': _Model()}
    schema = {
        'codes': {
            'type': 'string',
            'desc': 'CSV codes. Empty = all.',
            'choices_model': 'demo.item',
            'choices_domain': [['code', '!=', False]],
            'choices_code': 'code',
            'choices_label': ['name', 'group'],
        },
    }
    sr.attach_schema_choices(schema, env)
    rows = schema['codes']['choices']
    assert rows[0] == {'code': 'ABC', 'label': 'Alpha extra — Alpha group'}
    assert rows[1] == {'code': 'XYZ', 'label': 'Other long'}
    assert all(row['code'] != 'LV' for row in rows)
    system, _user = sr.build_param_extraction_prompt(
        schema, 'alpha extra and the other',
    )
    assert 'Values (code — label):' in system
    assert 'ABC — Alpha extra — Alpha group' in system
    assert 'XYZ — Other long' in system
    assert 'emit those codes (CSV)' in system
    assert ' LV' not in system
    assert 'área' not in system
    assert 'negocio' not in system


def test_attach_schema_choices_skips_code_only_and_strips_bracket():
    class _Rec(object):
        def __init__(self, **kw):
            self._d = kw

        def __getitem__(self, key):
            return self._d[key]

    class _Model(object):
        def search(self, domain, limit=200):
            return [
                _Rec(code='ABC', group='[ABC] Alpha extra'),
                _Rec(code='LV', group='LV'),
                _Rec(code='ZZ', group=''),
            ]

    schema = {
        'codes': {
            'type': 'string',
            'desc': 'CSV',
            'choices_model': 'demo.item',
            'choices_code': 'code',
            'choices_label': 'group',
        },
    }
    sr.attach_schema_choices(schema, {'demo.item': _Model()})
    assert schema['codes']['choices'] == [
        {'code': 'ABC', 'label': 'Alpha extra'},
    ]


def test_attach_schema_choices_missing_model_does_not_invent():
    schema = {
        'codes': {
            'type': 'string',
            'desc': 'CSV',
            'choices_model': 'no.such',
            'choices_code': 'code',
        },
    }
    sr.attach_schema_choices(schema, {})
    assert 'choices' not in schema['codes']


def test_schema_needs_ai_never_for_help():
    schema = {'mes': {'type': 'string'}}
    assert sr.schema_needs_ai_resolution({}, schema, '?') is False
    assert sr.schema_needs_ai_resolution({}, schema, 'ayuda') is False


def test_ordinals_bind_to_empty_schema_keys():
    schema = {'mes': {'type': 'string', 'desc': 'YYYY-MM'}}
    params, bound = sr.apply_schema_ordinals({}, schema, '2026-06')
    assert params['mes'] == '2026-06'
    assert bound['mes'] == '2026-06'


def test_ordinal_count_does_not_fill_a_year_slot():
    """A bare ``24`` is a count, not the calendar year default."""
    schema = {
        'yearall': {'type': 'integer', 'default': '{year}'},
        'months': {'type': 'integer', 'default': '12'},
    }
    params, bound = sr.apply_schema_ordinals({}, schema, '24')
    assert params['months'] == 24
    assert bound['months'] == '24'
    assert 'yearall' not in params
    year, year_bound = sr.apply_schema_ordinals({}, schema, '2026')
    assert year['yearall'] == 2026
    assert year_bound['yearall'] == '2026'
    assert 'months' not in year


def test_kv_wins_over_ordinal():
    schema = {
        'mes': {'type': 'string'},
        'top': {'type': 'integer'},
    }
    params, bound = sr.apply_schema_ordinals(
        {'mes': '2026-01'}, schema, 'mes=2026-01 30',
    )
    assert params['mes'] == '2026-01'
    assert params['top'] == 30
    assert 'mes' not in bound
    assert bound['top'] == '30'


def test_ordinals_skip_when_more_tokens_than_holes():
    schema = {
        'lugar': {'type': 'string'},
        'fecha': {'type': 'string'},
        'cities': {'type': 'array'},
    }
    params, bound = sr.apply_schema_ordinals(
        {}, schema, 'next Thursday in Seville please',
    )
    assert bound == {}
    assert 'fecha' not in params and 'cities' not in params


def test_ordinals_two_tokens_fill_lugar_and_fecha():
    """Two words are prose: the short call sees the whole phrase."""
    schema = {
        'lugar': {'type': 'string'},
        'fecha': {'type': 'string'},
        'cities': {'type': 'array'},
    }
    raw = 'Seville tomorrow'
    params, bound = sr.apply_schema_ordinals(
        {'lugar': raw}, schema, raw,
    )
    assert bound == {}
    assert 'fecha' not in params
    assert params['lugar'] == raw
    det = sr.deterministic_schema_hits(params, schema, raw)
    assert 'lugar' not in det


def test_prose_words_are_not_zipped_onto_keys():
    """Five words and five keys: nothing is bound; the phrase asks for IA."""
    schema = {
        'desde_hasta': {
            'type': 'string',
            'desc': 'YYYY or YYYY-YYYY or YYYY-MM-DD..YYYY-MM-DD.',
        },
        'ba': {'type': 'string', 'desc': 'Area codes, CSV.'},
        'vendida': {'type': 'string', 'desc': 'Stage names, CSV.'},
        'anulada': {'type': 'string', 'desc': 'Stage names, CSV.'},
        'importe': {'type': 'string', 'desc': 'presupuesto | esperado | aparte.'},
    }
    raw = 'el año pasado solo finalizadas'
    params, bound = sr.apply_schema_ordinals({}, schema, raw)
    assert bound == {}
    assert 'desde_hasta' not in params
    assert 'vendida' not in params
    kv_params, kv_bound = sr.apply_schema_ordinals({}, schema, 'vendida=Ganada')
    assert kv_params['vendida'] == 'Ganada'
    assert kv_bound == {}


def test_overlay_resolved_params_drops_the_raw_sentence():
    """Once a schema key is set, the skill must not see the original phrase."""
    params = sr.parse_skill_arguments('el año pasado solo finalizadas')
    assert params['arguments']
    out = sr.overlay_resolved_params(params, {
        'desde_hasta': '2025',
        'ba': None,
        'skill_state': {},
    })
    assert out['desde_hasta'] == '2025'
    assert out['ba'] is None
    assert out['arguments'] is None
    assert out['lugar'] is None
    assert 'arg0' not in out
    bare = sr.overlay_resolved_params(
        sr.parse_skill_arguments('hola'), {'skill_state': {}},
    )
    assert bare['arguments'] == 'hola'
    help_args = sr.overlay_resolved_params(sr.parse_skill_arguments('?'), {
        'arguments': '?',
        'lugar': '?',
        'periodo': '?',
    })
    assert help_args['arguments'] == '?'
    assert help_args['lugar'] == '?'


def test_sentence_comma_is_not_an_area_csv():
    """``pasado, solo COR`` must not bind PASADO and SOLO as area codes."""
    schema = {
        'desde_hasta': {
            'type': 'string',
            'desc': 'YYYY or YYYY-YYYY or YYYY-MM-DD..YYYY-MM-DD.',
        },
        'ba': {'type': 'string', 'desc': 'Area codes, CSV.'},
        'vendida': {'type': 'string', 'desc': 'Stage names, CSV.'},
        'anulada': {'type': 'string', 'desc': 'Stage names, CSV.'},
        'importe': {'type': 'string', 'desc': 'presupuesto | esperado | aparte.'},
    }
    raw = (
        'el año pasado, solo COR, el importe del pedido '
        'y el esperado en columnas distintas'
    )
    params, bound = sr.apply_schema_ordinals({}, schema, raw)
    assert params.get('ba') == 'COR'
    assert bound.get('ba') == 'COR'
    assert 'pasado' not in str(params.get('ba')).lower()
    assert 'solo' not in str(params.get('vendida') or '').lower()


def test_several_codes_join_the_csv_key():
    """ING LYS FOT is one CSV, not one sigla per following key."""
    schema = {
        'rango': {
            'type': 'string',
            'desc': 'YYYY or YYYY-YYYY or YYYY-MM-DD..YYYY-MM-DD.',
        },
        'codes': {'type': 'string', 'desc': 'CSV codes. Empty = all.'},
        'kind': {'type': 'string', 'desc': 'One word. Empty = both.'},
    }
    params, bound = sr.apply_schema_ordinals({}, schema, 'ABC DEF GHI')
    assert params.get('codes') == 'ABC,DEF,GHI'
    assert bound.get('codes') == 'ABC,DEF,GHI'
    assert 'kind' not in params
    one, _bound = sr.apply_schema_ordinals({}, schema, 'ABC')
    assert one.get('codes') == 'ABC'


def test_empty_leftover_skips_ai():
    schema = {'mes': {'type': 'string'}, 'sort_by': {'type': 'string'}}
    params = {'mes': '2026-06'}
    assert not sr.schema_needs_ai_resolution(
        params, schema, '2026-06', leftover='',
    )


_RANGO_CODES = {
    'rango': {
        'type': 'string',
        'desc': (
            'Period YYYY-YYYY or YYYYMMDD-YYYYMMDD. '
            'Relatives → YYYY-MM-DD..YYYY-MM-DD.'
        ),
    },
    'codes': {'type': 'string', 'desc': 'Uppercase CSV. E.g. ABC,XYZ.'},
}


def test_formal_year_range_and_codes_bind_by_shape():
    """Plan B without inference: YYYY-YYYY / uppercase CSV bind by shape."""
    cases = (
        ('2025-2026', {'rango': '2025-2026'}),
        ('ABC,XYZ', {'codes': 'ABC,XYZ'}),
        ('ABC,XYZ 2025-2026', {'codes': 'ABC,XYZ', 'rango': '2025-2026'}),
        (
            'ABC,XYZ 20251001-20260904',
            {'codes': 'ABC,XYZ', 'rango': '20251001-20260904'},
        ),
        ('20251001-20260904', {'rango': '20251001-20260904'}),
    )
    for raw, expect in cases:
        params, _bound = sr.apply_schema_ordinals({}, _RANGO_CODES, raw)
        for key, val in expect.items():
            assert params.get(key) == val, (raw, key, params)


def test_informal_period_word_binds_nothing_by_shape():
    """``ytd`` / prose is not a formal token: only inference can read it."""
    for raw in ('ytd', '2025 a 2026'):
        params, _bound = sr.apply_schema_ordinals({}, _RANGO_CODES, raw)
        assert 'rango' not in params, raw


def test_formal_lowercase_csv_spaces_and_bare_year_bind_by_shape():
    """How people actually type: abc,xyz / abc, xyz / 2026."""
    schema = {
        'rango': {
            'type': 'string',
            'desc': (
                'Period YYYY-YYYY or YYYYMMDD-YYYYMMDD. '
                'Relatives → YYYY-MM-DD..YYYY-MM-DD.'
            ),
        },
        'codes': {'type': 'string', 'desc': 'CSV codes. E.g. ABC,XYZ.'},
    }
    cases = (
        ('abc,xyz', {'codes': 'abc,xyz'}),
        ('abc, xyz', {'codes': 'abc,xyz'}),
        ('2026', {'rango': '2026'}),
        ('abc,xyz 2026', {'codes': 'abc,xyz', 'rango': '2026'}),
        ('abc, xyz 2025-2026', {'codes': 'abc,xyz', 'rango': '2025-2026'}),
        (
            'abc, def,ghi 2026',
            {'codes': 'abc,def,ghi', 'rango': '2026'},
        ),
    )
    for raw, expect in cases:
        params, _bound = sr.apply_schema_ordinals({}, schema, raw)
        for key, val in expect.items():
            assert params.get(key) == val, (raw, key, params)


def _bind(schema, raw):
    params = sr.parse_skill_arguments(raw)
    params, _bound = sr.apply_schema_ordinals(params, schema, raw)
    return sr.deterministic_schema_hits(params, schema, raw)


def test_period_token_fills_the_start_end_pair():
    schema = {
        'year': {'type': 'integer', 'desc': 'Calendar year.'},
        'start_date': {'type': 'string', 'desc': 'YYYY-MM-DD.'},
        'end_date': {'type': 'string', 'desc': 'YYYY-MM-DD.'},
    }
    det = _bind(schema, '2024-01-01..2024-06-30')
    assert (det['start_date'], det['end_date']) == ('2024-01-01', '2024-06-30')
    det = _bind(schema, '2026-02')
    assert (det['start_date'], det['end_date']) == ('2026-02-01', '2026-02-28')


def test_period_token_skips_a_key_it_does_not_fit():
    schema = {
        'mes': {'type': 'string', 'desc': 'Month YYYY-MM.'},
        'periodos': {'type': 'array', 'desc': 'YYYY-MM-DD..YYYY-MM-DD.'},
    }
    det = _bind(schema, '2024-01-01..2024-06-30')
    assert det == {'periodos': ['2024-01-01..2024-06-30']}


def test_period_token_follows_the_shape_the_contract_writes():
    schema = {
        'periodo': {'type': 'string', 'desc': 'YYYY=year, YYYY-YYYY=range.'},
    }
    assert _bind(schema, '2024') == {'periodo': '2024'}
    assert 'periodo' not in _bind(schema, '2026-07')


def test_leftover_free_text_drops_years_and_named():
    assert sr.leftover_free_text('2025 a 2026') == 'a'
    assert sr.leftover_free_text('mes=2026-07 julio') == 'julio'


def test_named_schema_params_reads_only_names():
    schema = {'umbral': {'type': 'string'}, 'periodo': {'type': 'string'}}
    assert sr.named_schema_params('umbral=4000 periodo=18', schema) == (
        {'umbral': '4000', 'periodo': '18'}, True,
    )
    assert sr.named_schema_params('umbral=4000', schema) == (
        {'umbral': '4000'}, True,
    )
    assert sr.named_schema_params('umbral=6000 24', schema) == (
        {'umbral': '6000'}, False,
    )
    assert sr.named_schema_params('4000 18', schema) == ({}, False)


def test_normalize_unresolved_key_collapses_space_and_case():
    assert sr.normalize_unresolved_key('  YTD  ') == 'ytd'
    assert sr.normalize_unresolved_key('año   pasado') == sr.normalize_unresolved_key(
        'AÑO PASADO'
    )
    assert sr.normalize_unresolved_key('   ') == ''
    assert sr.normalize_unresolved_key(None) == ''


def test_placeholder_help_and_rows_need_author():
    assert sr.is_placeholder_skill_help('')
    assert sr.is_placeholder_skill_help('  ')
    assert sr.is_placeholder_skill_help('Facturación', 'Facturación')
    assert sr.is_placeholder_skill_help('facturacion', 'Facturacion')
    assert sr.is_placeholder_skill_help('acme-an-rentabilidad pmcz', 'acme-an-rentabilidad')
    assert sr.is_placeholder_skill_help('acme-an-rentabilidadpmcz', 'acme-an-rentabilidad')
    assert sr.is_placeholder_skill_help('PMCZ')
    assert not sr.is_placeholder_skill_help('Invoices for a period')
    assert not sr.is_placeholder_skill_help(
        'Página interactiva de rentabilidad', 'acme-an-rentabilidad',
    )
    assert sr.param_rows_need_author([
        {'label': 'Period', 'desc': '', 'key': ''},
    ])
    assert not sr.param_rows_need_author([
        {'label': 'Period', 'desc': 'YYYY', 'key': 'periodo'},
    ])
    assert not sr.param_rows_need_author([])


def test_capture_help_text_skips_slash_and_turn_chip():
    assert sr.capture_help_text(
        name_hint='acme-an-rentabilidad',
        user_prompt='Página de rentabilidad por provincia',
        turn_id='PMCZ',
    ) == 'Página de rentabilidad por provincia'
    assert sr.capture_help_text(
        name_hint='acme-an-rentabilidad',
        user_prompt='',
        turn_id='PMCZ',
    ) == ''
    assert sr.capture_help_text(
        catalog_help='acme-an-rentabilidad pmcz',
        name_hint='acme-an-rentabilidad',
        user_prompt='Página de rentabilidad por provincia',
        turn_id='PMCZ',
    ) == 'Página de rentabilidad por provincia'
    assert sr.help_without_turn_chips('acme-an-rentabilidad PMCZ') == (
        'acme-an-rentabilidad'
    )


def test_param_cache_payload_skips_reject_and_empty():
    assert sr.param_cache_payload({'_skill_args_reject': True}) is None
    assert sr.param_cache_payload({}) is None
    assert sr.param_cache_payload({'rango': None, 'codes': ''}) is None
    assert sr.param_cache_payload({'rango': '2026', '_x': 1}) == {'rango': '2026'}


def test_param_cache_payload_drops_relative_keys():
    assert sr.relative_param_keys({
        'periodo': '2025', '_relative': ['periodo'],
    }) == ('periodo',)
    assert sr.param_cache_payload({
        'periodo': '2025',
        'codes': 'COR',
        '_relative': ['periodo'],
    }) == {'codes': 'COR'}
    assert sr.param_cache_payload({
        'periodo': '2025',
        '_relative': ['periodo'],
    }) is None


def test_parse_keeps_relative_list():
    schema = {'periodo': {'type': 'string'}, 'codes': {'type': 'string'}}
    out = sr.parse_and_validate_params(
        '{"periodo": "2025", "codes": "COR", "_relative": ["periodo"]}',
        schema,
    )
    assert out['periodo'] == '2025'
    assert out['codes'] == 'COR'
    assert out['_relative'] == ['periodo']
    merged = sr.merge_hybrid_params({}, out, schema, 'año pasado COR')
    assert merged['periodo'] == '2025'
    assert '_relative' not in merged


def test_extraction_prompt_marks_required_and_relative():
    schema = {
        'periodo': {
            'type': 'string',
            'desc': 'YYYY',
            'required': True,
        },
        'codes': {'type': 'string', 'desc': 'CSV'},
    }
    system, _user = sr.build_param_extraction_prompt(schema, 'año pasado')
    assert 'Required keys: "periodo"' in system
    assert 'None is required' not in system
    assert '"_relative"' in system
    assert 'live rankings' in system
    assert 'not a stable identifier' in system
    assert 'mando' not in system
    assert 'cliente' not in system
    assert 'Do not invent a value.' in system


def test_parse_param_cache_json_object_only():
    assert sr.parse_param_cache_json('{"rango": "2026"}') == {'rango': '2026'}
    assert sr.parse_param_cache_json('[]') is None
    assert sr.parse_param_cache_json('nope') is None
    assert sr.parse_param_cache_json('{}') == {}


def test_engine_checks_param_cache_before_hybrid_llm():
    from pathlib import Path
    src = engine_source()
    norm = src.split('def _normalize_skill_params', 1)[1].split(
        'def get_system_prompt', 1
    )[0]
    assert 'lookup_param_cache' in norm
    assert "tool_name='skill_param_cache'" in norm
    assert 'remember_param_cache' in norm
    assert 'finalize_skill_params' in norm
    assert 'finalize_skill_params({}, schema, env=self.env)' in norm
    assert 'schema_needs_ai_resolution' in norm
    assert norm.index('lookup_param_cache') < norm.index(
        'llm_json_completion_result'
    )
    assert 'named_schema_params' in norm
    assert 'HYBRID_PARAM_MAX_TOKENS' in norm
    assert 'ai_raw' in norm
    ae = engine_source()
    assert 'HYBRID_PARAM_MAX_TOKENS = 4096' in ae
    cache_src = (
        Path(__file__).resolve().parents[1]
        / 'common' / 'models' / 'ai_skill_param_cache.py'
    ).read_text(encoding='utf-8')
    assert 'registry.cursor()' in cache_src
    assert 'new_cr.commit()' in cache_src
    for stack in ('owl1', 'owl2'):
        xml = (
            Path(__file__).resolve().parents[1]
            / 'stacks' / stack / 'pns_ai_mcp' / 'views' / 'ai_skill_views.xml'
        ).read_text(encoding='utf-8')
        assert 'param_cache_ids' in xml
        assert 'Learned phrases' in xml
