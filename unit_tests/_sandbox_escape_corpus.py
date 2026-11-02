# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Escape-payload corpus (red-team) for the relaxaicode sandbox (box A).

Pure data, no dependencies, easy to extend. Consumed by the host unit
test (unit_tests/test_relaxaicode_sandbox_escapes.py) and the Odoo E2E
(common/tests/test_relaxaicode_sandbox_escapes_e2e.py keeps a minimal
copy because unit_tests/ is not shipped inside the addon at runtime).

Each payload is a real Python-sandbox escape: class walking
(``().__class__.__bases__[0].__subclasses__()``), frame/traceback access
to reach process builtins, and ``string.Formatter().get_field`` to get
internals without using '.'.
"""

# ── Payloads the AST layer (validate_relaxaicode_source_ast) MUST reject.
# They cover LITERAL names: dunders, Formatter, imports, class, format-strings.
AST_BLOCKED = [
    # Class walking through dots (regression: already covered).
    "result = ().__class__.__bases__[0].__subclasses__()",
    "result = [].__class__",
    "result = {}.__class__.__mro__",
    "result = (lambda: 0).__code__",
    "result = (lambda: 0).__globals__",
    # getattr/setattr/delattr with a LITERAL dangerous attribute.
    "result = getattr((), '__class__')",
    "result = getattr((), '__globals__')",
    "obj = ()\nsetattr(obj, '__class__', int)\nresult = 1",
    # Frames / tracebacks → the process's real builtins.
    "try:\n    1 / 0\nexcept Exception as e:\n    tb = e.__traceback__\nresult = 1",
    "def f():\n    return f.f_globals\nresult = f()",
    # string.Formatter: get_field/vformat return the real object.
    "result = string.Formatter().get_field('0.__class__', [()], {})",
    "result = string.Formatter().vformat('{0}', [1], {})",
    # format-string with dunder access.
    "result = '{0.__class__}'.format(())",
    "result = '{0.__class__.__bases__}'.format(())",
    # Class definition (direct and dynamic via type()).
    "class X(object):\n    pass\nresult = 1",
    "result = type('X', (), {})",
    # Dangerous imports (direct, from and dynamic).
    "import os\nresult = 1",
    "from os import system\nresult = 1",
    "from subprocess import Popen\nresult = 1",
    "result = __import__('os')",
    "import importlib\nresult = 1",
    # External API bypass via ORM (must go through Safe Plan api_call).
    "srv = env['ai.api.server'].search([], limit=1)\nresult = srv._get_driver()",
    "srv = env['ai.api.server'].search([], limit=1)\nresult = srv._get_driver().call(srv, 'X', {}, auth_token='t')",
    "result = getattr(env['ai.api.server'].search([], limit=1), '_resolve_auth_token')()",
    # F1IZ theater: inspect catalog/spec without drivers (search/browse + spec_json).
    "srv = env['ai.api.server'].search([('code', '=', 'x')], limit=1)\nresult = srv.spec_json",
    "srv = env['ai.api.server'].browse(6)\nresult = srv.spec_json",
    "srv = env.get('ai.api.server').search([], limit=1)\nresult = srv.tools_json",
    "result = env['ai.api.server'].browse(1).config_json",
    "result = getattr(env.user, 'spec_json', None)",
    # Knowledge catalog: listing/loading packs is get_context, not ORM.
    "recs = env['ai.context'].search([('code', 'ilike', 'self')])\nresult = [{'id': r.id, 'code': r.code, 'content': r.content} for r in recs]",
    "recs = env.get('ai.context').search([])\nresult = recs",
    "recs = env.sudo()['ai.context'].search([])\nresult = recs",
    "recs = env['ai.skill'].search([])\nresult = [{'code': r.code, 'body': r.code_body} for r in recs]",
    "result = env.sudo()['ai.skill'].search([])",
    "result = env['ai.' + 'context'].search([])",
    "recs = env['ai.trusted.action'].search([])\nresult = [{'code': r.code} for r in recs]",
    "result = env.sudo()['ai.trusted.action'].search([])",
]

# ── Attribute names guarded_getattr MUST reject even when they arrive already
# resolved at runtime (name built dynamically, invisible to the AST).
GETATTR_BLOCKED_NAMES = [
    '__class__',
    '__bases__',
    '__subclasses__',
    '__globals__',
    '__builtins__',
    '__code__',
    '__mro__',
    '__reduce__',
    '__getattribute__',
    'f_back',
    'f_globals',
    'f_locals',
    'tb_frame',
    'gi_frame',
    'cr',
    '_cr',
    'registry',
    '_get_driver',
    '_resolve_auth_token',
    'spec_json',
    'tools_json',
    'resources_json',
    'prompts_json',
    'auth_token',
    'config_json',
    'env_vars',
    # Intrusion 2026-08-12: ORM mutators via dynamic getattr (A6 bypass).
    'create',
    'write',
    'unlink',
    'copy',
]

# ── Obfuscated write: the AST must flag requires_write (do not run in box A).
AST_REQUIRES_WRITE = [
    "p = env['res.partner'].browse(1)\np.write({'comment': 'x'})\nresult = 1",
    "p = env['res.partner'].browse(1)\ngetattr(p, 'wr'+'ite')({'comment': 'x'})\nresult = 1",
    "p = env['res.partner'].browse(1)\ngetattr(p, 'write')({'comment': 'x'})\nresult = 1",
    "from operator import attrgetter\np = env['res.partner'].browse(1)\nattrgetter('write')(p)({'comment': 'x'})\nresult = 1",
    "import operator\np = env['res.partner'].browse(1)\noperator.attrgetter('wr'+'ite')(p)({'comment': 'x'})\nresult = 1",
    "op = env['ai.safe.operation'].browse(1)\ngetattr(op, 'resolve_execute')()\nresult = 1",
    "op = env['ai.safe.operation'].browse(1)\ngetattr(op, 'resolve_' + 'execute')()\nresult = 1",
    "from operator import methodcaller\nop = env['ai.safe.operation']\nmethodcaller('cleanup_expired')(op)\nresult = 1",
    "from operator import attrgetter\nop = env['ai.safe.operation']\nattrgetter('cleanup_stuck_state')(op)()\nresult = 1",
]

# ── Attribute names guarded_getattr MUST allow (legitimate ORM use).
GETATTR_ALLOWED_NAMES = [
    'name',
    'display_name',
    '_name',
    '_fields',
    '__last_update',  # dunder prefix but does NOT end in '__' → allowed
    'id',
]

# ── Imports guarded_import MUST reject (ImportError).
IMPORT_BLOCKED = [
    'os',
    'sys',
    'subprocess',
    'socket',
    'requests',
    'urllib',
    'http',
    'importlib',
    'pickle',
    'ctypes',
    'builtins',
    'odoo',
]

# ── Imports guarded_import MUST allow (safe modules).
IMPORT_ALLOWED = [
    'json',
    'math',
    'datetime',
    'collections',
    'itertools',
    're',
    'decimal',
]

# ── DOT leaks from a safe module to another module (os/sys) or to
# a file/process primitive. The AST accepts them (they are normal names);
# the runtime facade must cut them. Each one ran a real command.
RUNTIME_MODULE_ESCAPES = [
    "import platform\nresult = platform.os.system('echo x')",
    "import platform\nresult = platform.os.environ",
    "import uuid\nresult = uuid.os.listdir('/')",
    "import random\nresult = random._os.getpid()",
    "import calendar\nresult = calendar.sys.modules",
    "result = datetime.sys.modules",
    "result = uuid.os.getcwd()",
    "result = io.open('/etc/hostname').read()",
    "from platform import os\nresult = os.getpid()",
    "import json\nresult = json.decoder.sys",
    "import collections\nresult = getattr(collections, 'ab' + 'c')",
]

# ── Legitimate use of the same modules: must keep working after the facade.
RUNTIME_MODULE_ALLOWED = [
    "result = datetime.datetime(2026, 1, 2).isoformat()",
    "from datetime import datetime as dt, timedelta\nresult = (dt(2026, 1, 2) + timedelta(days=1)).day",
    "import json\nresult = json.loads(json.dumps({'a': 1}))['a']",
    "result = isinstance(date(2026, 1, 1), datetime.date)",
    "buf = io.StringIO()\nbuf.write('x')\nresult = buf.getvalue()",
    "result = len(str(uuid.uuid4()))",
    "result = calendar.monthrange(2026, 2)[1]",
    "import re\nresult = re.sub(r'\\s+', ' ', 'a   b')",
    "result = collections.Counter('aab')['a']",
]

# ── Identity change: RelaxAICode always reads as the user who asks.
# With sudo / with_user(1) / env(su=True) other people's keys and data were read.
AST_PRIVILEGE_BLOCKED = [
    "result = env.sudo()['ai.provider'].search([]).mapped('api_key')",
    "result = env['ir.config_parameter'].sudo().get_param('database.secret')",
    "result = env['res.partner'].with_user(1).search([])",
    "result = env.user.sudo().name",
    "result = env.user.env['ai.provider']",
    "result = env._env",
    "result = getattr(env.user, 'sudo')()",
    "import operator\nresult = operator.methodcaller('sudo')(env.user)",
    "from operator import attrgetter\nresult = attrgetter('env')(env.user)",
]

# The same ideas with the name built at runtime (the AST does not see it).
RUNTIME_PRIVILEGE_ESCAPES = [
    "result = getattr(env['res.partner'], 'su' + 'do')()",
    "result = operator.methodcaller('su' + 'do')(env['res.partner'])",
    "result = operator.attrgetter('wi' + 'th_user')(env['res.partner'])(1)",
    "result = getattr(env, 'su' + 'do')()",
    "result = env(su=True)",
    "result = env(user=1)",
]

# ── LEGITIMATE code that must NOT break after the hardening (false
# positives = functional regression). It must pass the AST.
AST_ALLOWED = [
    "result = {'v': odoo_version}",
    "recs = env['res.partner'].search([], limit=5)\nresult = [r.name for r in recs]",
    "result = getattr(env.user, 'name', 'x')",
    "result = getattr(env.user, '_name', '')",
    "result = '{0} {1}'.format('a', 'b')",
    "result = '{name}'.format(name='x')",
    "result = '{0.name}'.format(env.user)",
    "vals = [1, 2, 3]\nresult = sorted(vals, key=lambda x: x)",
    "result = format_number(1234.5)",
    "import json\nresult = json.dumps({'a': 1})",
    "result = string.ascii_letters",
]
