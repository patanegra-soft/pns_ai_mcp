# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Customer names the engine must not carry, read from the publish leak lists.

The lists live in the internal git only (``publish.leaks`` of this module and
``utilities/publish/leaks.default`` next to the modules). A published tree has
neither, so these guards find nothing to check there and never spell a name.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

_MODULE = Path(__file__).resolve().parents[1]
_LISTS = (
    _MODULE / 'publish.leaks',
    _MODULE.parents[1] / 'utilities' / 'publish' / 'leaks.default',
)


@lru_cache(maxsize=1)
def tenant_patterns():
    patterns = []
    for path in _LISTS:
        if not path.is_file():
            continue
        for line in path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line and not line.startswith('#'):
                patterns.append(re.compile(line, re.I))
    return tuple(patterns)


def names_tenant(text):
    """First leak pattern found in *text*, or ``''``."""
    for rx in tenant_patterns():
        if rx.search(text or ''):
            return rx.pattern
    return ''
