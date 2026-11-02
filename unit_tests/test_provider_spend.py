# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Monthly spend cap of a provider: in dollars when the cost is known, else in tokens."""
from _load_addon import load_module

s = load_module('provider_spend', 'utils', 'provider_spend.py')


def test_empty_cap_never_hits():
    assert not s.spend_cap_hit({'cost': 9, 'total_tokens': 9000})
    assert not s.spend_cap_hit({'cost': 9}, cap_usd=0)
    assert not s.spend_cap_hit({'total_tokens': 9}, cap_tokens=0)


def test_usd_cap_when_cost_is_known():
    assert s.spend_cap_hit({'cost': 10, 'total_tokens': 1}, cap_usd=10, cap_tokens=100)
    assert not s.spend_cap_hit({'cost': 9, 'total_tokens': 999}, cap_usd=10, cap_tokens=100)


def test_token_cap_when_there_is_no_cost():
    assert s.spend_cap_hit({'total_tokens': 100}, cap_usd=5, cap_tokens=100)
    assert not s.spend_cap_hit({'prompt_tokens': 40, 'completion_tokens': 50}, cap_tokens=100)
    assert s.spend_cap_hit({'prompt_tokens': 40, 'completion_tokens': 60}, cap_tokens=100)


def test_does_not_invent_euros_from_tokens():
    assert not s.spend_cap_hit({'total_tokens': 99999}, cap_usd=1)
