# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""The sandbox does not preload the database name (PNS-36).

No dbname/db_name/database global, the system prompt does not teach it,
and the repair of env.cr.dbname yields an empty string.
"""
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_CTX = (_ROOT / 'common' / 'controllers' / 'context_builder.py').read_text(encoding='utf-8')
_PROMPT = (_ROOT / 'common' / 'ai' / 'contexts' / 'core' / 'system_prompt.xml').read_text(
    encoding='utf-8')
_CHECKS = (_ROOT / 'common' / 'controllers' / 'validators_checks.py').read_text(
    encoding='utf-8')


def test_context_builder_publishes_no_dbname():
    assert "'dbname':" not in _CTX
    assert "'db_name':" not in _CTX
    assert "'database':" not in _CTX
    assert '_dbname' not in _CTX


def test_prompt_does_not_teach_dbname():
    assert 'dbname' not in _PROMPT
    assert 'db_name' not in _PROMPT


def test_hint_says_the_name_is_not_available():
    assert 'The database name is not available in the sandbox.' in _CHECKS
