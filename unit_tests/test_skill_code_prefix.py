# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Literal skill catalog + slash prefixes — no {company}/{user} interpolation."""
from __future__ import annotations

from _load_addon import load_module

p = load_module('skill_code_prefix', 'utils', 'skill_code_prefix.py')


def test_factory_defaults_are_custom_code_and_empty_slash():
    assert p.DEFAULT_SKILL_CODE_PREFIX == 'custom_'
    assert p.DEFAULT_SKILL_COMMAND_PREFIX == ''


def test_normalize_empty_is_blank():
    assert p.normalize_skill_code_prefix('') == ''
    assert p.normalize_skill_code_prefix(None) == ''
    assert p.normalize_skill_command_prefix('') == ''
    assert p.normalize_skill_command_prefix(None) == ''


def test_normalize_code_snake_and_command_kebab():
    assert p.normalize_skill_code_prefix('custom') == 'custom_'
    assert p.normalize_skill_code_prefix('acme-custom-') == 'acme_custom_'
    assert p.normalize_skill_command_prefix('acme') == 'acme-'
    assert p.normalize_skill_command_prefix('acme-') == 'acme-'


def test_instance_identity_no_prefix():
    code, command = p.instance_identity('facturacion', '', '')
    assert code == 'facturacion'
    assert command == 'facturacion'


def test_instance_identity_both_prefixes():
    code, command = p.instance_identity(
        'facturacion', 'acme_custom_', 'acme-',
    )
    assert code == 'acme_custom_facturacion'
    assert command == 'acme-facturacion'


def test_invoke_lookup_tokens_includes_stem_and_prefixed():
    tokens = p.invoke_lookup_tokens('facturacion', 'acme_custom_', 'acme-')
    assert 'facturacion' in tokens
    assert 'acme-facturacion' in tokens
    assert 'acme_custom_facturacion' in tokens
    already = p.invoke_lookup_tokens('acme-nominas', 'acme_custom_', 'acme-')
    assert 'acme-nominas' in already
    assert 'acme_custom_nominas' in already
    assert p.invoke_lookup_tokens('', 'acme_custom_', 'acme-') == ()


def test_instance_identity_does_not_double_prefixes():
    code, command = p.instance_identity(
        'acme-nominas', 'acme_custom_', 'acme-',
    )
    assert code == 'acme_custom_nominas'
    assert command == 'acme-nominas'


def test_instance_identity_legacy_code_prefix_only():
    code, command = p.instance_identity('facturacion', 'custom_', '')
    assert code == 'custom_facturacion'
    assert command == 'facturacion'
    code, command = p.instance_identity('custom-facturacion', 'custom_', '')
    assert code == 'custom_facturacion'
    assert command == 'facturacion'


def test_auto_prefix_detects_only_exact_match():
    assert p.is_auto_prefixed_code(
        'acme_custom_facturacion', 'facturacion', 'acme_custom_', 'acme-',
    )
    assert not p.is_auto_prefixed_code(
        'custom_acme_facturacion', 'facturacion', 'acme_custom_', 'acme-',
    )


def test_strip_and_stem_for_reapply():
    assert p.strip_prefix_stem('acme-nominas', ('acme-', 'custom_acme_')) == 'nominas'
    assert p.strip_prefix_stem(
        'custom_acme_nominas', ('acme-', 'custom_acme_'),
    ) == 'nominas'
    stem = p.stem_for_reapply(
        'custom_acme_nominas', 'acme-nominas',
        ('custom_acme_', 'acme_custom_'), ('acme-',),
    )
    assert stem == 'nominas'
    code, command = p.instance_identity(stem, 'acme_custom_', 'acme-')
    assert code == 'acme_custom_nominas'
    assert command == 'acme-nominas'


def test_strip_longest_prefix_wins_over_legacy_custom():
    assert p.strip_prefix_stem(
        'custom_acme_facturacion', ('custom_', 'custom_acme_', 'acme_custom_'),
    ) == 'facturacion'
    assert p.strip_prefix_stem(
        'custom_nominas', ('custom_acme_', 'acme_custom_', 'custom_'),
    ) == 'nominas'


def test_reapply_repairs_crossed_disk_and_legacy_rows():
    old_codes = ('custom_acme_', 'acme_custom_', 'custom_')
    old_cmds = ('acme-',)
    cases = (
        ('custom_nominas', 'acme-nominas', 'acme_custom_nominas', 'acme-nominas'),
        (
            'custom_acme_cuadro_mando', 'cuadro-mando',
            'acme_custom_cuadro_mando', 'acme-cuadro-mando',
        ),
        (
            'custom_acme_staffhr_geo', 'staff-geo',
            'acme_custom_staff_geo', 'acme-staff-geo',
        ),
    )
    for live_code, live_cmd, want_code, want_cmd in cases:
        stem = p.stem_for_reapply(live_code, live_cmd, old_codes, old_cmds)
        code, command = p.instance_identity(stem, 'acme_custom_', 'acme-')
        assert (code, command) == (want_code, want_cmd), (live_code, live_cmd)


def test_prefix_stomps_reserved_slash():
    assert p.prefix_stomps_slash('', 'skills')
    assert p.prefix_stomps_slash('', 'create-skill')
    assert p.prefix_stomps_slash('', 'set-skill-parameters')
    assert p.prefix_stomps_slash('', 'edit-skill')
    assert p.prefix_stomps_slash('', 'reload-skills')
    assert not p.prefix_stomps_slash('acme_custom_', 'acme-')
    assert p.prefix_stomps_slash('', 'payroll', taken_commands=('payroll',))


def test_uniquify_catalog_code():
    assert p.uniquify_catalog_code('custom_foo', set()) == 'custom_foo'
    assert p.uniquify_catalog_code('custom_foo', {'custom_foo'}) == 'custom_foo_2'
    assert p.uniquify_catalog_code(
        'custom_foo', {'custom_foo', 'custom_foo_2'},
    ) == 'custom_foo_3'


def test_unprefixed_twin_stems_strips_instance_prefix_only():
    stems = p.unprefixed_twin_stems(
        ('acme-polizas', 'acme-nominas', 'payroll', 'sys-info'),
        'acme-',
    )
    assert stems == frozenset({'polizas', 'nominas'})
    assert p.unprefixed_twin_stems(('acme-polizas',), '') == frozenset()
    assert p.unprefixed_twin_stems(('payroll',), 'acme-') == frozenset()


def test_leftover_twin_action_unlinks_unused_twins():
    factory = ('acme-nominas', 'acme-polizas', 'acme-flota')
    on_disk = {
        'skills/custom/custom_acme_nominas.md',
        'skills/system/flota.md',
        'skills/system/payroll.md',
    }
    assert p.leftover_twin_action(
        'nominas', factory, 'acme-',
        'skills/system/nominas.md', on_disk, True,
    ) == 'unlink'
    assert p.leftover_twin_action(
        'flota', factory, 'acme-',
        'skills/system/flota.md', on_disk, True,
    ) == 'unlink'
    assert p.leftover_twin_action(
        'polizas', factory, 'acme-',
        '', on_disk, False,
    ) == 'unlink'
    assert p.leftover_twin_action(
        'acme-nominas', factory, 'acme-',
        'skills/custom/custom_acme_nominas.md', on_disk, True,
    ) == ''
    assert p.leftover_twin_action(
        'payroll', factory, 'acme-',
        'skills/system/payroll.md', on_disk, True,
    ) == ''
