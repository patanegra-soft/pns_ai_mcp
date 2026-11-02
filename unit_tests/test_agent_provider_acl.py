# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Internal users can read the agent↔provider chain (form entry); write stays admin."""
from __future__ import annotations

from _load_addon import addon_file


def _acl_rows():
    text = addon_file('security', 'ir.model.access.csv').read_text(encoding='utf-8')
    return [line.strip() for line in text.splitlines() if line.strip()]


def test_plain_user_can_read_agent_provider_join():
    rows = _acl_rows()
    user = [
        r for r in rows
        if r.startswith('access_ai_agent_provider_user,')
    ]
    admin = [
        r for r in rows
        if r.startswith('access_ai_agent_provider_admin,')
    ]
    assert len(user) == 1, user
    assert len(admin) == 1, admin
    assert user[0].endswith(',base.group_user,1,0,0,0')
    assert admin[0].endswith(',group_ai_admin,1,1,1,1')
