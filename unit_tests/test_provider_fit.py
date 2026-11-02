# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Provider tags: none means any turn; a tick limits the turn."""
from __future__ import annotations

from _load_addon import load_module

fit = load_module('provider_fit', 'utils', 'provider_fit.py')


def test_no_flags_are_text_only():
    flags = {}
    assert fit.provider_fits(flags, 'conversation') is True
    assert fit.provider_fits(flags, 'vision') is False
    assert fit.provider_fits(flags, 'audio') is False
    assert fit.provider_fits(flags, 'design') is False


def test_audio_only_skips_text():
    flags = {'audio': True}
    assert fit.provider_fits(flags, 'audio') is True
    assert fit.provider_fits(flags, 'conversation') is False
    assert fit.provider_fits(flags, 'vision') is False


def test_conversation_only_skips_a_photo_and_a_clip():
    flags = {'conversation': True}
    assert fit.provider_fits(flags, 'conversation') is True
    assert fit.provider_fits(flags, 'vision') is False
    assert fit.provider_fits(flags, 'audio') is False


def test_a_tick_the_catalogue_denies_is_a_mismatch():
    ticks = {'conversation': True, 'audio': True}
    known = {'conversation': True, 'audio': False, 'vision': False}
    assert fit.fit_mismatches(ticks, known) == ['audio']
    # A Whisper row under a Conversation tick is the same mistake.
    assert fit.fit_mismatches(
        {'conversation': True},
        {'conversation': False, 'audio': True, 'vision': False},
    ) == ['conversation']


def test_a_silent_catalogue_judges_nothing():
    ticks = {'audio': True, 'vision': True, 'video': True}
    assert fit.fit_mismatches(ticks, {}) == []
    assert fit.fit_mismatches(ticks, None) == []
    # A key the catalogue does not publish (video) is not judged.
    assert fit.fit_mismatches(ticks, {'audio': True, 'vision': True}) == []


def test_design_only_skips_a_text_turn():
    flags = {'design': True}
    assert fit.provider_fits(flags, None) is False
    assert fit.provider_fits(flags, 'conversation') is False
    assert fit.provider_fits(flags, 'design') is True
    assert fit.provider_fits({}, 'design') is False


def test_parser_only_skips_a_text_turn_and_is_a_specialist():
    flags = {'parser': True}
    assert fit.provider_fits(flags, None) is False
    assert fit.provider_fits(flags, 'conversation') is False
    assert fit.provider_fits(flags, 'parser') is True
    assert fit.provider_fits({}, 'parser') is False
    assert fit.is_specialist(flags, 'parser') is True
    # A model the catalogue says cannot chat cannot parse either.
    assert fit.fit_mismatches(flags, {'parser': False}) == ['parser']


def test_conversation_and_vision():
    flags = {'conversation': True, 'vision': True}
    assert fit.provider_fits(flags, 'conversation') is True
    assert fit.provider_fits(flags, 'vision') is True
    assert fit.provider_fits(flags, 'audio') is False


