# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""OpenAPI wizard: stepped fetch/generate UI and RPC split."""
from __future__ import annotations

from pathlib import Path
from _load_addon import engine_source
from _tenant_needles import names_tenant

_ROOT = Path(__file__).resolve().parents[1]
_WIZARD = _ROOT / 'common' / 'wizard' / 'openapi_spec_generate_wizard.py'
_VIEW = _ROOT / 'common' / 'wizard' / 'openapi_spec_generate_wizard_views.xml'
_OWL1_ASSETS = (
    _ROOT / 'stacks' / 'owl1' / 'pns_ai_mcp' / 'views' / 'assets.xml'
)
_OWL2_JS = (
    _ROOT / 'stacks' / 'owl2' / 'pns_ai_mcp'
    / 'static' / 'src' / 'js' / 'openapi_spec_generate_wizard.js'
)
_OWL1_JS = (
    _ROOT / 'stacks' / 'owl1' / 'pns_ai_mcp'
    / 'static' / 'src' / 'js' / 'openapi_spec_generate_wizard_v14.js'
)


def test_wizard_split_fetch_and_generate_rpc():
    src = _WIZARD.read_text(encoding='utf-8')
    assert 'def action_fetch_documentation' in src
    assert 'def action_generate_openapi' in src
    assert 'def action_poll_generation' not in src
    assert 'def _spawn_generate_worker' not in src
    assert 'def _thread_manage_cm' not in src
    assert 'Environment.manage' not in src
    assert 'pending=True' not in src
    assert 'def _step_reply' in src
    assert 'inference_audit' in src
    assert 'def action_log_generation_usage' in src
    assert "openapi_spec_generate" in src
    assert "generation_state" in src
    assert "docs_text" in src
    assert "error_message" in src


def test_progress_row_has_stop_and_usage():
    xml = _VIEW.read_text(encoding='utf-8')
    assert 'o_skill_capture_progress' in xml
    assert 'o_skill_capture_stop' in xml
    assert 'o_skill_capture_usage' in xml
    assert 'fa-stop-circle-o' in xml
    assert 'name="action_abort_openapi"' in xml
    assert 'type="button"' in xml
    assert 'name="action_generate"' in xml
    assert 'string="Close" class="btn-secondary" special="cancel"' in xml
    assert 'string="Cancel" class="btn-secondary" special="cancel"' not in xml


def test_css_stop_has_icon_label_gap():
    for rel in (
        'stacks/owl1/pns_ai_mcp/static/src/css/skill_capture_wizard.css',
        'stacks/owl2/pns_ai_mcp/static/src/css/skill_capture_wizard.css',
    ):
        css = (_ROOT / rel).read_text(encoding='utf-8')
        assert '.o_skill_capture_stop' in css
        assert 'gap: 6px' in css


def test_owl1_assets_xml_includes_wizard_js():
    xml = _OWL1_ASSETS.read_text(encoding='utf-8')
    assert 'ai_usage_chip_v14.js' in xml
    assert 'openapi_spec_generate_wizard_v14.js' in xml


def test_js_steps_fetch_generate_and_cancel():
    for path in (_OWL2_JS, _OWL1_JS):
        js = path.read_text(encoding='utf-8')
        assert '_pnsOpenapiAborted' in js
        assert 'action_fetch_documentation' in js
        assert 'action_generate_openapi' in js
        assert 'action_poll_generation' not in js
        assert 'action_log_generation_usage' in js
        assert 'Cancel OpenAPI generation' in js
        assert 'Fetching documentation' in js
        assert 'Converting with AI Admin' in js
        assert 'Cancelling' in js
        assert 'current AI call' in js
        assert 'o_skill_capture_stop' in js
        assert 'act_window_close' in js
    owl2 = _OWL2_JS.read_text(encoding='utf-8')
    assert 'orm.silent.call.bind(orm.silent)' in owl2
    assert 'pollUntilDone' not in owl2
    assert 'model.root.load()' in owl2
    assert 'lastResult.ok === false' in owl2
    assert 'ConfirmationDialog' in owl2
    assert 'bindFooterCancel' in owl2
    assert 'closeWizard' in owl2
    owl1 = _OWL1_JS.read_text(encoding='utf-8')
    assert 'result.ok === false' in owl1
    assert '_pnsOpenapiPollUntilDone' not in owl1
    assert 'self.reload()' in owl1
    assert '{shadow: true}' in owl1
    assert 'window.confirm' in owl1
    assert 'pnsOpenapiFooterCancel' in owl1
    assert '_pnsOpenapiRequestCancel' in owl1
    assert '_pnsOpenapiCloseWizard' in owl1


