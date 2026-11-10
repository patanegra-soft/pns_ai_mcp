# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""The sandbox reads a provider, the log or a parameter, never the secret in it.

``ai.provider``, ``ai.agent`` and ``ir.config_parameter`` are open to the
sandbox. Their credential columns are shut one by one on the sandbox cursor
(``models/sandbox_secret_read.py``); the rule that names them lives in
``utils/sandbox_secrets.py``.
"""
from __future__ import annotations

from _load_addon import addon_file, load_module

ss = load_module('sandbox_secrets', 'utils', 'sandbox_secrets.py')
v_base = load_module('validators_base', 'controllers', 'validators_base.py')


class _Field(object):
    def __init__(self, type_='char', comodel=None, related=None, param=None):
        self.type = type_
        self.comodel_name = comodel
        self.related = related
        self.config_parameter = param


class _Model(object):
    def __init__(self, env, name, fields, secrets=()):
        self.env = env
        self._name = name
        self._fields = fields
        self._pns_secret_fields = secrets
        env[name] = self


def _env():
    env = {}
    _Model(env, 'ai.provider', {
        'name': _Field(), 'api_key': _Field(), 'context_window_tokens': _Field(),
    }, ('api_key',))
    _Model(env, 'ai.log', {
        'provider_id': _Field('many2one', 'ai.provider'),
        'prompt_tokens': _Field('integer'),
        'provider_key': _Field(related='provider_id.api_key'),
        'provider_name': _Field(related=('provider_id', 'name')),
    })
    _Model(env, 'ir.mail_server', {'smtp_pass': _Field(), 'smtp_user': _Field()})
    _Model(env, 'res.users', {
        'api_key_ids': _Field('one2many', 'res.users.apikeys'),
        'signup_token': _Field(),
    })
    _Model(env, 'ir.config_parameter', {'key': _Field(), 'value': _Field('text')})
    _Model(env, 'res.config.settings', {
        'google_maps_distance_key': _Field(param='pns_geo.google_maps_distance_key'),
        'maps_secretary_url': _Field(param='pns_geo.maps_url'),
        'wall_link': _Field(param='pns_x.wall_token'),
    })
    return env


def test_declared_and_named_columns_are_secret():
    env = _env()
    assert ss.field_is_secret(env['ai.provider'], 'api_key')
    assert ss.field_is_secret(env['ir.mail_server'], 'smtp_pass')
    assert ss.field_is_secret(env['res.users'], 'signup_token')


def test_the_rest_of_the_row_stays_readable():
    env = _env()
    assert not ss.field_is_secret(env['ai.provider'], 'name')
    assert not ss.field_is_secret(env['ai.provider'], 'context_window_tokens')
    assert not ss.field_is_secret(env['ai.log'], 'provider_id')
    assert not ss.field_is_secret(env['ai.log'], 'prompt_tokens')
    assert not ss.field_is_secret(env['ir.mail_server'], 'smtp_user')
    assert not ss.field_is_secret(env['res.users'], 'api_key_ids')
    assert not ss.field_is_secret(env['ir.config_parameter'], 'key')


def test_a_related_column_carries_the_secret_of_its_target():
    env = _env()
    assert ss.field_is_secret(env['ai.log'], 'provider_key')
    assert not ss.field_is_secret(env['ai.log'], 'provider_name')


def test_a_secret_setting_shuts_its_parameter():
    env = _env()
    settings = env['res.config.settings']
    assert ss.field_is_secret(settings, 'google_maps_distance_key')
    assert ss.field_is_secret(settings, 'wall_link')
    assert not ss.field_is_secret(settings, 'maps_secretary_url')
    keys = ss.secret_setting_params(settings)
    assert keys == {'pns_geo.google_maps_distance_key', 'pns_x.wall_token'}
    assert ss.secret_param_key('pns_x.wall_token', keys)


def test_parameter_keys():
    assert ss.secret_param_key('database.secret')
    assert ss.secret_param_key('pns_geo.google_maps_static_key')
    assert ss.secret_param_key('pns_x.custom', frozenset({'pns_x.custom'}))
    assert not ss.secret_param_key('web.base.url')
    assert not ss.secret_param_key('database.uuid')
    assert not ss.secret_param_key('pns_secretary.app_url')


def test_the_sandbox_cursor_carries_the_flag():
    class _Cr(object):
        pass

    cr = _Cr()
    assert not ss.sandbox_cursor(cr)
    setattr(cr, ss.SANDBOX_CURSOR_FLAG, True)
    assert ss.sandbox_cursor(cr)
    helpers = addon_file('controllers', 'controller_helpers.py').read_text(encoding='utf-8')
    assert 'setattr(cr, SANDBOX_CURSOR_FLAG, True)' in helpers


def test_the_guard_denial_goes_back_to_the_model_as_a_code_fix():
    """One secret column must not end the turn: the model drops it and runs again."""
    guard = addon_file('models', 'sandbox_secret_read.py').read_text(encoding='utf-8')
    assert '_COLUMN_DENIED = SECRET_DENIED_PREFIX + (' in guard
    assert '_PARAM_DENIED = SECRET_DENIED_PREFIX + (' in guard
    assert 'Do not retry another way' not in guard
    assert ss.is_secret_read_denial(
        ss.SECRET_DENIED_PREFIX + 'project.task.access_token: it holds a credential'
    )
    assert not ss.is_secret_read_denial('You are not allowed to access this document')
    assert not ss.is_secret_read_denial(None)
    failures = addon_file('controllers', 'relaxaicode_failures.py').read_text(encoding='utf-8')
    secret_branch = failures.split('is_secret_read_denial(error_msg)', 1)[1].split('# ACL / business denials', 1)[0]
    assert 'retryable=True' in secret_branch
    assert 'SECRET_DENIED_HINT' in secret_branch
    assert 'looping over _fields' in ss.SECRET_DENIED_HINT
    # The guard branch runs before the ACL stop.
    assert failures.index('is_secret_read_denial(error_msg)') < failures.index('# ACL / business denials')


def test_rows_with_a_secret_column_are_open_to_the_sandbox():
    closed = v_base.RELAXAICODE_CREDENTIAL_MODELS
    for model in ('ai.provider', 'ai.provider.model', 'ai.agent',
                  'ai.agent.provider', 'ir.config_parameter'):
        assert model not in closed, model
