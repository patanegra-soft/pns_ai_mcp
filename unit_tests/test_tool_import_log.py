# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""A tool module that fails to import is logged, and does not hide the others."""
from pathlib import Path

_INIT = (
    Path(__file__).resolve().parents[1] / 'common' / 'controllers' / '__init__.py'
).read_text(encoding='utf-8')


def test_each_tool_module_loads_on_its_own():
    assert 'except ImportError:\n    pass' not in _INIT
    assert 'except ImportError:' in _INIT
    assert "_logger.exception('MCP tools: %s did not load', name)" in _INIT
    body = _INIT.split('def _load_tool')[1]
    for name in ('tools_relaxaicode', 'safe_plan', 'tools_context'):
        assert "_load_tool('%s')" % name in body