def test_an_audio_only_provider_is_tested_with_the_speech_probe_not_a_chat():
    """A transcription model rejects chat/completions; the test must not ask it to say ok."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    src = (root / 'common' / 'models' / 'ai_provider.py').read_text(encoding='utf-8')
    body = src.split('    def test_connection(self):', 1)[1].split('\n    def ', 1)[0]
    gate = body.index("if self._hears() and not self._has_role('conversation'):")
    assert gate < body.index('driver.chat_completion(')
    assert '_test_speech_connection(target_model)' in body
    speech = src.split('def _test_speech_connection', 1)[1].split('\n    def ', 1)[0]
    assert 'probe_stt(' in speech
    assert 'chat_completion' not in speech
    # A model that answers no speech verb is an error, not a green toast.
    assert "if speech == 'no':" in speech


def test_saving_an_audio_tick_sends_the_silent_clip_and_a_no_fails_the_save():
    """The admin learns the model is wrong at save time; the walkie keeps its failover."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    src = (root / 'common' / 'models' / 'ai_provider.py').read_text(encoding='utf-8')
    gate = src.split('def _gate_audio_tick_on_save', 1)[1].split('\n    def ', 1)[0]
    assert '_probe_stt_support(' in gate
    assert "if speech == 'no':" in gate
    assert 'raise ValidationError' in gate
    # Network or auth trouble does not block the save.
    assert "speech != 'unknown'" in gate
    write = src.split('    def write(self, vals):', 1)[1].split('\n    def ', 1)[0]
    assert '_gate_audio_tick_on_save()' in write
    create = src.split('    def create(self, vals_list):', 1)[1].split('\n    def ', 1)[0]
    assert '_gate_audio_tick_on_save()' in create
    for key in ('model_id', 'role_ids', 'endpoint', 'protocol'):
        assert "'%s'" % key in src.split('_SPEECH_GATE_KEYS = ', 1)[1].split('\n', 1)[0]
    # Any role that takes audio is guarded, not only the engine's Audio.
    assert 'if not rec._hears()' in gate
    hears = src.split('    def _hears(self):', 1)[1].split('\n    def ', 1)[0]
    assert "role.accepts == 'audio'" in hears


def test_the_backup_carries_only_the_switches_of_a_role():
    """A role is the module's: the backup restores active / use_fallback, never makes one."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    backup = (root / 'common' / 'utils' / 'config_backup.py').read_text(encoding='utf-8')
    export = backup.split('def _export_provider_roles', 1)[1].split('\ndef ', 1)[0]
    for key in ("'active': r.active", "'use_fallback': r.use_fallback",
                "'bg_color': r.own_bg_color", "'fg_color': r.own_fg_color"):
        assert key in export
    imp = backup.split('def _import_provider_roles', 1)[1].split('\ndef ', 1)[0]
    assert '.create(' not in imp
    assert "for key in ('active', 'use_fallback') if key in row" in imp
    assert "vals['own_' + key]" in imp
    assert "is not installed here; skipped." in imp
    assert "'provider_roles': _export_provider_roles(env)" in backup
    for caller in ('def import_config', 'def import_partial'):
        body = backup.split(caller, 1)[1].split('\ndef ', 1)[0]
        assert '_import_provider_roles(' in body
    bundle = (root / 'common' / 'utils' / 'artifact_bundle.py').read_text(encoding='utf-8')
    assert bundle.count("'provider_roles.json'") >= 3


def test_no_handwritten_role_list_in_the_fit_rule():
    """The roles are records; the rule reads whatever codes the provider holds."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    src = (root / 'common' / 'utils' / 'provider_fit.py').read_text(encoding='utf-8')
    assert 'FITS' not in src
    flags = {'barcode': True}
    assert fit.provider_fits(flags, 'barcode') is True
    assert fit.provider_fits(flags, None) is False
    assert fit.is_specialist(flags, 'barcode') is True


def test_roles_are_seeded_with_text_tasks_falling_to_conversation():
    import xml.etree.ElementTree as ET
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    seed = ET.parse(root / 'common' / 'data' / 'ai_provider_role_data.xml').getroot()
    roles = {}
    for rec in seed.iter('record'):
        assert rec.get('model') == 'ai.provider.role'
        vals = {f.get('name'): (f.text, f.get('ref')) for f in rec.iter('field')}
        roles[rec.get('id')] = vals
    codes = {vals['code'][0]: xid for xid, vals in roles.items()}
    assert set(codes) == {
        'conversation', 'audio', 'vision', 'video', 'decision', 'design', 'parser',
    }
    fallbacks = {
        vals['code'][0]: vals['fallback_id'][1]
        for vals in roles.values() if 'fallback_id' in vals
    }
    # Decision never falls: nobody holding it means no.
    assert fallbacks == {
        'parser': codes['conversation'],
        'design': codes['conversation'],
    }
    # The database's own switches are not seeded, so a -u does not undo them.
    for switch in ('active', 'use_fallback'):
        assert all(switch not in vals for vals in roles.values())
    role = (root / 'common' / 'models' / 'ai_provider_role.py').read_text(encoding='utf-8')
    shipped = role.split('_SHIPPED_FIELDS = ', 1)[1].split(')', 1)[0]
    assert 'use_fallback' not in shipped and "'active'" not in shipped


