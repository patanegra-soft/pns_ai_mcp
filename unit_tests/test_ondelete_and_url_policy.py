# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""ondelete and the Settings URL policy stay on our side."""
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_ONDELETE = (
    _ROOT / 'common' / 'models' / 'ir_model_fields_selection.py'
).read_text(encoding='utf-8')
_SETTINGS = (
    _ROOT / 'common' / 'models' / 'res_config_settings.py'
).read_text(encoding='utf-8')
_HTTP = (_ROOT / 'common' / 'http_patch.py').read_text(encoding='utf-8')


def test_ondelete_skip_only_pns_models():
    assert 'def _pns_model_is_ours' in _ONDELETE
    assert "startswith('pns')" in _ONDELETE
    assert 'and self._pns_model_is_ours(model_name)' in _ONDELETE


def test_url_policy_not_rewritten_when_unchanged():
    assert 'if new_policy != old_policy:' in _SETTINGS
    assert "ICP.set_param('pns_ai_mcp.url_access_policy', new_policy)" in _SETTINGS


def test_root_get_request_documents_process_scope():
    assert '/mcp' in _HTTP
    assert 'process' in _HTTP.lower()
