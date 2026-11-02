# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""A correction rewrites the pending authorisation. It does not open another."""
from _load_addon import safe_plan_source


def test_request_replaces_a_pending_row_before_creating_one():
    src = safe_plan_source()
    fn = src.split('def request_safe_plan(')[1].split('\ndef ')[0]
    assert 'replace_verification_id=None' in fn[:500]
    assert fn.index('_replace_pending_plan(') < fn.index('create_verification(')
    body = src.split('def _replace_pending_plan(')[1].split('\ndef ')[0]
    assert "('status', '=', 'pending')" in body
    assert 'op.write(' in body
    assert 'create_verification' not in body
    assert "'replaced_pending': True" in body
