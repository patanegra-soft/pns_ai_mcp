# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Trainer prose → param_schema. choices_* only if the text names them."""
from __future__ import annotations

from _load_addon import load_module

sr = load_module('skill_runtime', 'utils', 'skill_runtime.py')


def test_parse_keys_without_inventing_choices():
    parsed = sr.parse_param_author_json(
        '{"keys": {"codes": {"type": "string", "desc": "CSV of codes."}}}'
    )
    assert list(parsed) == ['codes']
    assert parsed['codes']['type'] == 'string'
    assert 'choices_model' not in parsed['codes']


def test_parse_nested_choices_and_flat_fallback():
    parsed = sr.parse_param_author_json(
        '{"keys": {"codes": {"type": "string"}}, '
        '"choices": {"codes": {"model": "demo.item", "code": "x_code", '
        '"label": "group_id.name"}}}'
    )
    assert parsed['codes']['choices_model'] == 'demo.item'
    assert parsed['codes']['choices_code'] == 'x_code'
    assert parsed['codes']['choices_label'] == 'group_id.name'
    flat = sr.parse_param_author_json(
        '{"codes": {"type": "string", "desc": "CSV.", '
        '"choices_model": "demo.item", "choices_code": "x_code"}}'
    )
    assert flat['codes']['choices_model'] == 'demo.item'


def test_ground_drops_unmentioned_model():
    spec = {
        'type': 'string',
        'desc': 'CSV of codes.',
        'choices_model': 'demo.item',
        'choices_code': 'x_code',
    }
    grounded = sr.ground_choices_on_spec(
        spec, 'codes is a CSV of short codes',
    )
    assert 'choices_model' not in grounded
    assert 'choices_code' not in grounded
    assert grounded['desc'] == 'CSV of codes.'


def test_ground_keeps_named_model_and_code():
    spec = {
        'type': 'string',
        'choices_model': 'demo.item',
        'choices_code': 'x_code',
        'choices_label': 'group_id.name',
        'choices_domain': [('active', '=', True)],
    }
    text = (
        'codes from demo.item x_code, label group_id.name'
    )
    grounded = sr.ground_choices_on_spec(spec, text)
    assert grounded['choices_model'] == 'demo.item'
    assert grounded['choices_code'] == 'x_code'
    assert grounded['choices_label'] == 'group_id.name'
    assert 'choices_domain' not in grounded


def test_merge_overlays_and_keeps_other_keys():
    existing = {
        'periodo': {'type': 'string', 'desc': 'YYYY-YYYY.'},
        'codes': {'type': 'string', 'desc': 'old'},
    }
    extracted = {
        'codes': {
            'type': 'string',
            'desc': 'CSV of codes.',
            'choices_model': 'demo.item',
            'choices_code': 'x_code',
        },
    }
    merged = sr.merge_authored_param_schema(
        existing, extracted, 'codes from demo.item x_code',
    )
    assert merged['periodo']['desc'] == 'YYYY-YYYY.'
    assert merged['codes']['desc'] == 'CSV of codes.'
    assert merged['codes']['choices_model'] == 'demo.item'


def test_merge_does_not_keep_invented_choices():
    extracted = {
        'codes': {
            'type': 'string',
            'desc': 'CSV of codes.',
            'choices_model': 'demo.item',
            'choices_code': 'x_code',
        },
    }
    merged = sr.merge_authored_param_schema(
        {}, extracted, 'codes is a CSV of short codes',
    )
    assert merged['codes']['desc'] == 'CSV of codes.'
    assert 'choices_model' not in merged['codes']


def test_reject_and_skips_invalid_keys():
    assert sr.parse_param_author_json('{"_reject": true}') == {'_reject': True}
    parsed = sr.parse_param_author_json(
        '{"keys": {"not a key": {"type": "string"}, "ok": {"type": "string"}}}'
    )
    assert list(parsed) == ['ok']


def test_author_prompt_mentions_code_keys_only():
    system, user = sr.build_param_author_prompt(
        'codes are a CSV', code_keys=['codes', 'periodo'],
    )
    assert 'codes' in system
    assert 'periodo' in system
    assert 'locale en_US' in system
    assert user == 'codes are a CSV'
    assert 'demo.item' not in system


def test_author_prompt_derives_keys_from_free_prose():
    system, user = sr.build_param_author_prompt(
        'Se pueden pedir ubicaciones geográficas. Ej: sevilla y cádiz',
    )
    assert 'snake_case' in system
    assert 'not about parameters' in system
    assert 'Do not invent a model, field, or domain.' in system
    assert 'Do not invent a model, field, domain, or key.' not in system
    assert '"help"' in system
    assert user.startswith('Se pueden')


def test_parse_param_author_help():
    parsed = sr.parse_param_author_json(
        '{"keys": {"locations": {"type": "string", "desc": "cities"}}, '
        '"help": "Best customers by place."}'
    )
    assert list(parsed) == ['locations']
    assert sr.parse_param_author_help(
        '{"keys": {"locations": {"type": "string"}}, '
        '"help": "Best customers by place."}'
    ) == 'Best customers by place.'
    assert sr.parse_param_author_help('{"_reject": true}') == ''
