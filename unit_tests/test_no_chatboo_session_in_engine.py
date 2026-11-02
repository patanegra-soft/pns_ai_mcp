# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""The engine must not name Chatboo's chat table."""
from __future__ import annotations

from pathlib import Path

_COMMON = Path(__file__).resolve().parents[1] / 'common'
_NEEDLE = 'chatboo.session'


def test_engine_common_does_not_name_chatboo_session():
    hits = []
    for path in _COMMON.rglob('*'):
        if not path.is_file() or path.suffix.lower() != '.py':
            continue
        text = path.read_text(encoding='utf-8')
        if _NEEDLE in text:
            hits.append(str(path.relative_to(_COMMON)).replace('\\', '/'))
    assert hits == [], (
        'Engine still names Chatboo\'s table in: %s' % ', '.join(hits)
    )