def test_restore_factory_prompt_button_in_views():
    for rel in (
        'stacks/owl1/pns_ai_mcp/views/external_server_views.xml',
        'stacks/owl2/pns_ai_mcp/views/external_server_views.xml',
    ):
        xml = (_ROOT / rel).read_text(encoding='utf-8')
        assert 'action_restore_usage_guide' in xml
        assert 'Restore factory usage guide' in xml
        # OpenAPI prompt tab on the server form: edit + restore factory.
        assert 'string="OpenAPI prompt"' in xml
        assert xml.count('action_restore_openapi_gen_prompt') == 1
        assert 'Restore factory OpenAPI prompt' in xml
        assert 'string="Restore factory prompt"' not in xml
        assert 'this documentation page only' in xml
        assert 'eTLD+1' not in xml
        assert 'not OpenAPI generation' in xml
        wiz = (
            _ROOT / 'common' / 'wizard'
            / 'openapi_spec_generate_wizard_views.xml'
        ).read_text(encoding='utf-8')
        assert 'openapi_gen_prompt' in wiz
        assert 'action_restore_openapi_gen_prompt' in wiz


def test_factory_usage_guide_uses_pack_hooks_plug():
    src = (
        _ROOT / 'common' / 'models' / 'external_server.py'
    ).read_text(encoding='utf-8')
    block = src.split('def _factory_usage_guide', 1)[1].split(
        '\n    def action_restore_usage_guide', 1,
    )[0]
    assert 'factory_usage_guide_for_code' in block
    assert "odoo.addons.%s.hooks" % 'name' in block or (
        "odoo.addons.%s.hooks" % '% name' in block
        or "odoo.addons.%s.hooks' % name" in block
    )
    assert not names_tenant(block)


def test_llm_timeout_and_overflow_failover_for_openapi():
    from _load_addon import load_module
    gen = load_module(
        'openapi_spec_generator', 'services', 'openapi_spec_generator.py',
    )
    assert gen._LLM_TIMEOUT == 120
    assert gen._LLM_MAX_PROVIDERS == 2
    assert gen._LLM_MAX_TOKENS == 8192
    assert gen._MAX_LLM_CHARS == 24_000
    msg = gen._format_llm_call_error('urlopen error timed out')
    assert 'AI conversion timed out' in msg
    assert 'Tried up to 2' in msg
    gen_src = (
        _ROOT / 'common' / 'services' / 'openapi_spec_generator.py'
    ).read_text(encoding='utf-8')
    assert 'failover_on_overflow=True' in gen_src
    assert 'json_mode=False' in gen_src
    assert 'max_providers=_LLM_MAX_PROVIDERS' in gen_src
    wiz = _WIZARD.read_text(encoding='utf-8')
    assert "ok=False" in wiz
    assert 'error_message' in wiz
    assert 'raw_text' in wiz
    assert 'def _keep_llm_json' in wiz
    assert 'after_llm' in wiz
    assert 'Last reply starts with' not in gen_src
    assert 'after_llm=None' in gen_src
    engine = engine_source()
    assert 'failover_on_overflow=False' in engine
    assert 'max_providers=None' in engine
    assert 'ctx_size' in engine