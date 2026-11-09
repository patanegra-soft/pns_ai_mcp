# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Sandbox helpers: literals, result call, self-recursive shadow, pins."""
from __future__ import annotations

from _load_addon import load_module

r = load_module('relaxaicode_recipe', 'utils', 'relaxaicode_recipe.py')


def test_module_level_data_literal_error():
    code = 'rows = ' + repr([{'a': i} for i in range(20)]) + '\nresult = rows\n'
    err = r.module_level_data_literal_error(code)
    assert err
    assert 'dataset' in err.lower() or 'literal' in err.lower()
    assert r.module_level_data_literal_error('result = 1\n') is None


def test_computed_literal_is_not_a_pasted_dataset():
    code = (
        'pairs = [\n'
        + ''.join(
            "    ('Fact %d', env['res.partner'].search_count([])),\n" % i
            for i in range(11)
        )
        + "    ('Version', odoo_version),\n"
        + "    ('Now', now.strftime('%Y')),\n"
        + ']\nresult = pairs\n'
    )
    assert r.module_level_data_literal_error(code) is None
    cleaned, names, _extracted = r.strip_module_level_data_literals(code)
    assert names == []
    assert cleaned == code


def test_strip_module_level_data_literals_rebinds():
    code = (
        'rows = ' + repr([{'a': i} for i in range(20)]) + '\n'
        'result = hours_table("2026-08-06", rows)\n'
    )
    cleaned, names, extracted = r.strip_module_level_data_literals(code)
    assert names == ['rows']
    assert 'rows' in extracted
    assert len(extracted['rows']) == 20
    assert 'rows = [' not in cleaned
    assert 'hours_table' in cleaned
    assert r.module_level_data_literal_error(cleaned) is None
    preamble = r.bind_stripped_names_from_prior(names, extracted)
    assert 'json.loads' in preamble
    assert 'rows =' in preamble


def test_strip_recovers_round_fold():
    code = (
        'rows = [\n'
        + ',\n'.join(
            "{'Empleado': 'A', 'Horas': round(30396/3600, 2), "
            "'Teóricas': round(28800/3600, 2)}"
            for _ in range(10)
        )
        + '\n]\nresult = f(rows)\n'
    )
    cleaned, names, extracted = r.strip_module_level_data_literals(code)
    assert names == ['rows']
    assert len(extracted.get('rows') or []) == 10
    assert extracted['rows'][0]['Horas'] == round(30396 / 3600, 2)
    preamble = r.bind_stripped_names_from_prior(names, extracted)
    assert 'json.loads' in preamble


def test_ensure_module_result_call_appends_invocation():
    code = (
        'def hours_report(fecha, rows_src):\n'
        '    """Personal hours table."""\n'
        '    return {"data": rows_src, "summary": fecha}\n'
    )
    out, changed = r.ensure_module_result_call(code)
    assert changed
    assert 'result = hours_report(str(today)' in out
    assert 'previous_result' in out
    out2, changed2 = r.ensure_module_result_call(out)
    assert not changed2


def test_ensure_module_result_call_uses_module_binders():
    code = (
        'hours = [{"a": 1}]\n'
        'def report(fecha, rows_src):\n'
        '    """Build table."""\n'
        '    return {"data": rows_src}\n'
    )
    out, changed = r.ensure_module_result_call(code)
    assert changed
    assert 'result = report(str(today), hours)' in out


def test_strip_self_recursive_shadow_keeps_real_body():
    """T8TP / S13X pattern: real def then ``def f(): return f()`` shadow."""
    code = (
        'def ruta(min_amount=10000.0):\n'
        '    """Tour clients by corridors."""\n'
        '    return {"data": [{"amt": min_amount}]}\n'
        '\n'
        'def ruta(min_amount=15000.0):\n'
        '    """Tour clients by corridors."""\n'
        '    return ruta(min_amount=min_amount)\n'
        '\n'
        'result = ruta(min_amount=15000.0)\n'
    )
    cleaned, stripped = r.strip_self_recursive_shadow_defs(code)
    assert stripped == ['ruta']
    assert 'return ruta(min_amount=min_amount)' not in cleaned
    assert 'result = ruta(min_amount=15000.0)' in cleaned
    assert r.self_recursive_def_error(cleaned) is None
    ns = {}
    exec(cleaned, ns, ns)
    assert ns['result']['data'][0]['amt'] == 15000.0


