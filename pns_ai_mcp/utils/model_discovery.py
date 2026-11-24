# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Model discovery that works the same for every internal user, Odoo 14–20.

A plain internal user cannot read ``ir.model`` / ``ir.model.fields`` from
Odoo 17 on, nor ``ir.module.module`` in Odoo 14. The registry is always
there: these helpers list the models the user can read and add what their
defining module says about itself (manifest summary and description, which
is the README when the manifest has none). No business names, no per-module
dictionary.
"""
from __future__ import annotations

import difflib

DESCRIPTION_MAX_CHARS = 4000


def _model_name(model):
    if isinstance(model, str) and model.strip():
        return model.strip()
    name = getattr(model, '_name', None)
    if isinstance(name, str) and name.strip():
        return name.strip()
    raise ValueError('model_module(model) needs a model name or recordset')


def can_read_model(Model):
    """True if the current user may read this model (rights, not records).

    ``has_access`` exists from Odoo 18; ``check_access_rights`` until 19.
    """
    has_access = getattr(Model, 'has_access', None)
    try:
        if callable(has_access):
            return bool(has_access('read'))
        return bool(Model.check_access_rights('read', raise_exception=False))
    except Exception:
        return False


def _summary_row(env, name):
    Model = env[name]
    return {
        'model': name,
        'name': getattr(Model, '_description', None) or name,
        'module': getattr(Model, '_original_module', None) or '',
    }


def _readable_names(env):
    out = []
    for name in env:
        Model = env[name]
        if getattr(Model, '_abstract', False):
            continue
        if can_read_model(Model):
            out.append(name)
    return out


def find_models(env, text, limit=10):
    """Models the user can read whose name or description matches *text*.

    Every word of *text* scores on the technical name and on the model
    description; with no hit, the closest technical names win.
    """
    needle = (text or '').strip().lower()
    if not needle:
        raise ValueError("find_models(text) needs a word, e.g. find_models('invoice')")
    limit = max(1, int(limit or 10))
    words = needle.replace('.', ' ').replace('_', ' ').split()
    names = _readable_names(env)

    scored = []
    for name in names:
        label = (getattr(env[name], '_description', None) or '').lower()
        score = 0
        if name == needle:
            score += 10
        for word in words:
            if word in name:
                score += 2
            if word in label:
                score += 1
        if score:
            scored.append((-score, len(name), name))
    scored.sort()
    picked = [name for _s, _l, name in scored[:limit]]
    if not picked:
        picked = difflib.get_close_matches(needle, names, n=limit, cutoff=0.5)
    return [_summary_row(env, name) for name in picked]


def _module_sheet(env, module, max_chars):
    """Summary and description of an installed module, for internal users.

    Odoo 14 hides ``ir.module.module`` from them and Odoo 19 does not; the
    text is the same one the app store shows. Only these three fields of an
    installed module leave the elevated read, as plain strings.
    """
    if not module or not env.user.has_group('base.group_user'):
        return {}
    rec = env['ir.module.module'].sudo().search(
        [('name', '=', module), ('state', '=', 'installed')], limit=1,
    )
    if not rec:
        return {}
    description = rec.description or ''
    if max_chars and len(description) > max_chars:
        description = description[:max_chars].rstrip() + ' …'
    return {
        'module_name': rec.shortdesc or '',
        'summary': rec.summary or '',
        'description': description,
    }


def model_module(env, model, max_chars=DESCRIPTION_MAX_CHARS):
    """The module that brings *model* and what that module says about itself.

    ``None`` when the user cannot read the model. ``KeyError`` when the model
    is not installed.
    """
    name = _model_name(model)
    if name not in env:
        raise KeyError(name)
    if not can_read_model(env[name]):
        return None
    row = _summary_row(env, name)
    row.update(_module_sheet(env, row['module'], max_chars))
    return row
