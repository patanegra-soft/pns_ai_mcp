# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""relaxaicode decides by the shape of code and values, never by the words."""
from __future__ import annotations

import pytest

from _load_addon import load_module, relaxaicode_source

prepare = load_module('relaxaicode_prepare', 'controllers', 'relaxaicode_prepare.py')
rows = load_module('relaxaicode_rows', 'controllers', 'relaxaicode_rows.py')

_PNG = 'iVBORw0KGgo' + 'A' * 400


@pytest.mark.parametrize('code', [
    'result = "No se puede acceder a la base de datos"',
    'result = "Impossibile accedere ai dati"',
    'result = "データにアクセスできません"',
    '# 環境が使えないので別の方法\nresult = []',
    '# proviamo un altro metodo\nresult = {}',
    'result = None',
])
def test_message_or_nothing_without_env_is_preventive(code):
    reply = prepare._preventive_code_response(code)
    assert reply and reply['__preventive_code_error__'] is True


@pytest.mark.parametrize('code', [
    '# let\'s try a different method\nresult = env["res.partner"].search_count([])',
    'try:\n    n = env["res.partner"].search_count([])\nexcept Exception:\n    n = 0\nresult = "No se puede" if not n else n',
    'result = previous_result',
    'result = f"Total: {len(previous_result)}"',
    'result = [{"a": 1}]',
    'x = 1',
    'result = "start"\nresult += str(len(previous_result))',
])
def test_query_or_computation_is_not_preventive(code):
    assert prepare._preventive_code_response(code) is None


class _Field:
    def __init__(self, type_):
        self.type = type_


class _Rec:
    _name = 'res.partner'
    _fields = {'name': _Field('char'), 'image_128': _Field('binary')}

    def __init__(self, rec_id):
        self.id = rec_id

    def exists(self):
        return self

    def __bool__(self):
        return True

    def __getitem__(self, fname):
        return {'name': 'Ana', 'image_128': _PNG}[fname]


class _Model:
    def browse(self, rec_id):
        return _Rec(rec_id)


class _Env:
    def __contains__(self, name):
        return name == 'res.partner'

    def __getitem__(self, name):
        return _Model()


@pytest.mark.parametrize('alias', ['foto', 'retrato', '写真', 'image_128'])
def test_picture_column_is_found_by_its_value(alias):
    result = [{'id': 7, '__model': 'res.partner', 'name': 'Ana', alias: _PNG}]
    rows._postprocess_images(result, env=_Env())
    assert result[0][alias] == '/web/image/res.partner/7/image_128'
    assert result[0]['name'] == 'Ana'


def test_no_locale_words_in_relaxaicode():
    src = relaxaicode_source()
    for word in ("'foto'", 'No se puede', 'No es posible', "let's try",
                 'La consulta provocó', 'imagen omitida'):
        assert word not in src, word