def test_strip_self_recursive_shadow_assign_return_pattern():
    code = (
        'def pick(batch_size=20):\n'
        '    """Pick partners."""\n'
        '    return {"n": batch_size}\n'
        '\n'
        'def pick(batch_size=25):\n'
        '    """Pick partners."""\n'
        '    result = pick(batch_size=batch_size)\n'
        '    return result\n'
        '\n'
        'result = pick(batch_size=25)\n'
    )
    cleaned, stripped = r.strip_self_recursive_shadow_defs(code)
    assert stripped == ['pick']
    ns = {}
    exec(cleaned, ns, ns)
    assert ns['result']['n'] == 25


def test_sole_self_recursive_def_rejected():
    code = (
        'def broken(x=1):\n'
        '    """Oops."""\n'
        '    return broken(x=x)\n'
        '\n'
        'result = broken(x=2)\n'
    )
    cleaned, stripped = r.strip_self_recursive_shadow_defs(code)
    assert stripped == []
    assert cleaned == code
    err = r.self_recursive_def_error(code)
    assert err and 'broken' in err and 'infinite recursion' in err


def test_inject_map_pins_origin_from_distance():
    """distance() must not paint roads on a pins-only map_pins_* call."""
    code = (
        'origin = company\n'
        'for row in rows:\n'
        '    d = distance(origin, row["Dirección"], mode="driving")\n'
        'result = {\n'
        '    "map_url": map_pins_url(rows, lat="Lat", lon="Lon", name="Cliente"),\n'
        '    "map_pins": map_pins_cell(rows, lat="Lat", lon="Lon"),\n'
        '}\n'
    )
    out, changed = r.inject_map_pins_origin_from_distance(code)
    assert not changed
    assert out == code
    assert 'origin=origin' not in out.replace(' ', '')


def test_inject_map_pins_origin_skips_when_origin_present():
    code = (
        'd = distance(hq, dest)\n'
        'map_pins_url(rows, origin=hq, title="Ruta")\n'
    )
    out, changed = r.inject_map_pins_origin_from_distance(code)
    assert not changed
    assert out == code


def test_inject_map_pins_origin_noop_without_distance():
    code = 'map_pins_url(rows, lat="Lat", lon="Lon")\n'
    out, changed = r.inject_map_pins_origin_from_distance(code)
    assert not changed
    assert out == code


def test_ensure_module_result_call_omits_optional_date_range():
    code = (
        'def mapa(date_from=None, date_to=None):\n'
        '    """Mapa de rango."""\n'
        '    return {"ok": True}\n'
    )
    out, changed = r.ensure_module_result_call(code)
    assert changed
    assert 'result = mapa()' in out
    assert 'str(today)' not in out


def test_ensure_module_result_call_required_range_does_not_invent_period():
    code = (
        'def mapa(date_from, date_to):\n'
        '    """Mapa de rango."""\n'
        '    return {"ok": True}\n'
    )
    out, changed = r.ensure_module_result_call(code)
    assert not changed
    assert out == code
    assert 'timedelta' not in out
    assert 'str(today)' not in out
    assert 'result = mapa' not in out


def test_ensure_date_param_coercion_makes_isoformat_safe():
    code = (
        'def mapa(date_from=None, date_to=None):\n'
        '    """Rango."""\n'
        '    return date_from.isoformat() + "|" + date_to.isoformat()\n'
        "result = mapa('2026-08-01', '2026-08-14')\n"
    )
    out, changed = r.ensure_date_param_coercion(code)
    assert changed
    assert 'fromisoformat(date_from[:10])' in out
    ns = {'date': __import__('datetime').date}
    exec(out, ns, ns)
    assert ns['result'] == '2026-08-01|2026-08-14'
    out2, changed2 = r.ensure_date_param_coercion(out)
    assert not changed2
