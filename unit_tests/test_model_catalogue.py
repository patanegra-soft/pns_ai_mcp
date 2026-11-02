# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Catalogue columns come from the gateway object, not a handwritten list."""
from __future__ import annotations

from _load_addon import load_module

cat = load_module('model_catalogue', 'utils', 'model_catalogue.py')


def test_batch_and_pro_stay_and_are_marked():
    row = cat.catalogue_fields({
        'id': 'openai/gpt-6.1-sol-pro:batch',
        'name': 'GPT-6.1 Sol Pro',
        'context_length': 1050000,
        'architecture': {
            'input_modalities': ['text', 'image'],
            'output_modalities': ['text'],
        },
        'pricing': {'prompt': '0.000002', 'completion': '0.00001'},
        'top_provider': {'max_completion_tokens': 128000},
    })
    assert row['maker'] == 'openai'
    assert row['title'] == 'GPT-6.1 Sol Pro'
    assert row['apt_batch'] is True
    assert row['apt_reasoning'] is True
    assert row['apt_conversation'] is False
    assert row['apt_vision'] is True
    assert row['apt_decision'] is False
    assert row['context_label'] == '1050000'
    assert row['max_output_label'] == '128000'
    assert row['price_in_label'] == '2'
    assert row['price_out_label'] == '10'
    assert row['modality_label'] == 'text, image → text'


def test_plain_text_model_is_conversation():
    row = cat.catalogue_fields({
        'id': 'openai/gpt-6-luna',
        'architecture': {'modality': 'text->text'},
        'pricing': {'prompt': '0.0000001', 'completion': '0.0000005',
                    'input_cache_read': '0.00000001'},
    })
    assert row['apt_conversation'] is True
    assert row['apt_batch'] is False
    assert row['apt_reasoning'] is False
    assert row['apt_vision'] is False
    assert row['price_cache_label'] == '0.01'
    assert row['maker'] == 'openai'


def test_a_choosing_driver_marks_decision_without_dropping_the_row():
    row = cat.catalogue_fields({'id': 'acme/some-router'}, chooses=True)
    assert row['apt_decision'] is True
    assert row['apt_conversation'] is False
    assert row['price_in_label'] == ''
    assert row['context_label'] == ''


def test_missing_keys_stay_empty():
    row = cat.catalogue_fields({'id': 'local-model'})
    assert row['maker'] == ''
    assert row['title'] == ''
    assert row['apt_vision'] is False
    assert row['apt_audio'] is False
    assert row['apt_transcriptions'] is False
    assert row['apt_file'] is False
    assert row['modality_label'] == ''


def test_audio_to_text_is_whisper_shaped():
    row = cat.catalogue_fields({
        'id': 'acme/ear-large',
        'architecture': {'modality': 'audio->text'},
    })
    assert row['apt_audio'] is True
    assert row['apt_transcriptions'] is True
    assert row['apt_conversation'] is False


def test_listing_url_on_openrouter_is_the_full_grid():
    from pathlib import Path
    url = cat.listing_url('https://openrouter.ai/api/v1/models')
    assert 'output_modalities=all' in url
    assert 'limit=1000' in url
    assert cat.listing_url('https://api.openai.com/v1/models') == (
        'https://api.openai.com/v1/models'
    )
    fetch = (
        Path(__file__).resolve().parents[1]
        / 'common' / 'models' / 'ai_provider.py'
    ).read_text(encoding='utf-8')
    body = fetch.split('def _refresh_model_catalogue', 1)[1].split(
        'def action_copy_model_catalogue', 1,
    )[0]
    assert 'unlink' not in body
    items_body = fetch.split('def _fetch_model_items', 1)[1].split(
        'def _refresh_model_catalogue', 1,
    )[0]
    assert 'while' not in items_body
    assert 'total_count' not in items_body


def test_browse_and_copy_refresh_first_and_there_is_no_third_button():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    fetch = (root / 'common' / 'models' / 'ai_provider.py').read_text(encoding='utf-8')
    assert 'def action_fetch_models' not in fetch
    pick = fetch.split('def action_pick_model', 1)[1].split('\n    def ', 1)[0]
    copy = fetch.split('def action_copy_model_catalogue', 1)[1].split('\n    def ', 1)[0]
    assert '_refresh_model_catalogue()' in pick
    assert '_refresh_model_catalogue()' in copy
    # No stale grid behind an error, and no "fetch first" gate.
    assert 'Fetch Models first' not in fetch
    for stack in ('owl1', 'owl2'):
        view = (
            root / 'stacks' / stack / 'pns_ai_mcp' / 'views' / 'ai_provider_views.xml'
        ).read_text(encoding='utf-8')
        assert 'action_fetch_models' not in view
        assert 'action_pick_model' in view
        assert 'action_copy_model_catalogue' in view


def test_openrouter_whisper_row_is_audio_to_transcription():
    row = cat.catalogue_fields({
        'id': 'openai/whisper-1',
        'architecture': {
            'modality': 'audio->transcription',
            'input_modalities': ['audio'],
            'output_modalities': ['transcription'],
        },
    })
    assert row['apt_audio'] is True
    assert row['apt_transcriptions'] is True
    assert row['apt_conversation'] is False


def test_chat_audio_is_not_whisper_shaped():
    row = cat.catalogue_fields({
        'id': 'acme/talk-mini',
        'architecture': {
            'input_modalities': ['text', 'audio'],
            'output_modalities': ['text', 'audio'],
        },
    })
    assert row['apt_audio'] is True
    assert row['apt_transcriptions'] is False
    assert row['apt_conversation'] is True


def test_a_slug_alone_does_not_invent_whisper():
    from pathlib import Path
    text = (
        Path(__file__).resolve().parents[1]
        / 'common' / 'utils' / 'model_catalogue.py'
    ).read_text(encoding='utf-8')
    assert 'whisper' not in text.lower()
    row = cat.catalogue_fields({'id': 'openai/whisper-1'})
    assert row['apt_audio'] is False
    assert row['apt_transcriptions'] is False
