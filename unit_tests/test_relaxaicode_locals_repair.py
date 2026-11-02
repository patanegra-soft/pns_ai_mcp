# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Repair of dir()/locals() and network import hints."""
from __future__ import annotations

from _load_addon import load_module

v = load_module('validators', 'controllers', 'validators.py')
v_base = load_module('validators_base', 'controllers', 'validators_base.py')
v_repair = load_module('validators_repair', 'controllers', 'validators_repair.py')


def test_repair_dir_model_to_fields():
    src = (
        "Model = env['res.partner']\n"
        "result = dir(Model)\n"
    )
    out, changed = v_repair.repair_locals_dir_checks(src)
    assert changed
    assert 'dir(' not in out
    assert '._fields' in out
    assert 'sorted(' in out
    ok, err, _w = v.validate_relaxaicode_source_ast(out)
    assert ok, err


def test_repair_dir_env_index_comprehension():
    src = (
        "result = [k for k in dir(env['res.partner']) if 'name' in k]\n"
    )
    out, changed = v_repair.repair_locals_dir_checks(src)
    assert changed
    assert 'dir(' not in out
    assert "env['res.partner']._fields" in out or '._fields' in out
    ok, err, _w = v.validate_relaxaicode_source_ast(out)
    assert ok, err


def test_repair_dir_already_fields():
    src = "result = dir(env['res.partner']._fields)\n"
    out, changed = v_repair.repair_locals_dir_checks(src)
    assert changed
    assert 'dir(' not in out
    assert '._fields._fields' not in out
    ok, err, _w = v.validate_relaxaicode_source_ast(out)
    assert ok, err


def test_bare_dir_still_banned():
    src = "result = dir()\n"
    out, _changed = v_repair.repair_locals_dir_checks(src)
    ok, err, _w = v.validate_relaxaicode_source_ast(out)
    assert not ok
    assert v_base.ast_error_code(err) == 'DIR'
    assert err.startswith('[PROHIBITED:DIR]')


def test_ast_error_code_is_locale_blind():
    assert v_base.ast_error_code('[PROHIBITED:DIR] cualquier prosa') == 'DIR'
    assert v_base.ast_error_code('[MANDATORY:RESULT] definir la variable') == 'RESULT'
    assert v_base.ast_error_code('[SYNTAX] Error de sintaxis') == 'SYNTAX'
    assert v_base.ast_error_code('[PROHIBITED:SORT_KEY] Unsafe lambda') == 'SORT_KEY'
    assert v_base.ast_error_code('NO puede usar dir') is None
    assert v_base.ast_error_code("Cannot use 'dir'") is None


def test_missing_result_has_stable_code():
    ok, err, _w = v.validate_relaxaicode_source_ast('x = 1\n')
    assert not ok
    assert v_base.ast_error_code(err) == 'RESULT'


def test_syntax_error_has_stable_code():
    ok, err, _w = v.validate_relaxaicode_source_ast('def (\n')
    assert not ok
    assert v_base.ast_error_code(err) == 'SYNTAX'


def test_repair_controller_does_not_match_locale_phrases():
    from _load_addon import relaxaicode_source
    src = relaxaicode_source()
    for banned in (
        "NO puede usar 'dir'",
        "NO puede usar 'locals'",
        "definir la variable",
        "Cannot use 'dir'",
        "Cannot use 'locals'",
    ):
        assert banned not in src, banned


def test_repair_lugar_in_dir_pattern():
    src = "_lugar_param = lugar if 'lugar' in dir() and lugar else None\nresult = {}\n"
    out, changed = v_repair.repair_locals_dir_checks(src)
    assert changed
    assert 'dir()' not in out
    assert '_lugar_param = lugar if lugar else None' in out
    ok, err, _w = v.validate_relaxaicode_source_ast(out)
    assert ok, err


def test_repair_previous_result_in_locals():
    src = "data = previous_result if 'previous_result' in locals() else None\nresult = data\n"
    out, changed = v_repair.repair_locals_dir_checks(src)
    assert changed
    assert 'locals()' not in out
    ok, err, _w = v.validate_relaxaicode_source_ast(out)
    assert ok, err


def test_network_import_requests_mentions_fetch_url():
    ok, err, _w = v.validate_relaxaicode_source_ast(
        "import requests\nresult = {}\n"
    )
    assert not ok
    assert 'fetch_url' in err
    assert 'requests' in err


