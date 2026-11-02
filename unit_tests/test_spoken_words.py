# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Words a person says live in data/spoken/*.json, never in engine Python."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from _load_addon import load_module

_ROOT = Path(__file__).resolve().parents[1]
_UTILS = _ROOT / 'common' / 'utils'


def _clear(mod):
    mod._packs.cache_clear()
    mod.words.cache_clear()
    mod.weekdays.cache_clear()


def test_a_language_is_one_file(tmp_path, monkeypatch):
    spoken = load_module('spoken_words', 'utils', 'spoken_words.py')
    for name in ('en.json', 'es.json'):
        (tmp_path / name).write_text(
            (_ROOT / 'common' / 'data' / 'spoken' / name).read_text(encoding='utf-8'),
            encoding='utf-8',
        )
    (tmp_path / 'it.json').write_text(json.dumps({
        'what': 'spoken_words',
        'help': ['aiuto'],
        'today': ['oggi'],
        'weekdays': [['lunedì'], ['martedì'], ['mercoledì'], ['giovedì'],
                     ['venerdì'], ['sabato'], ['domenica']],
    }), encoding='utf-8')
    monkeypatch.setattr(spoken, '_DIR', str(tmp_path))
    _clear(spoken)
    try:
        assert {'help', 'ayuda', 'aiuto'} <= spoken.words('help')
        assert 'oggi' in spoken.words('today')
        assert spoken.weekdays()['giovedi'] == 3
        assert spoken.weekdays()['miercoles'] == 2
    finally:
        _clear(spoken)


def test_shipped_files_cover_the_readers():
    sd = load_module('skill_dates', 'utils', 'skill_dates.py')
    friday = date(2026, 8, 7)
    assert sd.try_resolve_date('pasado mañana', friday) == date(2026, 8, 9)
    assert sd.try_resolve_date('next monday', friday) == date(2026, 8, 10)
    assert sd.is_help_like('/opciones')
    assert sd.is_help_like('¿')
    assert not sd.is_help_like('2026')


def test_engine_python_holds_no_spoken_words():
    sources = ''.join(
        (_UTILS / name).read_text(encoding='utf-8')
        for name in (
            'skill_dates.py', 'svg_download.py', 'skill_help.py',
            'skill_code_prefix.py', 'agent_engine.py',
        )
    )
    for word in ("'ayuda'", "'hoy'", "'lunes'", "'descarga'", "'pintame'", "'opciones'"):
        assert word not in sources
