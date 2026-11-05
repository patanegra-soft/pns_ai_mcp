# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""The sandbox never holds the database connection.

Report of 2026-11-04: ``env.args[0]`` is the raw cursor (Odoo sets
``self.args = (cr, uid, context, su)``), so ``ROLLBACK`` left box A's READ ONLY
transaction and an ``UPDATE`` + ``COMMIT`` went through. The names were
public, so no denylist had them. Two fences close it whatever the name:

* ``GuardedSandboxEnv`` is an allowlist: an env attribute nobody listed raises.
* Every attribute read (literal ones too, rewritten by ``compile_sandbox``)
  refuses a cursor, connection, raw Environment or registry, as the object
  read from and as the value returned.

The doubles below carry the same class names and modules as Odoo and psycopg2
and record SQL instead of running it.
"""
from __future__ import annotations

import ast
import operator
import re
from pathlib import Path

import pytest

from _load_addon import load_module
import _sandbox_escape_corpus as corpus

v = load_module('validators', 'controllers', 'validators.py')
cb = load_module('context_builder', 'controllers', 'context_builder.py')

_COMMON = Path(__file__).resolve().parents[1] / 'common'


def _cls(module, name, **attrs):
    attrs['__module__'] = module
    return type(name, (object,), attrs)


class _Doubles(object):
    def __init__(self):
        self.sql = []
        sql = self.sql

        def _log(_self, query, params=None):
            sql.append(query)

        def _noop(_self, *a, **k):
            sql.append('<transaction call>')

        self.PgConnection = _cls(
            'psycopg2.extensions', 'connection', commit=_noop, rollback=_noop)
        self.PgCursor = _cls('psycopg2.extensions', 'cursor', execute=_log)
        self.Cursor = _cls(
            'odoo.sql_db', 'Cursor', execute=_log, commit=_noop, rollback=_noop)
        pg_cursor = self.PgCursor()
        pg_cursor.connection = self.PgConnection()

        class DbError(Exception):
            pass

        class Record(object):
            def __init__(self, env, model, name):
                self.env, self._model, self.name = env, model, name

        class Records(object):
            def __init__(self, env, model):
                self.env, self._model = env, model

            def search(self, domain, **_kw):
                if any(term[0] == 'boom' for term in domain):
                    err = DbError('invalid input syntax for type date')
                    err.cursor = pg_cursor
                    raise err
                return []

            def search_read(self, _domain=None, _fields=None, **_kw):
                return [{'name': 'ACME'}]

        def _env_init(env, cr, uid, context, su=False):
            env.cr, env.uid, env.context, env.su = env.args = (
                cr, uid, dict(context), su)
            env.all = [env]
            env.cache = {}
            env.brand_new_attr = 'added by the next Odoo release'
            env.user = Record(env, 'res.users', 'Juan Pérez')
            env.company = Record(env, 'res.company', 'ACME')

        self.Environment = _cls(
            'odoo.api', 'Environment',
            __init__=_env_init,
            __getitem__=lambda env, model: Records(env, model),
            ref=lambda env, xmlid, raise_if_not_found=True: Record(env, 'x', 'ACME'),
            with_context=lambda env, *a, **k: env,
        )
        self.raw_env = self.Environment(self.Cursor(), 7, {'lang': 'es_ES'})


@pytest.fixture
def doubles():
    return _Doubles()


def _namespace(d):
    import datetime
    builtins = {
        'getattr': cb.guarded_getattr,
        '__import__': cb.guarded_import,
        cb.SANDBOX_ATTR_BUILTIN: cb.sandbox_attr,
    }
    for name in ('type', 'str', 'len', 'list', 'dict', 'tuple', 'range',
                 'isinstance', 'sorted', 'any'):
        builtins[name] = __builtins__[name] if isinstance(__builtins__, dict) \
            else getattr(__builtins__, name)
    return {
        '__builtins__': builtins,
        'Exception': Exception,
        'env': cb.GuardedSandboxEnv(d.raw_env),
        'user': d.raw_env.user,
        'operator': cb.safe_module(operator),
        'datetime': cb.safe_module(datetime),
    }


def _run(code, d):
    ok, err, _write = v.validate_relaxaicode_source_ast(code)
    if not ok:
        return 'ast', err
    ns = _namespace(d)
    exec(cb.compile_sandbox(code, '<relaxaicode>'), ns, ns)
    return 'ran', ns.get('result')


# ───────────────────────── env allowlist ─────────────────────────
@pytest.mark.parametrize('name', corpus.ENV_ATTRS_BLOCKED)
def test_env_attribute_not_on_the_allowlist_is_refused(name, doubles):
    with pytest.raises(AttributeError):
        getattr(cb.GuardedSandboxEnv(doubles.raw_env), name)


def test_env_attribute_added_by_a_future_odoo_is_refused(doubles):
    assert doubles.raw_env.brand_new_attr
    with pytest.raises(AttributeError):
        cb.GuardedSandboxEnv(doubles.raw_env).brand_new_attr


@pytest.mark.parametrize('name', corpus.ENV_ATTRS_ALLOWED)
def test_env_allowlist_names_reach_the_env(name):
    class _Env(object):
        pass

    raw = _Env()
    setattr(raw, name, 'value of %s' % name)
    assert getattr(cb.GuardedSandboxEnv(raw), name) == 'value of %s' % name


# ───────────────────── the escapes, end to end ─────────────────────
@pytest.mark.parametrize('code', corpus.RUNTIME_DB_HANDLE_ESCAPES)
def test_no_public_name_reaches_the_database(code, doubles):
    try:
        outcome, value = _run(code, doubles)
    except (AttributeError, TypeError, KeyError):
        outcome, value = 'refused', None
    assert outcome in ('ast', 'refused'), (
        'ESCAPA — el código llegó al final:\n%s\nresult=%r' % (code, value))
    assert doubles.sql == [], 'SQL que habría llegado a Postgres: %r' % doubles.sql


@pytest.mark.parametrize('code', corpus.RUNTIME_ATTR_ALLOWED)
def test_ordinary_code_still_runs(code, doubles):
    outcome, value = _run(code, doubles)
    assert outcome == 'ran', value
    assert value is not None


# ───────────────────── the fences, one by one ─────────────────────
def test_handles_are_recognised_by_class_and_by_instance(doubles):
    for handle in (doubles.raw_env, doubles.Cursor(), doubles.PgCursor(),
                   doubles.PgConnection()):
        assert cb.is_db_handle(handle)
        assert cb.is_db_handle(type(handle))
    assert not cb.is_db_handle(cb.GuardedSandboxEnv(doubles.raw_env))
    assert not cb.is_db_handle(doubles.raw_env.user)
    assert not cb.is_db_handle({'cursor': 1})


def test_a_handle_already_in_hand_gives_nothing(doubles):
    cursor = doubles.Cursor()
    with pytest.raises(AttributeError):
        cb.guarded_getattr(cursor, 'exe' + 'cute')
    with pytest.raises(AttributeError):
        cb.sandbox_attr(cursor, 'execute')
    with pytest.raises(AttributeError):
        cb.guarded_methodcaller('exe' + 'cute', 'ROLLBACK')(cursor)
    with pytest.raises(AttributeError):
        cb.guarded_attrgetter('execute')(cursor)
    assert doubles.sql == []


def test_attrgetter_reads_through_the_sandbox_on_each_call(doubles):
    err = Exception('x')
    err.cursor = doubles.PgCursor()
    getter = cb.guarded_attrgetter('cursor')
    with pytest.raises(AttributeError):
        getter(err)


def test_a_str_subclass_keeps_its_format_with_plain_fields_only(doubles):
    class Markupish(str):
        pass

    assert cb.sandbox_attr(Markupish('<b>{0}</b>'), 'format')('x') == '<b>x</b>'
    with pytest.raises(AttributeError):
        cb.sandbox_attr(Markupish('{0.name}'), 'format')(doubles.raw_env.user)


def test_compile_sandbox_rewrites_reads_and_keeps_stores():
    code = "d = {}\nx = d.get\nresult = x('k')\n"
    tree = ast.parse(code)
    rewritten = cb._AttributeReadsThroughSandbox().visit(tree)
    assert not [n for n in ast.walk(rewritten)
                if isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Load)]
    ns = {'__builtins__': {cb.SANDBOX_ATTR_BUILTIN: cb.sandbox_attr}}
    exec(cb.compile_sandbox(code, '<t>'), ns, ns)
    assert ns['result'] is None


def test_compile_sandbox_refuses_the_reserved_name():
    with pytest.raises(SyntaxError):
        cb.compile_sandbox(
            "%s = getattr\nresult = 1" % cb.SANDBOX_ATTR_BUILTIN, '<t>')


def test_every_exec_of_sandbox_code_compiles_through_the_sandbox():
    """An exec built on plain compile() would read attributes unchecked."""
    runners = []
    for path in _COMMON.rglob('*.py'):
        text = path.read_text(encoding='utf-8')
        if re.search(r'^\s*exec\(', text, re.M):
            runners.append(path)
            assert 'compile_sandbox(' in text, path
            assert not re.search(r'exec\(\s*compile\(', text), path
    assert runners


def test_every_exec_of_sandbox_code_runs_in_box_a():
    """Skills included: the caller's cursor can write, box A cannot."""
    for path in _COMMON.rglob('*.py'):
        text = path.read_text(encoding='utf-8')
        if re.search(r'^\s*exec\(', text, re.M):
            assert re.search(r'_get_readonly_env\(|open_readonly_env\(', text), path
            assert re.search(r'\.close\(\)', text), path


def test_the_engine_never_takes_env_back_from_the_sandbox_namespace():
    """``safe_context['env']`` is the wrapper (no ``cr``) and the code can rebind it."""
    reads = re.compile(r"""(?<!`)\b(?:safe_context|ctx)(?:\.get\(|\[)\s*['"]env['"]""")
    for path in (_COMMON / 'controllers').glob('*.py'):
        for n, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            assert not reads.search(line), '%s:%d %s' % (path.name, n, line.strip())
