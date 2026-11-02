# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Load addon modules as t.sh/i.sh merge does: common base + stack on top."""
from __future__ import annotations

import functools
import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType

_REPO_ROOT = Path(__file__).resolve().parents[1]
_STACK = os.environ.get('PNS_TEST_STACK', 'owl2')
_MODULE = 'pns_ai_mcp'


def addon_file(*parts: str) -> Path:
    """Effective path of an addon file (stack override if there is one)."""
    rel = Path(*parts)
    stack_path = _REPO_ROOT / 'stacks' / _STACK / _MODULE / rel
    if stack_path.is_file():
        return stack_path
    common_path = _REPO_ROOT / 'common' / rel
    if common_path.is_file():
        return common_path
    raise FileNotFoundError(
        'No está en common/ ni en stacks/%s/%s/: %s' % (_STACK, _MODULE, rel.as_posix())
    )


@functools.lru_cache(maxsize=None)
def engine_source() -> str:
    """Text of ``AgentEngine``: ``agent_engine.py`` plus each ``engine_*.py``.

    Source tests read the engine through here, so a method that moves to
    another engine file is still found.
    """
    main = addon_file('utils', 'agent_engine.py')
    parts = [main] + sorted(main.parent.glob('engine_*.py'))
    return '\n'.join(p.read_text(encoding='utf-8') for p in parts)


def context_source() -> str:
    """Text of the ``ai.context`` model: ``ai_context.py`` plus each ``ai_context_*.py``."""
    main = addon_file('models', 'ai_context.py')
    parts = [main] + sorted(main.parent.glob('ai_context_*.py'))
    return '\n'.join(p.read_text(encoding='utf-8') for p in parts)


def relaxaicode_source() -> str:
    """Text of the relaxaicode tool: ``tools_relaxaicode.py`` plus each ``relaxaicode_*.py``."""
    main = addon_file('controllers', 'tools_relaxaicode.py')
    parts = [main] + sorted(main.parent.glob('relaxaicode_*.py'))
    return '\n'.join(p.read_text(encoding='utf-8') for p in parts)


def validators_source() -> str:
    """Text of the relaxaicode AST check: ``validators.py`` plus each ``validators_*.py``."""
    main = addon_file('controllers', 'validators.py')
    parts = [main] + sorted(main.parent.glob('validators_*.py'))
    return '\n'.join(p.read_text(encoding='utf-8') for p in parts)


def skill_source() -> str:
    """Text of the ``ai.skill`` model: ``ai_skill.py`` plus each file that inherits it."""
    main = addon_file('models', 'ai_skill.py')
    parts = [main] + [
        p for p in sorted(main.parent.glob('ai_skill_*.py'))
        if "_inherit = 'ai.skill'" in p.read_text(encoding='utf-8')
    ]
    return '\n'.join(p.read_text(encoding='utf-8') for p in parts)


def safe_plan_source() -> str:
    """Text of Safe Plan: ``safe_plan.py`` plus each ``safe_plan_*.py``."""
    main = addon_file('controllers', 'safe_plan.py')
    parts = [main] + sorted(main.parent.glob('safe_plan_*.py'))
    return '\n'.join(p.read_text(encoding='utf-8') for p in parts)


def runtime_source() -> str:
    """Text of the skill runtime: ``skill_runtime.py`` plus each ``skill_runtime_*.py``."""
    main = addon_file('utils', 'skill_runtime.py')
    parts = [main] + sorted(main.parent.glob('skill_runtime_*.py'))
    return '\n'.join(p.read_text(encoding='utf-8') for p in parts)


def export_source() -> str:
    """Text of file export: ``artifact_export.py`` plus each ``artifact_export_*.py``."""
    main = addon_file('utils', 'artifact_export.py')
    parts = [main] + sorted(main.parent.glob('artifact_export_*.py'))
    return '\n'.join(p.read_text(encoding='utf-8') for p in parts)


def render_source() -> str:
    """Text of the result renderer: ``relaxaicode_render.py`` plus each ``relaxaicode_render_*.py``."""
    main = addon_file('utils', 'relaxaicode_render.py')
    parts = [main] + sorted(main.parent.glob('relaxaicode_render_*.py'))
    return '\n'.join(p.read_text(encoding='utf-8') for p in parts)


def load_module(mod_name: str, *parts: str) -> ModuleType:
    """importlib of an addon .py (no Odoo runtime).

    Loaded inside a synthetic package with the file's folder, so that a
    ``from .neighbour import …`` resolves the same as in Odoo. The neighbour
    comes from that folder: a sibling's stack override is not seen here.
    """
    path = addon_file(*parts)
    pkg_name = '_pns_addon_%s' % path.parent.name
    if pkg_name not in sys.modules:
        pkg = ModuleType(pkg_name)
        pkg.__path__ = [str(path.parent)]
        sys.modules[pkg_name] = pkg
    full_name = '%s.%s' % (pkg_name, mod_name)
    spec = importlib.util.spec_from_file_location(full_name, path)
    if spec is None or spec.loader is None:
        raise ImportError('No se pudo cargar %s desde %s' % (mod_name, path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = mod
    spec.loader.exec_module(mod)
    return mod
