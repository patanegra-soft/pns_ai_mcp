# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Unit tests for the published skill↔engine contract."""
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from common.utils.skill_engine_contract import (
    SKILL_ENGINE_CAPABILITIES,
    published_front_matter_keys,
    published_result_dunders,
    skill_contract_violations,
)
from _load_addon import export_source, render_source


def test_published_requires_are_clean():
    assert 'compose-model' in SKILL_ENGINE_CAPABILITIES
    assert 'report_outline' in SKILL_ENGINE_CAPABILITIES
    assert not skill_contract_violations(
        meta={'skill': 'demo', 'requires': 'compose-model, report_outline'},
        code_body="result = {'data': [], '__return_direct__': True}",
    )
    bad_old = skill_contract_violations(
        meta={'requires': 'painter-free, report_outline'},
    )
    assert 'painter-free' in bad_old
    assert 'report_outline' not in bad_old
    assert skill_contract_violations(meta={'formatting_mode': 'compose-model'})


def test_unknown_requires_is_a_violation():
    bad = skill_contract_violations(
        meta={'requires': 'after_llm, compose-model'},
    )
    assert 'after_llm' in bad
    assert 'compose-model' not in bad


def test_unknown_front_matter_is_a_violation():
    bad = skill_contract_violations(
        meta={'engine_patch': 'yes', 'name': 'Demo'},
    )
    assert 'engine_patch' in bad
    assert 'name' not in bad


def test_unpublished_dunder_in_source_is_a_violation():
    bad = skill_contract_violations(
        code_body="result['__after_llm__'] = True",
    )
    assert '__after_llm__' in bad


def test_unpublished_dunder_in_result_is_a_violation():
    bad = skill_contract_violations(
        result={'__after_llm__': True, '__return_direct__': True},
    )
    assert '__after_llm__' in bad
    assert '__return_direct__' not in bad


def test_result_dunders_come_from_engine_source():
    """No handwritten allowlist: a reader in the engine publishes the key."""
    published = published_result_dunders()
    render = render_source()
    assert "'__hide_columns__'" in render or '"__hide_columns__"' in render
    assert '__hide_columns__' in published
    export = export_source()
    assert "'__excel_formulas__'" in export
    assert '__excel_formulas__' in published
    assert '__after_llm__' not in published
    contract = (
        _ROOT / 'common' / 'utils' / 'skill_engine_contract.py'
    ).read_text(encoding='utf-8')
    assert "'__hide_columns__'" not in contract
    assert not skill_contract_violations(
        code_body="result = {'__hide_columns__': ['id'], '__return_direct__': True}",
    )


def test_front_matter_keys_come_from_the_readers():
    """The importer reads required_groups; the contract lets it through."""
    keys = published_front_matter_keys()
    assert 'required_groups' in keys
    assert 'agent_codes' in keys
    assert 'requires' in keys
    assert not skill_contract_violations(
        meta={'skill': 'users-all', 'required_groups': 'pns_ai_mcp.group_ai_admin'},
    )
    contract = (
        _ROOT / 'common' / 'utils' / 'skill_engine_contract.py'
    ).read_text(encoding='utf-8')
    assert 'SKILL_FRONT_MATTER_KEYS = frozenset((' not in contract


def _front_matter(path):
    lines = path.read_text(encoding='utf-8').split('\n')
    meta = {}
    if lines and lines[0].strip() == '---':
        for line in lines[1:]:
            if line.strip() == '---':
                break
            if ':' in line:
                meta[line.split(':', 1)[0].strip()] = line.split(':', 1)[1].strip()
    return meta


def test_every_skill_on_disk_passes_the_front_matter_contract():
    """A shipped skill with a key the readers do not cite never imports."""
    keys = published_front_matter_keys()
    roots = [_ROOT] + sorted(p for p in _ROOT.parent.iterdir() if p.is_dir())
    seen = 0
    for root in roots:
        skills = root / 'common' / 'ai' / 'skills'
        if not skills.is_dir():
            continue
        for path in skills.rglob('*.md'):
            unknown = sorted(set(_front_matter(path)) - keys)
            assert not unknown, (path, unknown)
            seen += 1
    if not seen:
        pytest.skip('no skill on disk: the engine ships none and no neighbour module is here')
