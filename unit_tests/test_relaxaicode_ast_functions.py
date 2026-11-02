# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""RelaxAICode: helper defs allowed; return only inside them; limits from constants."""
from __future__ import annotations

from _load_addon import load_module

v = load_module('validators', 'controllers', 'validators.py')
v_base = load_module('validators_base', 'controllers', 'validators_base.py')
v_sort = load_module('validators_sort', 'controllers', 'validators_sort.py')


def _ok(code):
    good, err, _write = v.validate_relaxaicode_source_ast(code)
    assert good, err


def _fail(code, needle):
    good, err, _write = v.validate_relaxaicode_source_ast(code)
    assert not good
    assert needle in (err or '')


def test_module_level_def_helper_like_rc8u_allowed():
    code = """
by_partner = {}

def _add(pid, name, key, amount):
    by_partner.setdefault(pid, {'name': name, 'gross': 0.0})
    by_partner[pid][key] += amount
    return None

_add(1, 'Ada', 'gross', 10.0)
result = {'data': list(by_partner.values())}
"""
    _ok(code)


def test_return_inside_def_ok_module_level_return_forbidden():
    _ok("""
def double(x):
    return x * 2
result = double(3)
""")
    _fail("""
result = {'a': 1}
return result
""", 'module level')


def test_nested_def_depth_two_ok_three_forbidden():
    _ok("""
def outer():
    def inner():
        return 1
    return inner()
result = outer()
""")
    # depth 3: outer > mid > inner
    _fail("""
def outer():
    def mid():
        def inner():
            return 1
        return inner()
    return mid()
result = outer()
""", 'nesting too deep')


def test_too_many_function_defs_uses_constant():
    parts = ['def f%s():\n    return %s\n' % (i, i) for i in range(v_base.RELAXAICODE_MAX_FUNCTION_DEFS + 1)]
    code = ''.join(parts) + 'result = f0()\n'
    _fail(code, 'Too many function definitions')


def test_def_body_still_blocks_open():
    _fail("""
def bad():
    return open('/etc/passwd').read()
result = bad()
""", "open")


def test_class_still_forbidden():
    _fail("""
class X(object):
    pass
result = {}
""", 'classes')


def test_sorted_with_trim_order_index_lambda_ok():
    _ok("""
TRIM_ORDER = ['T1', 'T2', 'T3', 'T4']
rows = [{'t': 'T2', 'v': 1}, {'t': 'T1', 'v': 2}]
result = {'data': sorted(rows, key=lambda r: TRIM_ORDER.index(r['t']))}
""")


def test_sorted_with_split_in_key_ok():
    _ok("""
rows = [{'t': '2026-T1', 'v': 1}]
result = {'data': sorted(rows, key=lambda r: r['t'].split('-')[1])}
""")


def test_sorted_with_safe_comprehension_in_key_ok():
    _ok("""
rows = [{'tags': ['b', 'a'], 'n': 1}, {'tags': ['c'], 'n': 2}]
result = {
    'data': sorted(
        rows,
        key=lambda r: ''.join(t.lower() for t in (r.get('tags') or [])),
    ),
}
""")


def test_sorted_with_unsafe_call_in_comprehension_still_fails():
    _fail("""
rows = [{'n': 1}]
result = {'data': sorted(rows, key=lambda r: [open('/x') for _ in range(1)])}
""", 'Unsafe lambda')


def test_repair_noop_when_script_def_in_key_already_ok():
    code = """
def band_dist(b):
    return 1
bands = {0: [{'Lat': 1, 'Lon': 2}]}
band_order = sorted(bands.keys(), key=lambda b: band_dist(bands[b]))
result = {'data': band_order}
"""
    repaired, changed = v_sort.repair_unsafe_sort_keys(code)
    assert not changed
    _ok(repaired)


