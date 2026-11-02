# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Unit tests for next_copy_code suffixes."""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from common.utils.copy_code import next_copy_code


def test_next_copy_code_first_suffix():
    assert next_copy_code('alpha', ['alpha']) == 'alpha_copy'


def test_next_copy_code_skips_taken():
    assert next_copy_code('alpha', ['alpha', 'alpha_copy']) == 'alpha_copy2'


def test_next_copy_code_empty_base():
    assert next_copy_code('', []) == 'server_copy'