def test_network_import_urllib_mentions_fetch_url():
    ok, err, _w = v.validate_relaxaicode_source_ast(
        "import urllib.request\nresult = {}\n"
    )
    assert not ok
    assert 'fetch_url' in err


def test_repair_cr_dbname_hasattr_ternary():
    src = (
        "def sys_info_snapshot():\n"
        "    \"\"\"Información del sistema.\"\"\"\n"
        "    result = [\n"
        "        {'Propiedad': 'Base de datos',\n"
        "         'Valor': env.cr.dbname if hasattr(env, 'cr') else ''},\n"
        "    ]\n"
        "    return result\n"
        "result = sys_info_snapshot()\n"
    )
    out, changed = v_repair.repair_cr_dbname(src)
    assert changed
    assert 'env.cr' not in out
    assert "'Valor': ''" in out
    ok, err, _w = v.validate_relaxaicode_source_ast(out)
    assert ok, err


def test_repair_cr_dbname_plain_and_getattr():
    src = (
        "db = env.cr.dbname\n"
        "other = getattr(env._cr, 'dbname', '')\n"
        "result = db or other\n"
    )
    out, changed = v_repair.repair_cr_dbname(src)
    assert changed
    assert 'env.cr' not in out
    assert 'env._cr' not in out
    assert 'dbname' not in out
    ok, err, _w = v.validate_relaxaicode_source_ast(out)
    assert ok, err


def test_cr_hint_mentions_dbname():
    ok, err, _w = v.validate_relaxaicode_source_ast(
        "result = env.cr\n"
    )
    assert not ok
    assert v_base.ast_error_code(err) == 'CR'
    assert 'dbname' in err
    assert "env.cr.dbname" in err


def test_repair_registry_models_ubws_comprehension():
    src = (
        "def tipo_iva_precise():\n"
        "    \"\"\"Campos/vistas de tipo de IVA.\"\"\"\n"
        "    tax_models = [m for m in env.registry.models if 'tax' in m and 'account' in m]\n"
        "    return tax_models[:40]\n"
        "result = tipo_iva_precise()\n"
    )
    out, changed = v_repair.repair_registry_models(src)
    assert changed
    assert 'registry' not in out
    assert "env['ir.model']" in out
    assert ".mapped('model')" in out
    ok, err, _w = v.validate_relaxaicode_source_ast(out)
    assert ok, err


def test_repair_registry_models_pr1y_for_in():
    src = (
        "def find_recipe_model():\n"
        "    \"\"\"Find recipe models.\"\"\"\n"
        "    names = [m for m in env.registry if 'recipe' in m or 'relaxai' in m]\n"
        "    return names[:40]\n"
        "result = find_recipe_model()\n"
    )
    out, changed = v_repair.repair_registry_models(src)
    assert changed
    assert 'registry' not in out
    assert "env['ir.model']" in out
    ok, err, _w = v.validate_relaxaicode_source_ast(out)
    assert ok, err


def test_repair_registry_membership_and_subscript():
    src = (
        "name = 'res.partner'\n"
        "ok = name in env.registry\n"
        "Model = env.registry[name]\n"
        "result = {'ok': ok, 'model': Model._name}\n"
    )
    out, changed = v_repair.repair_registry_models(src)
    assert changed
    assert 'registry' not in out
    assert 'name in env' in out
    assert "env[name]" in out
    ok, err, _w = v.validate_relaxaicode_source_ast(out)
    assert ok, err


def test_repair_registry_keys_and_sorted():
    src = (
        "names = sorted(env.registry.models.keys())\n"
        "also = list(env.registry)\n"
        "result = names + also\n"
    )
    out, changed = v_repair.repair_registry_models(src)
    assert changed
    assert 'registry' not in out
    assert "env['ir.model']" in out
    ok, err, _w = v.validate_relaxaicode_source_ast(out)
    assert ok, err


def test_repair_registry_leaves_cursor_banned():
    src = "result = env.registry.cursor()\n"
    out, changed = v_repair.repair_registry_models(src)
    assert not changed
    ok, err, _w = v.validate_relaxaicode_source_ast(out)
    assert not ok
    assert v_base.ast_error_code(err) == 'REGISTRY'
    assert 'ir.model' in err


def test_unrepaired_registry_has_stable_code():
    ok, err, _w = v.validate_relaxaicode_source_ast(
        "result = sorted(env.registry.models.keys())\n"
    )
    assert not ok
    assert v_base.ast_error_code(err) == 'REGISTRY'
    assert err.startswith('[PROHIBITED:REGISTRY]')
