# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Once a plan ran in the turn, a provider failure does not restart it elsewhere."""
from __future__ import annotations

from _load_addon import engine_source

_SRC = engine_source()


def test_an_executed_plan_marks_the_turn():
    i = _SRC.index("_info.get('success') and _info.get('status') == 'confirmed':")
    assert 'self._turn_effects_done = True' in _SRC[i:i + 200]


def test_the_cascade_resets_the_mark_and_stops_on_it():
    loop = _SRC.index('for idx, current in enumerate(cascade_providers):')
    # Reset before the cascade starts, wherever the surrounding lines move to.
    head = _SRC.index('provider_errors = []')
    assert head < loop
    assert 'self._turn_effects_done = False' in _SRC[head:loop]
    handler = _SRC.index('except ProviderConnectionError as exc:', loop)
    stop = _SRC.index('if self._turn_effects_done:', handler)
    assert stop < _SRC.index("All providers failed for agent", handler)
    assert 'return' in _SRC[stop:stop + 1200]