def test_old_fit_columns_move_to_roles_once_the_roles_exist():
    """O14 skips migrations/3.1.*, and a -u drops a removed field's column
    before the roles are seeded: init stashes the ticks, the load hands them on."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    fossils = (root / 'common' / 'utils' / 'schema_fossils.py').read_text(encoding='utf-8')
    stash = fossils.split('def stash_fit_columns', 1)[1].split('\ndef ', 1)[0]
    assert stash.index('INSERT INTO') < stash.index('_drop_column_if_exists(')
    move = fossils.split('def promote_fit_columns', 1)[1].split('\ndef ', 1)[0]
    assert 'ON CONFLICT DO NOTHING' in move
    assert 'JOIN ai_provider_role r ON r.code = s.code' in move
    # The stash goes only once every tick found its role.
    assert move.index('LIMIT 1') < move.index('DROP TABLE')
    init = (root / 'common' / 'models' / 'ai_schema_fossil.py').read_text(encoding='utf-8')
    assert init.index('promote_decision_provider(cr)') < init.index('stash_fit_columns(cr)')
    assert 'promote_fit_columns' not in init
    role = (root / 'common' / 'models' / 'ai_provider_role.py').read_text(encoding='utf-8')
    hook = role.split('def _register_hook', 1)[1]
    assert 'promote_fit_columns' in hook


def test_a_chip_wears_its_role_colours_not_a_css_list():
    """A module's new role brings its colour; the database may pick its own,
    kept apart from the module's so a -u does not take it back."""
    import re
    import xml.etree.ElementTree as ET
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    for stack in ('owl1', 'owl2'):
        css = (root / 'stacks' / stack / 'pns_ai_mcp' / 'static' / 'src' / 'css'
               / 'pns_list.css').read_text(encoding='utf-8')
        assert re.findall(r'\.o_pns_fit_chip--(\w+)', css) == ['text']
        view = (root / 'stacks' / stack / 'pns_ai_mcp' / 'views'
                / 'ai_provider_role_views.xml').read_text(encoding='utf-8')
        assert '<field name="bg_color" widget="color"/>' in view
        assert '<field name="fg_color" widget="color"/>' in view
    seed = ET.parse(root / 'common' / 'data' / 'ai_provider_role_data.xml').getroot()
    for rec in seed.iter('record'):
        names = {f.get('name') for f in rec.iter('field')}
        assert {'module_bg_color', 'module_fg_color'} <= names, rec.get('id')
        assert not names & {'own_bg_color', 'own_fg_color'}
    role = (root / 'common' / 'models' / 'ai_provider_role.py').read_text(encoding='utf-8')
    shipped = role.split('_SHIPPED_FIELDS = ', 1)[1].split(')', 1)[0]
    assert "'module_bg_color'" in shipped and "'own_bg_color'" not in shipped
    provider = (root / 'common' / 'models' / 'ai_provider.py').read_text(encoding='utf-8')
    chips = provider.split('def _compute_fit_chips_html', 1)[1].split('\n    def ', 1)[0]
    assert 'role._chip(' in chips


