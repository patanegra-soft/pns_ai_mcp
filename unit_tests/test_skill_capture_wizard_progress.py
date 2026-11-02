# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Capture wizard: stop the AI pass and show tokens from the usage source."""
from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_WIZARD = _ROOT / 'common' / 'wizard' / 'skill_capture_wizard.py'
_VIEW = _ROOT / 'common' / 'wizard' / 'skill_capture_wizard_views.xml'
_OWL2_JS = (
    _ROOT / 'stacks' / 'owl2' / 'pns_ai_mcp'
    / 'static' / 'src' / 'js' / 'skill_capture_wizard.js'
)
_OWL1_JS = (
    _ROOT / 'stacks' / 'owl1' / 'pns_ai_mcp'
    / 'static' / 'src' / 'js' / 'skill_capture_wizard_v14.js'
)


def test_snapshot_reads_bundle_usage():
    src = _WIZARD.read_text(encoding='utf-8')
    assert 'def _snapshot_authored_capture' in src
    assert "bundle.get('usage')" in src
    assert "bundle.get('provider')" in src
    assert 'def _step_reply' in src
    assert 'return self._step_reply' in src
    assert "dict(prior.get('usage') or {})" in src


def test_progress_row_has_stop_and_usage():
    xml = _VIEW.read_text(encoding='utf-8')
    assert 'o_skill_capture_stop' in xml
    assert 'o_skill_capture_usage' in xml
    assert 'fa-stop-circle-o' in xml
    assert 'name="action_abort_author"' in xml
    assert 'type="button"' in xml


def test_wizard_basic_hides_advanced_until_toggled():
    xml = _VIEW.read_text(encoding='utf-8')
    src = _WIZARD.read_text(encoding='utf-8')
    assert 'name="show_advanced"' in xml
    assert 'name="action_toggle_advanced"' in xml
    assert 'string="Advanced"' in xml
    assert 'string="Hide advanced"' in xml
    assert "('show_advanced', '=', False)" in xml
    assert 'Leave empty for automatic generation.' in xml
    assert 'alert alert-info o_skill_param_token_legend' in xml
    assert '__SKILL_PARAM_TOKEN_LEGEND__' in xml
    assert xml.index('o_skill_param_token_legend') < xml.index(
        'string="Parameters"',
    )
    assert xml.index('__SKILL_PARAM_TOKEN_LEGEND__') < xml.index(
        'name="param_line_ids"',
    )
    assert 'string="Parameters" col="1"' in xml
    assert 'def action_toggle_advanced' in src
    assert 'skip_skill_form_author' in src


def test_skill_form_authors_help_not_code():
    import re
    from _load_addon import skill_source
    skill_py = skill_source()
    method = re.split(
        r'\n    (?:@|def )',
        skill_py.split('def _author_form_help_and_params', 1)[1], 1,
    )[0]
    assert '_author_param_help' in method
    assert '_author_param_schema' in method
    assert '_rewrite_code_for_params' not in method
    assert 'install_mode' in skill_py.split(
        'def _skill_form_author_allowed', 1,
    )[1].split('def _resolve_inference_provider', 1)[0]
    for rel in (
        'stacks/owl1/pns_ai_mcp/views/ai_skill_views.xml',
        'stacks/owl2/pns_ai_mcp/views/ai_skill_views.xml',
    ):
        xml = (_ROOT / rel).read_text(encoding='utf-8')
        assert 'Leave empty for automatic generation.' in xml


def test_js_cancels_without_inventing_tokens():
    for path in (_OWL2_JS, _OWL1_JS):
        js = path.read_text(encoding='utf-8')
        assert '_pnsCaptureAborted' in js
        assert 'o_skill_capture_stop' in js
        assert 'Cancelled.' in js
        assert 'usageHasTokens' in js or 'ai_usage_chip' in js
        assert 'formatUsageChip' in js or 'setUsageElementsWithFx' in js
        assert 'return "-"' not in js
        assert "return '-'" not in js
