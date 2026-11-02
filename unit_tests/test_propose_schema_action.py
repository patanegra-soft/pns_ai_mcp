# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""op=action must sit on the propose tool card next to create/write (no Odoo)."""
from __future__ import annotations

from _load_addon import safe_plan_source


def test_propose_schema_lists_action_like_crud():
    src = safe_plan_source()
    start = src.index('_PROPOSE_SCHEMA')
    chunk = src[start:start + 2500]
    assert "op='create'" in chunk
    assert "op='write'" in chunk
    assert "op='action'" in chunk
    assert "op='field_required'" in chunk
    assert 'action_code' in chunk
    assert 'module.update' in chunk


def test_propose_description_does_not_train_prose_confirm():
    """PAAP I4: The model is told the human confirms in Odoo, never through the chat."""
    src = safe_plan_source()
    assert 'informa al usuario' not in src
    assert 'Calling this tool IS the proposal' in src
    # Tool card (decorator), not the helper docstring.
    deco = "or op=action (closed action_code"
    assert deco in src