def test_sorted_with_haversine_def_in_key_ok():
    _ok("""
def haversine(a, b):
    return abs(a - b)
rows = [{'Lat': 1.0, 'Lon': 2.0}, {'Lat': 3.0, 'Lon': 4.0}]
rows = sorted(rows, key=lambda r: haversine(r['Lat'], 0.0))
result = {'data': rows}
""")


def test_sorted_get_or_empty_lambda_ok():
    _ok("""
rows = [{'Empleado': 'Ada'}, {'Empleado': None}]
result = {'data': sorted(rows, key=lambda x: x.get('Empleado') or '')}
""")


def test_sorted_with_casefold_and_strptime_lambda_ok():
    _ok("""
rows = [{'name': 'Ada', 'f': '2020-01-02'}]
result = {
    'data': sorted(
        rows,
        key=lambda r: (r['name'].casefold(), datetime.datetime.strptime(r['f'], '%Y-%m-%d')),
    ),
}
""")


def test_sorted_with_isinstance_lambda_ok():
    _ok("""
rows = [{'v': 1}, {'v': 'x'}]
result = sorted(rows, key=lambda r: isinstance(r['v'], (int, float)))
""")


def test_constants_are_named_and_positive():
    assert v_base.RELAXAICODE_MAX_FUNCTION_NESTING_DEPTH >= 1
    assert v_base.RELAXAICODE_MAX_FUNCTION_DEFS >= v_base.RELAXAICODE_MAX_FUNCTION_NESTING_DEPTH
    # Count is a pathological backstop, not a tight skill budget.
    assert v_base.RELAXAICODE_MAX_FUNCTION_DEFS >= 1000
    assert 'casefold' in v_sort._SAFE_LAMBDA_METHODS
    assert 'strptime' in v_sort._SAFE_LAMBDA_METHODS
    assert 'split' in v_sort._SAFE_LAMBDA_METHODS
    assert 'isinstance' in v_sort._SAFE_LAMBDA_CALL_NAMES


def test_env_param_must_receive_name_env():
    _ok("""
def find_contacts(env):
    \"\"\"Find contacts.\"\"\"
    return env['res.partner'].search([])
result = find_contacts(env)
""")
    _ok("""
def find_contacts(env):
    \"\"\"Find contacts.\"\"\"
    return []
result = find_contacts(env=env)
""")
    _fail("""
def find_contacts(env):
    \"\"\"Find contacts.\"\"\"
    return env['res.partner'].search([])
result = find_contacts((previous_result.get('data') if isinstance(previous_result, dict) else None) or raw_data or [])
""", "Parameter 'env'")
    _fail("""
def find_contacts(env):
    \"\"\"Find contacts.\"\"\"
    return []
result = find_contacts(env=raw_data)
""", "Parameter 'env'")
    # Helpers without an env param are untouched.
    _ok("""
def add(a, b):
    return a + b
result = add(1, 2)
""")


def test_search_domain_must_not_be_prior_result():
    _ok("""
result = env['res.partner'].search([('name', 'ilike', 'Ada')])
""")
    _ok("""
result = env['res.partner'].search([])
""")
    _ok("""
rows = (previous_result.get('data') if isinstance(previous_result, dict) else None) or raw_data or []
ids = [r['id'] for r in rows]
result = env['res.partner'].search([('id', 'in', ids)])
""")
    _fail("""
result = env['res.partner'].search(previous_result)
""", 'SEARCH_DOMAIN')
    _fail("""
result = env['res.partner'].search(raw_data)
""", 'SEARCH_DOMAIN')
    _fail("""
domain = (previous_result.get('data') if isinstance(previous_result, dict) else None) or raw_data or []
result = env['calendar.event'].search(domain, order='start')
""", 'SEARCH_DOMAIN')
    _fail("""
result = env['res.partner'].search_count(previous_result)
""", 'SEARCH_DOMAIN')
    _fail("""
result = env['res.partner'].search(domain=raw_data)
""", 'SEARCH_DOMAIN')
