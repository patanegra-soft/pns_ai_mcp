# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Factory discovery files are neutral or es_ES. No leftover unlink in the engine."""
import re
from pathlib import Path

from _load_addon import context_source

_KEEP = frozenset({'es', 'es_ES'})
_RE = re.compile(r'_([a-z]{2}(?:_[A-Z]{2})?)$')
_DISC = (
    Path(__file__).resolve().parents[1] / 'common' / 'ai' / 'contexts' / 'discovery'
)

def test_factory_discovery_files_are_neutral_or_es_es():
    assert _DISC.is_dir()
    for path in sorted(_DISC.glob('*.json')):
        match = _RE.search(path.stem)
        if match:
            assert match.group(1) in _KEEP, path.name


def test_engine_has_no_leftover_discovery_unlink():
    src = context_source()
    assert '_unlink_non_es_locale_discovery' not in src
    assert '_unlink_retired_factory_discovery' not in src
    assert '_purge_legacy_disc_leftovers' not in src
