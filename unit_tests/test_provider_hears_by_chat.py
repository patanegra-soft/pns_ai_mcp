# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""The provider form warns when an audio role is heard as a chat.

The warning comes from the speech probe and the role, never from a model name.
"""
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_PROVIDER = (_ROOT / 'common' / 'models' / 'ai_provider.py').read_text(encoding='utf-8')


def test_the_warning_is_the_probe_and_the_audio_role():
    body = _PROVIDER.split('def _compute_hears_by_chat', 1)[1].split('\n    def ', 1)[0]
    assert "rec.stt_support == 'chat'" in body
    assert 'rec._hears()' in body
    assert 'model_name' not in body
    assert 'model_id' not in body


def test_both_stacks_show_it_and_translate_it():
    text = 'This model hears audio as a chat'
    for stack, po in (('owl1', 'es.po'), ('owl2', 'es_ES.po')):
        view = (
            _ROOT / 'stacks' / stack / 'pns_ai_mcp' / 'views' / 'ai_provider_views.xml'
        ).read_text(encoding='utf-8')
        assert text in view
        assert "('hears_by_chat', '=', False)" in view
        catalogue = (
            _ROOT / 'stacks' / stack / 'pns_ai_mcp' / 'i18n' / po
        ).read_text(encoding='utf-8')
        assert 'Este modelo oye el audio como un chat' in catalogue
