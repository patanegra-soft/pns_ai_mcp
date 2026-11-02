# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Closed default tokens for every skill. Allowlist only; no sudo/eval."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from _load_addon import load_module

sr = load_module('skill_runtime', 'utils', 'skill_runtime.py')
tok = load_module('skill_param_tokens', 'utils', 'skill_param_tokens.py')

_ROOT = Path(__file__).resolve().parents[1]
_TOKEN_PY = _ROOT / 'common' / 'utils' / 'skill_param_tokens.py'
_MIXIN_PY = _ROOT / 'common' / 'models' / 'skill_param_token_legend.py'
_ENGINE = _ROOT / 'common' / 'utils' / 'engine_skills.py'


class _Rec(object):
    def __init__(self, **kw):
        for key, val in kw.items():
            setattr(self, key, val)


class _Env(object):
    user = _Rec(name='Ada Lovelace', login='ada')
    company = _Rec(name='PNS', vat='B12345678')


def test_legend_lists_only_allowlisted_tokens():
    names = tok.skill_param_token_names()
    assert names == frozenset(('year', 'today', 'ytd', 'user', 'company', 'vat'))
    text = tok.skill_param_token_legend_text()
    assert text.startswith('In Default you may write:')
    for token in names:
        assert '{%s}' % token in text
    assert '{year}-n' in text
    assert '{sudo}' not in text
    html = tok.skill_param_token_legend_html()
    assert '{ytd}' in html
    assert '<script>' not in html


def test_expand_defaults_and_unknown_stay():
    env = _Env()
    today = date.today()
    schema = {
        'year': {'type': 'string', 'default': '{year}'},
        'day': {'type': 'string', 'default': '{today}'},
        'who': {'type': 'string', 'default': '{user}'},
        'co': {'type': 'string', 'default': '{company}'},
        'tax': {'type': 'string', 'default': '{vat}'},
        'ago': {'type': 'string', 'default': '{year}-1'},
        'range': {'type': 'string', 'default': '{ytd}'},
        'jan': {'type': 'string', 'default': '{year}-01-01'},
        'bad': {'type': 'string', 'default': '{sudo} {env}'},
    }
    filled = sr.apply_schema_defaults({}, schema, env=env)
    assert filled['year'] == str(today.year)
    assert filled['day'] == today.isoformat()
    assert filled['who'] == 'Ada Lovelace'
    assert filled['co'] == 'PNS'
    assert filled['tax'] == 'B12345678'
    assert filled['ago'] == str(today.year - 1)
    assert filled['range'] == '%s..%s' % (
        date(today.year, 1, 1).isoformat(), today.isoformat(),
    )
    assert filled['jan'] == '%s-01-01' % today.year
    assert filled['bad'] == '{sudo} {env}'
    leftover = sr.apply_schema_defaults({}, schema)
    assert leftover['year'] == '{year}'
    assert sr.infer_type_from_default('{year}') == 'integer'
    assert sr.infer_type_from_default('{year}-1') == 'integer'
    assert sr.infer_type_from_default('{year}-01-01') == 'string'
    assert sr.infer_type_from_default('12') == 'integer'
    ints = sr.apply_schema_defaults(
        {},
        {'months': {'type': 'integer', 'default': '12'}},
        env=env,
    )
    assert ints['months'] == 12
    empty = sr.finalize_skill_params(
        {},
        {
            'yearall': {'type': 'integer', 'default': '{year}'},
            'months': {'type': 'integer', 'default': '12'},
        },
        env=env,
    )
    assert empty['yearall'] == today.year
    assert empty['months'] == 12


def test_finalize_expands_and_does_not_eval():
    env = _Env()
    out = sr.finalize_skill_params(
        {'label': 'Report {year} {__class__}'},
        {'label': {'type': 'string'}},
        env=env,
    )
    assert out['label'] == 'Report %s {__class__}' % date.today().year
    assert tok.expand_skill_param_text('{year.__class__}', env) == '{year.__class__}'
    assert tok.expand_skill_param_text('{year}-2', env) == str(date.today().year - 2)
    assert tok.expand_skill_param_text('{year}-0', env) == '%s-0' % date.today().year


def test_expander_and_mixin_have_no_sudo_or_eval():
    for path in (_TOKEN_PY, _MIXIN_PY):
        src = path.read_text(encoding='utf-8')
        assert '.sudo(' not in src
        assert 'sudo()' not in src
        assert 'eval(' not in src
        assert 'exec(' not in src
        assert '__import__' not in src
    mixin = _MIXIN_PY.read_text(encoding='utf-8')
    assert 'def fields_view_get' in mixin
    assert 'fill_skill_param_token_legend_arch' in mixin
    assert 'fields.Html' not in mixin
    assert 'fields.Text(' not in mixin


def test_engine_bind_passes_asking_user_env():
    src = _ENGINE.read_text(encoding='utf-8')
    assert src.count('finalize_skill_params(') >= 4
    assert 'finalize_skill_params(det or {}, schema, env=self.env)' in src
    assert 'finalize_skill_params(merged, schema, env=self.env)' in src
    assert 'finalize_skill_params({}, schema, env=self.env)' in src
    assert 'env=self.env' in src
    assert 'sudo()' not in src


def test_wizard_and_skill_form_show_the_same_legend_field():
    views = (
        _ROOT / 'common' / 'wizard' / 'skill_capture_wizard_views.xml',
        _ROOT / 'stacks' / 'owl1' / 'pns_ai_mcp' / 'views' / 'ai_skill_views.xml',
        _ROOT / 'stacks' / 'owl2' / 'pns_ai_mcp' / 'views' / 'ai_skill_views.xml',
    )
    slot = tok.SKILL_PARAM_TOKEN_LEGEND_SLOT
    for path in views:
        xml = path.read_text(encoding='utf-8')
        assert 'name="param_token_legend"' not in xml
        assert 'alert alert-info o_skill_param_token_legend' in xml
        assert slot in xml
        between = xml[
            xml.index('o_skill_param_token_legend'):xml.index('name="param_line_ids"')
        ]
        assert '<group' in between
        assert xml.index(slot) < xml.index('name="param_line_ids"')
        filled = tok.fill_skill_param_token_legend_arch(xml)
        assert slot not in filled
        assert '{year}' in filled
        assert '{ytd}' in filled
        assert 'In Default you may write:' in filled
