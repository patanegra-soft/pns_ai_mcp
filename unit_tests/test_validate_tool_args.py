# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Catalogue inputSchema: nested required body, no vendor names."""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from common.lib.api.validate_tool_args import check_tool_arguments

# Anonymous POST: body.data required (shape of many OpenAPI wrappers).
_BODY_DATA_SCHEMA = {
    'type': 'object',
    'required': ['body'],
    'properties': {
        'body': {
            'type': 'object',
            'required': ['data'],
            'properties': {
                'data': {
                    'type': 'object',
                    'properties': {
                        'flag': {'type': 'integer', 'enum': [0, 1]},
                    },
                },
            },
        },
    },
}


def test_empty_body_missing_data():
    issue = check_tool_arguments(_BODY_DATA_SCHEMA, {'body': {}})
    assert issue == {'kind': 'missing', 'name': 'data', 'path': 'arguments.body'}


def test_missing_body():
    issue = check_tool_arguments(_BODY_DATA_SCHEMA, {})
    assert issue == {'kind': 'missing', 'name': 'body', 'path': 'arguments'}


def test_body_data_object_ok():
    assert check_tool_arguments(
        _BODY_DATA_SCHEMA, {'body': {'data': {}}}
    ) is None


def test_empty_schema_is_noop():
    assert check_tool_arguments({}, {'body': {}}) is None
    assert check_tool_arguments(None, {}) is None


def test_wrong_body_type():
    issue = check_tool_arguments(_BODY_DATA_SCHEMA, {'body': []})
    assert issue == {'kind': 'type', 'path': 'arguments.body', 'expected': 'object'}
