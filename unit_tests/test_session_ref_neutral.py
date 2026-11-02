# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""The engine carries the host's session as ``ai_session_ref``, not by a host's name."""
import ast
from pathlib import Path

from _load_addon import addon_file, safe_plan_source

_ROOT = Path(__file__).resolve().parents[1]
_GONE = (
    'chatboo_session_id',
    'chatboo_options',
    'resolve_chatboo_session_id',
    'persist_chatboo_session_file',
    'chatboo_card_payload',
    'chatboo_pending_card_payloads',
    'from_chatboo',
)


def _joined(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _joined(node.left) + _joined(node.right)
    return ''


def test_engine_tells_no_one_about_chatboo():
    """What a person reads (``_()``, ``help=``, ``string=``) says «the chat», not a host."""
    found = []
    for path in _engine_python():
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            texts = []
            if isinstance(node.func, ast.Name) and node.func.id == '_':
                texts += [_joined(a) for a in node.args[:1]]
            texts += [_joined(k.value) for k in node.keywords if k.arg in ('help', 'string')]
            found += ['%s:%s' % (path.relative_to(_ROOT), node.lineno)
                      for t in texts if 'Chatboo' in t]
    for path in (_ROOT / 'stacks').rglob('views/*.xml'):
        text = path.read_text(encoding='utf-8')
        found += ['%s: placeholder' % path.relative_to(_ROOT)
                  for chunk in text.split('placeholder="')[1:] if 'Chatboo' in chunk.split('"', 1)[0]]
    assert found == []


def test_capture_wizard_names_no_host():
    wizard = _ROOT / 'common' / 'wizard'
    for name in ('skill_capture_wizard.py', 'skill_capture_wizard_views.xml'):
        assert 'Chatboo' not in (wizard / name).read_text(encoding='utf-8')
    py = (wizard / 'skill_capture_wizard.py').read_text(encoding='utf-8')
    assert 'from_chat = fields.Boolean(' in py
    assert "'active': bool(self.from_chat)," in py


def _engine_python():
    for base in (_ROOT / 'common', _ROOT / 'stacks'):
        for path in base.rglob('*.py'):
            if 'tests' in path.parts or '__pycache__' in path.parts:
                continue
            yield path


def test_engine_names_no_host_session():
    found = []
    for path in _engine_python():
        text = path.read_text(encoding='utf-8')
        found += ['%s: %s' % (path.relative_to(_ROOT), name) for name in _GONE if name in text]
    assert found == []


def test_engine_markup_is_not_chatboo():
    """The engine writes ``data-ai-*`` / ``o_ai_*``; only the stored-rows rename names the old ones."""
    found = []
    for base in (_ROOT / 'common', _ROOT / 'stacks'):
        for path in base.rglob('*'):
            if path.suffix not in ('.py', '.xml', '.md', '.js', '.css') or path.name == 'markup_rename.py':
                continue
            if {'migrations', '__pycache__', 'tests'} & set(path.parts):
                continue
            text = path.read_text(encoding='utf-8')
            found += ['%s: %s' % (path.relative_to(_ROOT), old)
                      for old in ('data-chatboo-', 'o_chatboo_') if old in text]
    assert found == []


def _markup_rename():
    from importlib.util import module_from_spec, spec_from_file_location
    spec = spec_from_file_location('markup_rename', addon_file('utils', 'markup_rename.py'))
    rename = module_from_spec(spec)
    spec.loader.exec_module(rename)
    return rename


def test_stored_markup_rename_covers_the_engine_names():
    rename = _markup_rename()

    class _Cr:
        rowcount = 3

        def execute(self, sql, params):
            self.sql, self.params = sql, params

    cr = _Cr()
    assert rename.rename_stored_markup(cr, 'chatboo_session', 'messages') == 3
    n = 2 * len(rename.RENAMED)
    pairs = dict(zip(cr.params[0:n:2], cr.params[1:n:2]))
    assert pairs['data-chatboo-dataset='] == 'data-ai-dataset='
    assert pairs['data-chatboo-showmode='] == 'data-ai-show-mode='
    assert len(pairs) == len(rename.ENGINE_MARKUP) + 1
    assert cr.params[n:] == [rename.CLASS_PATTERN, r'o_ai_\1',
                             cr.params[-2], rename.CLASS_PATTERN]
    assert cr.params[-2].startswith('data-chatboo-(card|')
    assert cr.sql.startswith('UPDATE "chatboo_session" SET "messages" = regexp_replace(replace(')


def test_stored_class_rename_leaves_host_classes():
    import re
    rename = _markup_rename()
    html = ('<div class="o_chatboo_dashboard_card o_chatboo_dashboard_card_collapsed">'
            '<td class="o_chatboo_num"></td><div class="o_chatboo_map_banner o_chatboo_map_banner_gm">'
            '<span class="o_chatboo_bubble"></span>')
    out = re.sub(rename.CLASS_PATTERN, r'o_ai_\1', html)
    assert out == ('<div class="o_ai_dashboard_card o_chatboo_dashboard_card_collapsed">'
                   '<td class="o_ai_num"></td><div class="o_ai_map_banner o_ai_map_banner_gm">'
                   '<span class="o_chatboo_bubble"></span>')


def test_session_ref_travels_with_the_operation():
    safe_plan = safe_plan_source()
    assert "operation_data['ai_session_ref'] = int(session_id)" in safe_plan
    assert "for key in ('mcp_agent_code', 'ai_session_ref'):" in safe_plan
    operation = addon_file('models', 'safe_operation.py').read_text(encoding='utf-8')
    assert "data.get('ai_session_ref') or resolve_session_ref(self.env)" in operation
    download = addon_file('utils', 'session_download.py').read_text(encoding='utf-8')
    resolve = download.split('def resolve_session_ref', 1)[1].split('\ndef ', 1)[0]
    assert "get('ai_session_ref')" in resolve
    assert "getattr(http_request, 'ai_session_ref', None)" in resolve
