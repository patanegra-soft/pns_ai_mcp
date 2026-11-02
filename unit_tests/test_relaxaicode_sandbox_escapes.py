# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Red-team suite for the relaxaicode sandbox (box A).

Security TDD: each corpus payload (_sandbox_escape_corpus) is a real
escape technique. Both host defense layers are checked (no Odoo):
  · static AST → validate_relaxaicode_source_ast rejects dangerous literals.
  · runtime    → guarded_getattr / guarded_import close what the AST misses
                 (dynamically built names, dynamic imports).
Legitimate cases must still pass (anti false-positive).
"""
from __future__ import annotations

import pytest

from _load_addon import load_module
import _sandbox_escape_corpus as corpus

v = load_module('validators', 'controllers', 'validators.py')
v_base = load_module('validators_base', 'controllers', 'validators_base.py')
cb = load_module('context_builder', 'controllers', 'context_builder.py')


# ─────────────────────────── AST layer ───────────────────────────
@pytest.mark.parametrize('code', corpus.AST_BLOCKED)
def test_ast_blocks_escape_payload(code):
    """PAAP I9: The AST refuses sandbox escape payloads."""
    good, err, _write = v.validate_relaxaicode_source_ast(code)
    assert not good, "El AST debería RECHAZAR este payload de fuga:\n%s" % code
    assert err


@pytest.mark.parametrize('code', corpus.AST_ALLOWED)
def test_ast_allows_legit_code(code):
    good, err, _write = v.validate_relaxaicode_source_ast(code)
    assert good, "El AST NO debería rechazar código legítimo:\n%s\nerr=%s" % (code, err)


def test_sandbox_print_is_allowed_and_discards():
    good, err, _write = v.validate_relaxaicode_source_ast(
        "print('look', 1)\nresult = {'n': 2}\n"
    )
    assert good, err
    ns = {'__builtins__': {'print': cb.sandbox_print}}
    exec("print('secret', 1)\nresult = {'n': 2}\n", ns)
    assert ns['result'] == {'n': 2}
    assert cb.sandbox_print('x', file=object(), flush=True) is None


def test_shared_denylist_is_single_source():
    # The runtime denylist is EXACTLY the AST one (a single place).
    assert cb.DANGEROUS_ATTR_NAMES is v_base.DANGEROUS_ATTR_NAMES or \
        set(cb.DANGEROUS_ATTR_NAMES) == set(v_base.DANGEROUS_ATTR_NAMES)
    # Key families present (regression if someone deletes them).
    for name in ('__class__', '__globals__', 'f_back', 'f_globals',
                 'tb_frame', '__subclasses__', '__mro__', 'cr', '_cr'):
        assert name in v_base.DANGEROUS_ATTR_NAMES


def test_shared_import_allowlists_are_single_source():
    assert set(cb.RELAXAICODE_SAFE_MODULES) == set(v_base.RELAXAICODE_SAFE_MODULES)
    assert set(cb.RELAXAICODE_DANGEROUS_MODULES) == set(v_base.RELAXAICODE_DANGEROUS_MODULES)


def _runtime_namespace():
    """Same builtins and module facades the sandbox hands to ``exec``."""
    import calendar
    import collections
    import datetime
    import io
    import json
    import uuid
    ns = {'__builtins__': {
        '__import__': cb.guarded_import,
        'getattr': cb.guarded_getattr,
        'isinstance': isinstance,
        'len': len,
        'str': str,
    }}
    for mod in (calendar, collections, datetime, io, json, uuid):
        ns[mod.__name__] = cb.safe_module(mod)
    ns['date'] = datetime.date
    ns['timedelta'] = datetime.timedelta
    return ns


@pytest.mark.parametrize('code', corpus.RUNTIME_MODULE_ESCAPES)
def test_safe_module_never_hands_out_another_module(code):
    with pytest.raises((AttributeError, ImportError)):
        exec(code, _runtime_namespace())


@pytest.mark.parametrize('code', corpus.RUNTIME_MODULE_ALLOWED)
def test_safe_module_keeps_legit_use(code):
    ns = _runtime_namespace()
    exec(code, ns)
    assert ns['result'] is not None


def test_every_module_in_the_safe_context_goes_through_its_facade():
    import inspect
    import re
    src = inspect.getsource(cb.build_safe_context)
    local_modules = re.findall(r'^\s+import (\w+) as (_\w+)$', src, re.M)
    assert local_modules
    for _name, alias in local_modules:
        assert not re.search(r":\s*%s\s*,\s*$" % re.escape(alias), src, re.M), (
            "%s reaches the sandbox without safe_module()" % alias)


def test_inspect_import_hint_points_to_orm():
    good, err, _write = v.validate_relaxaicode_source_ast(
        "import inspect\nresult = inspect.signature(env['acl.role'].create)\n"
    )
    assert not good
    assert 'inspect' in err.lower()
    assert 'inspect_result' not in err
    assert '_fields' in err or 'ORM' in err
    with pytest.raises(ImportError) as ei:
        cb.guarded_import('inspect')
    assert '_fields' in str(ei.value) or 'ORM' in str(ei.value)


def test_dir_and_registry_hints_point_to_orm():
    good, err, _w = v.validate_relaxaicode_source_ast(
        "result = [m for m in dir(type(env['res.partner']))]\n"
    )
    assert not good
    assert '_fields' in err
    good, err, _w = v.validate_relaxaicode_source_ast(
        "result = sorted(env.registry.models.keys())\n"
    )
    assert not good
    assert 'ir.model' in err


def test_nested_defaultdict_lambda_is_a_bucket_not_a_sort_key():
    """IXPI: grouping rows must not be reported as an unsafe sort key."""
    good, err, _w = v.validate_relaxaicode_source_ast(
        "from collections import defaultdict\n"
        "bucket = defaultdict(lambda: defaultdict(lambda: {'n': 0.0}))\n"
        "rows = [{'Saldo €': 2.0}, {'Saldo €': 1.0}]\n"
        "rows = sorted(rows, key=lambda x: x['Saldo €'], reverse=True)\n"
        "result = {'data': rows, 'n': bucket}\n"
    )
    assert good, err
    good, err, _w = v.validate_relaxaicode_source_ast(
        "bucket = defaultdict(lambda: env['res.partner'].search([]))\n"
        "result = {'n': len(bucket)}\n"
    )
    assert not good
    assert 'SORT_KEY' in (err or '')


def test_type_dunder_name_is_allowed():
    """type(x).__name__ is a plain string label — common LLM idiom, safe."""
    good, err, _w = v.validate_relaxaicode_source_ast(
        "x = {'a': 1}\nresult = type(x).__name__\n"
    )
    assert good, err


def test_other_dunder_name_still_blocked():
    good, err, _w = v.validate_relaxaicode_source_ast(
        "def f():\n    return 1\nresult = f.__name__\n"
    )
    assert not good
    assert '__name__' in err
    assert 'type(value).__name__' in err
    good, err, _w = v.validate_relaxaicode_source_ast(
        "result = getattr(type([]), '__name__')\n"
    )
    assert not good
    good, err, _w = v.validate_relaxaicode_source_ast(
        "result = [].__class__.__name__\n"
    )
    assert not good


# ─────────────────────── runtime: guarded_getattr ───────────────────────
class _Dummy:
    """Object with ORM-like attributes to test allowed getattr."""
    name = 'x'
    display_name = 'x'
    _name = 'res.dummy'
    _fields = {}
    id = 1

    def __init__(self):
        setattr(self, '__last_update', 'now')


@pytest.mark.parametrize('attr', corpus.GETATTR_BLOCKED_NAMES)
def test_guarded_getattr_blocks_dangerous(attr):
    """PAAP I9: Getattr cannot hand out a dangerous attribute."""
    with pytest.raises(AttributeError):
        cb.guarded_getattr((), attr)


def test_guarded_getattr_blocks_dynamically_built_name():
    # H1: the name is built at runtime → the AST does not see it, guarded_getattr does.
    built = '__cla' + 'ss__'
    with pytest.raises(AttributeError):
        cb.guarded_getattr((), built)


def test_guarded_getattr_blocks_any_dunder():
    # Any unknown __x__ is blocked too (generic defence).
    with pytest.raises(AttributeError):
        cb.guarded_getattr((), '__init__')


@pytest.mark.parametrize('attr', corpus.GETATTR_ALLOWED_NAMES)
def test_guarded_getattr_allows_orm_attrs(attr):
    d = _Dummy()
    # Must not raise because of sandbox policy (if the attribute does not exist,
    # the real getattr would raise AttributeError; that is why we pass a default).
    cb.guarded_getattr(d, attr, None)


def test_guarded_getattr_default_and_passthrough():
    d = _Dummy()
    assert cb.guarded_getattr(d, 'name') == 'x'
    assert cb.guarded_getattr(d, 'no_existe', 'fallback') == 'fallback'


@pytest.mark.parametrize('attr', ('create', 'write', 'unlink', 'copy'))
def test_guarded_getattr_blocks_orm_mutators(attr):
    """A6: getattr(rec, 'wr'+'ite') cannot hand out the ORM mutator."""
    with pytest.raises(AttributeError) as ei:
        cb.guarded_getattr(object(), attr)
    assert 'mutator' in str(ei.value).lower() or attr in str(ei.value)


@pytest.mark.parametrize('code', corpus.AST_REQUIRES_WRITE)
def test_ast_marks_obfuscated_orm_write(code):
    """PAAP I2: A write hidden behind getattr leaves the read box for a plan."""
    good, err, requires_write = v.validate_relaxaicode_source_ast(code)
    assert good, "Debe ser AST-válido pero requires_write:\n%s\nerr=%s" % (code, err)
    assert requires_write, "Debe marcar requires_write:\n%s" % code


def test_shared_orm_write_attrs_are_single_source():
    assert set(cb.RELAXAICODE_ORM_WRITE_ATTRS) == set(v_base.RELAXAICODE_ORM_WRITE_ATTRS)
    assert set(cb.RELAXAICODE_SIDE_EFFECT_METHODS) == set(
        v_base.RELAXAICODE_SIDE_EFFECT_METHODS)


@pytest.mark.parametrize('name', ('resolve_execute', 'execute_plan_now',
                                  'cleanup_expired', 'cleanup_stuck_state'))
def test_methods_with_own_cursor_are_not_reachable_by_name(name):
    """getattr/attrgetter/methodcaller cannot hand out a method that commits."""
    built = name[:3] + name[3:]
    with pytest.raises(AttributeError):
        cb.guarded_getattr(object(), built)
    with pytest.raises(AttributeError):
        cb.guarded_attrgetter(built)
    with pytest.raises(AttributeError):
        cb.guarded_methodcaller(built)


# ─────────────────────── runtime: guarded_import ───────────────────────
@pytest.mark.parametrize('mod', corpus.IMPORT_BLOCKED)
def test_guarded_import_blocks_dangerous(mod):
    with pytest.raises(ImportError):
        cb.guarded_import(mod)


@pytest.mark.parametrize('mod', corpus.IMPORT_ALLOWED)
def test_guarded_import_allows_safe(mod):
    assert cb.guarded_import(mod) is not None


def test_guarded_import_urllib_parse_requires_fromlist():
    # `import urllib.parse` (no fromlist) forbidden; `from urllib.parse import x` ok.
    with pytest.raises(ImportError):
        cb.guarded_import('urllib.parse')
    assert cb.guarded_import('urllib.parse', {}, {}, ['quote']) is not None


def test_ast_blocks_ai_context_and_points_to_get_context():
    payloads = [
        "recs = env['ai.context'].search([('code', 'ilike', 'self')])\n"
        "result = [{'id': r.id, 'code': r.code, 'content': r.content} for r in recs]",
        "recs = env.get('ai.context').search([])\nresult = recs",
        "result = env['ai.' + 'context'].search([])",
        "recs = env.with_context(active_test=False)['ai.context'].browse(1)\n"
        "result = recs",
    ]
    for code in payloads:
        good, err, _write = v.validate_relaxaicode_source_ast(code)
        assert not good, "Debería rechazar ORM de ai.context:\n%s" % code
        assert 'get_context' in (err or '')
        assert 'ai.context' in (err or '')
        assert v_base.ast_error_code(err) == 'CONTEXT_CATALOGUE'


def test_ast_blocks_ai_skill_and_does_not_nudge_get_context():
    payloads = [
        "recs = env['ai.skill'].search([])\n"
        "result = [{'code': r.code, 'body': r.code_body} for r in recs]",
        "recs = env.get('ai.skill').search([])\nresult = recs",
        "result = env['ai.' + 'skill'].search([])",
        "recs = env.with_context(active_test=False)['ai.skill'].browse(1)\n"
        "result = recs",
    ]
    for code in payloads:
        good, err, _write = v.validate_relaxaicode_source_ast(code)
        assert not good, "Debería rechazar ORM de ai.skill:\n%s" % code
        assert 'ai.skill' in (err or '')
        assert 'get_context' not in (err or '')
        assert v_base.ast_error_code(err) == 'SKILL_CATALOGUE'


def test_ast_blocks_ai_trusted_action_and_does_not_nudge_get_context():
    payloads = [
        "recs = env['ai.trusted.action'].search([])\n"
        "result = [{'code': r.code} for r in recs]",
        "recs = env.get('ai.trusted.action').search([])\nresult = recs",
        "result = env['ai.' + 'trusted.action'].search([])",
        "recs = env.with_context(active_test=False)['ai.trusted.action']"
        ".browse(1)\nresult = recs",
    ]
    for code in payloads:
        good, err, _write = v.validate_relaxaicode_source_ast(code)
        assert not good, "Debería rechazar ORM de ai.trusted.action:\n%s" % code
        assert 'ai.trusted.action' in (err or '')
        assert 'get_context' not in (err or '')
        assert 'safe_plan_request' in (err or '')
        assert v_base.ast_error_code(err) == 'ACTION_CATALOGUE'


def test_ast_still_allows_business_orm():
    good, err, _write = v.validate_relaxaicode_source_ast(
        "recs = env['res.partner'].search([], limit=5)\n"
        "result = [r.name for r in recs]\n"
    )
    assert good, err


def test_guarded_sandbox_env_blocks_catalogue_models():
    class _DummyEnv(object):
        def __init__(self):
            self.user = type('U', (), {'name': 'x'})()
            self._models = {'res.partner': 'PARTNER'}

        def __getitem__(self, model):
            return self._models[model]

        def get(self, model, default=None):
            return self._models.get(model, default)

        def __contains__(self, model):
            return model in self._models

        def sudo(self):
            return self

    wrapped = cb.GuardedSandboxEnv(_DummyEnv())
    assert wrapped['res.partner'] == 'PARTNER'
    assert 'res.partner' in wrapped
    with pytest.raises(KeyError) as ei_ctx:
        wrapped['ai.context']
    assert 'get_context' in str(ei_ctx.value)
    with pytest.raises(KeyError) as ei_api:
        wrapped['ai.api.server']
    assert 'api_call' in str(ei_api.value)
    with pytest.raises(KeyError) as ei_skill:
        wrapped['ai.skill']
    assert 'ai.skill' in str(ei_skill.value)
    assert 'get_context' not in str(ei_skill.value)
    with pytest.raises(KeyError) as ei_act:
        wrapped['ai.trusted.action']
    assert 'ai.trusted.action' in str(ei_act.value)
    assert 'safe_plan_request' in str(ei_act.value)
    assert 'get_context' not in str(ei_act.value)
    assert wrapped.user.name == 'x'


@pytest.mark.parametrize('code', corpus.AST_PRIVILEGE_BLOCKED)
def test_ast_refuses_another_identity(code):
    good, err, _write = v.validate_relaxaicode_source_ast(code)
    assert not good, "Debería rechazar el cambio de identidad:\n%s" % code
    assert v_base.ast_error_code(err) == 'PRIVILEGE'


@pytest.mark.parametrize('name', sorted(v_base.RELAXAICODE_PRIVILEGE_ATTRS))
def test_guarded_getattr_refuses_another_identity(name):
    with pytest.raises(AttributeError):
        cb.guarded_getattr(object(), name)


@pytest.mark.parametrize('code', corpus.RUNTIME_PRIVILEGE_ESCAPES)
def test_runtime_refuses_another_identity(code):
    class _Rec(object):
        def sudo(self):
            raise AssertionError('sudo reached')

        def with_user(self, _uid):
            raise AssertionError('with_user reached')

    class _Env(object):
        def __getitem__(self, _model):
            return _Rec()

        def sudo(self):
            raise AssertionError('env.sudo reached')

        def __call__(self, *a, **k):
            raise AssertionError('env(...) reached')

    ns = _runtime_namespace()
    import operator
    ns['operator'] = cb.safe_module(operator)
    ns['env'] = cb.GuardedSandboxEnv(_Env())
    with pytest.raises((AttributeError, TypeError)):
        exec(code, ns)


def test_sandbox_env_keeps_with_context():
    class _Env(object):
        def with_context(self, **_k):
            return self

        def __getitem__(self, model):
            return model

    wrapped = cb.GuardedSandboxEnv(_Env())
    assert wrapped.with_context(active_test=False)['res.partner'] == 'res.partner'


def test_datetime_aliases_are_wired_in_safe_context():
    """Contract: date/timedelta/timezone are injected (docs use date.today()).

    The LLM writes a bare date(...); the sandbox must
    resolve it without NameError.
    """
    import datetime as _dt
    import inspect

    src = inspect.getsource(cb.build_safe_context)
    for name in ('date', 'timedelta', 'timezone'):
        needle = "'%s': _datetime.%s" % (name, name)
        assert needle in src, "Falta precarga de %s en build_safe_context" % name
    # Sanity: the aliases are the real stdlib types
    assert _dt.date.today()
    assert _dt.timedelta(days=1).days == 1


# ───────────────────── Fixed names built from pieces ─────────────────────
@pytest.mark.parametrize('code', (
    "x = env['res.partner']\nresult = getattr(x, '__cla' + 'ss__')",
    "result = ('{0.__cla' + 'ss__}').format(1)",
    "env = context.get('e' + 'nv')\nresult = 1",
))
def test_ast_blocks_a_fixed_name_built_from_pieces(code):
    good, err, _write = v.validate_relaxaicode_source_ast(code)
    assert not good and err.startswith('[PROHIBITED')


# ───────────────────── Allowed modules reassigned ─────────────────────
@pytest.mark.parametrize('code', (
    "json = 1\nresult = json",
    "for row in [1]:\n    re = row\nresult = 1",
    "re, x = 1, 2\nresult = x",
    "math: int = 1\nresult = math",
    "string += 'a'\nresult = 1",
))
def test_ast_rejects_assigning_to_an_allowed_module(code):
    good, err, _write = v.validate_relaxaicode_source_ast(code)
    assert not good
    assert err.startswith('[PROHIBITED] Do not assign to ')
    assert v_base.ast_error_code(err) is None


def test_ast_allows_comparing_an_allowed_module():
    good, err, _write = v.validate_relaxaicode_source_ast(
        "import json\njson == 1\nresult = {'n': 1}\n"
    )
    assert good, err