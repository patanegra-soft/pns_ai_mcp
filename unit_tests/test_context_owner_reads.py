# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""The engine reads contexts in sudo, but a private one stays its owner's."""
from __future__ import annotations

from pathlib import Path

import pytest
from _load_addon import context_source, engine_source

_COMMON = Path(__file__).resolve().parents[1] / 'common'
_CTX = context_source()
_ENGINE = engine_source()
_MAIN = (_COMMON / 'controllers' / 'main.py').read_text(encoding='utf-8')


def _method(src, name):
    start = src.index('def %s(' % name)
    return src[start:src.index('\n    def ', start + 10)]


@pytest.mark.parametrize('name', [
    'get_context_for_country',
    'get_listable_for_mcp',
    'get_discovery_entries',
    'get_canonical_contexts_for_agent',
    '_injectable_active_contexts',
])
def test_each_reader_keeps_the_owner_rule(name):
    body = _method(_CTX, name)
    assert 'ownership_read_domain()' in body or 'filter_visible_for_user(' in body


def test_every_search_in_get_context_for_country_is_filtered():
    body = _method(_CTX, 'get_context_for_country')
    assert body.count('self.search(') == body.count('self.search(self.ownership_read_domain()')


def test_the_engine_fallback_is_filtered():
    body = _method(_ENGINE, '_domain_index_inject_bodies')
    assert 'Context.search(Context.ownership_read_domain()' in body


def test_mcp_prompts_read_as_the_caller():
    for anchor in ("get_listable_for_mcp()", "refuse_foreign_identity_pack(self, env, prompt_name)"):
        i = _MAIN.index(anchor)
        window = _MAIN[i - 400:i]
        assert 'env = self._get_mcp_env()(su=True)' in window
        assert '_get_mcp_env().sudo()' not in window
        assert 'env = request.env(user=SUPERUSER_ID)' not in window