def test_picking_the_module_colour_keeps_none_of_its_own():
    import ast
    import re
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    src = (root / 'common' / 'models' / 'ai_provider_role.py').read_text(encoding='utf-8')
    tree = ast.parse(src)
    ns = {'re': re}
    keep = [
        n for n in tree.body
        if (isinstance(n, ast.Assign) and n.targets[0].id in ('_HEX', '_CHIP_BG', '_CHIP_FG'))
        or (isinstance(n, ast.FunctionDef) and n.name == '_hex')
    ]
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
    own = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_own_colour')
    own.decorator_list = []
    exec(compile(ast.Module(body=keep + [own], type_ignores=[]), 'role', 'exec'), ns)
    pick = ns['_own_colour']
    assert pick('#17A2B8', '#17a2b8', '#6c757d') is False
    assert pick('#ff0000', '#17a2b8', '#6c757d') == '#ff0000'
    assert pick('', '#17a2b8', '#6c757d') is False
    # A role shipped with no colour wears the grey; picking grey keeps none.
    assert pick('#6c757d', False, '#6c757d') is False
    assert ns['_hex']('red;"><script>', '#6c757d') == '#6c757d'


def test_the_log_names_the_provider_and_why_each_one_failed():
    """A parser on the wrong protocol answered empty; the log has to say so."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    skills = (root / 'common' / 'utils' / 'engine_skills.py').read_text(encoding='utf-8')
    hybrid = skills.split("tool_name='skill_param_hybrid'", 1)[1].split('return merged', 1)[0]
    assert 'provider_id=prov.id if prov else None' in hybrid
    loop = skills.split('for cand in chain:', 1)[1].split('if (\n', 1)[0]
    assert "'empty reply'" in loop and "get('error')" in loop
    provider = (root / 'common' / 'models' / 'ai_provider.py').read_text(encoding='utf-8')
    for summary in ('Manual Test Speech Connection', 'Manual Test Decision Connection',
                    'Manual Test LLM Connection'):
        row = provider.split(summary, 1)[1].split('except Exception', 1)[0]
        assert 'provider_id=self.id' in row, summary
    test = provider.split('    def test_connection(self):', 1)[1].split('\n    def ', 1)[0]
    assert test.index('answered with no text') < test.index('Connection Successful')


def test_an_endpoint_the_protocol_does_not_post_to_fails_on_save():
    """Anthropic over OpenRouter's /chat/completions answered empty, silently."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    drivers = root / 'common' / 'lib' / 'llm' / 'drivers'
    base = (drivers / 'base.py').read_text(encoding='utf-8')
    assert "    endpoint_path = ''" in base
    anthropic = (drivers / 'anthropic_driver.py').read_text(encoding='utf-8')
    assert "    endpoint_path = '/messages'" in anthropic
    assert anthropic.index('"""Driver for Anthropic') < anthropic.index('endpoint_path')
    provider = (root / 'common' / 'models' / 'ai_provider.py').read_text(encoding='utf-8')
    check = provider.split('def _check_endpoint_matches_protocol', 1)[1].split('\n    @', 1)[0]
    assert '_driver().endpoint_path' in check
    assert 'protocol ==' not in check


def test_a_role_is_shipped_by_a_module_not_made_on_screen():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    role = (root / 'common' / 'models' / 'ai_provider_role.py').read_text(encoding='utf-8')
    for verb in ('def create', 'def write', 'def unlink'):
        body = role.split(verb, 1)[1].split('\n    def ', 1)[0]
        assert 'self.env.su' in body
    shipped = role.split('_SHIPPED_FIELDS = ', 1)[1].split(')', 1)[0]
    # What a -u writes again is not editable on screen either.
    for key in ('code', 'name', 'description', 'sequence', 'accepts', 'fallback_id'):
        assert "'%s'" % key in shipped
        field = role.split('    %s = fields.' % key, 1)[1].split('\n    )', 1)[0]
        assert 'readonly=True' in field.split('\n    def ', 1)[0]
    acl = (root / 'common' / 'security' / 'ir.model.access.csv').read_text(encoding='utf-8')
    rows = [line for line in acl.splitlines() if 'model_ai_provider_role,' in line]
    assert rows and all(line.endswith(',0,0') for line in rows)
