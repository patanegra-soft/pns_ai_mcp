# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Domain index deterministic match over discovery contexts (spike metrics).

Routing now lives as ``ai.context`` rows (``context_type='discovery'``) seeded
from ``contexts/discovery/*.json``. These host tests can't spin an Odoo env, so
they compose entries directly from the discovery JSON files — mirroring
``ai.context.get_discovery_entries`` (entry ``code`` = discovery ``target``).
"""
from __future__ import annotations

import json
import re
import statistics
import time
from pathlib import Path

from _load_addon import load_module
from _tenant_needles import names_tenant

di = load_module('domain_index', 'utils', 'domain_index.py')
_ROOT = Path(__file__).resolve().parents[1]

DISCOVERY_DIR = (
    Path(__file__).resolve().parents[1] / 'common' / 'ai' / 'contexts' / 'discovery'
)
# Sibling modules (multi-root workspace) — cross-module discovery rows.
ACL_DISCOVERY_DIR = (
    Path(__file__).resolve().parents[2]
    / 'pns_acl_manager' / 'common' / 'ai' / 'contexts' / 'discovery'
)
GEO_DISCOVERY_DIR = (
    Path(__file__).resolve().parents[2]
    / 'pns_geo' / 'common' / 'ai' / 'contexts' / 'discovery'
)

# Codes that are ``core`` in the shipped library — never valid discovery targets.
_CORE_CODES = {'system_prompt'}

# Labelled set: expected primary code or None (noise — no business domain).
FIXTURE_CASES = [
    # payroll
    ('¿Cuánto cobró de nómina Ana en marzo?', 'hr_payroll'),
    ('lista de payslips del mes', 'hr_payroll'),
    ('muéstrame el bruto y neto de la última nómina', 'hr_payroll'),
    ('IRPF retenido en nóminas 2025', 'hr_payroll'),
    ('payroll by employee this year', 'hr_payroll'),
    ('recibo de salario de Juan', 'hr_payroll'),
    ('quién gana más dinero', 'hr_payroll'),
    ('los que menos cobran', 'hr_payroll'),
    ('sueldos del equipo', 'hr_payroll'),
    # geo / maps
    ('pon en un mapa los clientes de Madrid', 'geo'),
    ('geocode estas direcciones', 'geo'),
    ('ruta en mapa de las visitas de hoy', 'geo'),
    ('muéstrame las coordenadas latitud longitud', 'geo'),
    ('leaflet pins de partners', 'geo'),
    ('tour geográfico de almacenes', 'geo'),
    # invoices / partners
    ('lista de facturas de cliente ACME', 'invoice_concepts'),
    ('facturas impagadas del trimestre', 'invoice_concepts'),
    ('mejores clientes por facturación', 'partners'),
    ('líneas del albarán WH/OUT/00012', 'business_documents'),
    ('detalle del presupuesto SO42', 'business_documents'),
    ('sales order lines for SO42', 'business_documents'),
    ('what is on delivery picking WH/OUT/1', 'business_documents'),
    ('créame un presupuesto para Galvatec', 'business_documents'),
    ('ponle un 10% de descuento', 'business_documents'),
    ('create a quotation for ACME', 'business_documents'),
    ('apply a global discount', 'business_documents'),
    # HR contracts
    ('contratos laborales activos', 'hr_contracts'),
    # ACL (needs sibling pns_acl_manager discovery row on disk)
    ('explica la ley de rol único ACL', 'acl_security'),
    # noise — presentation / chitchat (must not pick heavy domains as first)
    ('hola, qué hora es', None),
    ('ordena la tabla con pijama', None),
    ('explica el system prompt', None),
    ('quiénes están logueados ahora', None),
    ('exporta a excel el listado', None),
    ('pásame el informe en excel', None),
    ('pásame el informe en word', None),
    ('quiero el informe en word con gráficos', None),
    ('reformula en prosa lacónica', None),
]

# Domains that must not win on pure noise fixtures.
_NOISE_FORBIDDEN_FIRST = {
    'hr_payroll', 'geo', 'invoice_concepts',
    'partners', 'business_documents',
    'acl_security', 'trial_balance',
}


def _read_discovery_file(path: Path) -> dict:
    data = json.loads(path.read_text(encoding='utf-8'))
    triggers = [str(t).strip() for t in (data.get('triggers') or []) if str(t).strip()]
    soft = [str(s).strip() for s in (data.get('soft_depends') or []) if str(s).strip()]
    code = (data.get('code') or path.stem).strip()
    # Locale: explicit metadata → code suffix (foo_fr_FR). Mirrors
    # ai.context._infer_explicit_locale + _compute_base_code.
    loc = (data.get('locale') or data.get('locale_code') or '').strip().replace('-', '_')
    if not loc:
        m = re.match(r'^.+_([a-z]{2})_([A-Z]{2})$', code)
        if m:
            loc = '%s_%s' % (m.group(1), m.group(2))
    base = code[: -(len(loc) + 1)] if loc and code.endswith('_' + loc) else code
    return {
        'target': (data.get('target') or '').strip(),
        'code': code,
        'base_code': base,
        'locale': loc,
        'tipo': (data.get('tipo') or '').lower(),
        'triggers': triggers,
        'priority': int(data.get('priority') or 0),
        'soft_depends': soft,
        'source_module': (data.get('source_module') or '').strip(),
        'target_kind': (data.get('target_kind') or 'domain').strip() or 'domain',
    }


def _discovery_files():
    files = list(DISCOVERY_DIR.glob('*.json'))
    if ACL_DISCOVERY_DIR.is_dir():
        files += list(ACL_DISCOVERY_DIR.glob('*.json'))
    if GEO_DISCOVERY_DIR.is_dir():
        files += list(GEO_DISCOVERY_DIR.glob('*.json'))
    return files


def _entries(user_locale=None):
    """Mirror ai.context.get_discovery_entries.

    One entry per ``base_code``. Spoken locale variants (shipped: ``es_ES``)
    union their triggers with the generic English set; other locales (or
    ``None``) hear only the generic row. Emit ``{code=target, ...}``.
    """
    by_base = {}
    for path in _discovery_files():
        row = _read_discovery_file(path)
        by_base.setdefault(row['base_code'], {})[row['locale'] or 'generic'] = row
    collapsed = []
    for base in sorted(by_base):
        variants = by_base[base]
        generic = variants.get('generic')
        spoken = variants.get(user_locale) if user_locale else None
        row = spoken or generic or next(iter(variants.values()))
        target = row['target']
        if not target:
            continue
        if spoken and generic:
            triggers = di.merge_trigger_lists(
                generic['triggers'], spoken['triggers'],
            )
        else:
            triggers = row['triggers']
        collapsed.append({
            'target': target,
            'target_kind': row.get('target_kind') or 'domain',
            'triggers': triggers,
            'priority': row['priority'],
            'soft_depends': row['soft_depends'],
            'source_module': row['source_module'],
        })
    return di.compose_discovery_entries(
        collapsed,
        core_codes=_CORE_CODES,
        active_server_codes=set(),
    )


def _spoken_entries():
    """Index as composed for an ``es_ES`` user (generic ∪ spoken)."""
    return _entries('es_ES')


def test_discovery_files_load_all_nucleus_targets():
    entries = _entries()
    codes = {e['code'] for e in entries}
    for needed in (
        'hr_payroll', 'invoice_concepts',
        'partners', 'business_documents',
        'account',
        'cost_accounting', 'filters',
        'geography', 'trial_balance', 'hr_contracts',
        'accounting_imbalances', 'fetch_url_recipe',
    ):
        assert needed in codes, 'missing %s' % needed
    if GEO_DISCOVERY_DIR.is_dir():
        assert 'geo' in codes
    else:
        assert 'geo' not in codes
    assert len(entries) >= 11


def test_prefixed_discovery_retired():
    stems = {p.stem for p in DISCOVERY_DIR.glob('*.json')}
    assert 'discovery_business_documents' in stems
    assert 'discovery_partners' in stems
    leftover = sorted(s for s in stems if 'domain_knowledge' in s)
    assert leftover == [], leftover


def test_all_discovery_files_are_tipo_discovery():
    """Every discovery file declares tipo=discovery and a non-core target."""
    for path in _discovery_files():
        row = _read_discovery_file(path)
        assert row['tipo'] == 'discovery', '%s tipo=%s' % (path.name, row['tipo'])
        assert row['target'], '%s missing target' % path.name
        assert row['target'] not in _CORE_CODES, (
            '%s targets core %s' % (path.name, row['target'])
        )
        # Naming convention: code namespaced to avoid clashing with target.
        assert row['code'] != row['target'], (
            '%s code must differ from target' % path.name
        )
        assert 'domain_knowledge' not in row['code'], path.name
        assert not row['target'].startswith('domain_knowledge_'), path.name
        for dep in row['soft_depends']:
            assert not dep.startswith('domain_knowledge_'), path.name


def test_engine_discovery_has_no_geo_target():
    """Maps routing lives in pns_geo, not in the engine tree."""
    for path in DISCOVERY_DIR.glob('discovery_*.json'):
        row = _read_discovery_file(path)
        assert row['target'] != 'geo', path.name
        assert path.stem not in ('discovery_geo', 'discovery_geo_es_ES'), path.name


def test_cross_module_acl_target():
    """ACL ships a discovery row (cross-module authoring is allowed)."""
    if not ACL_DISCOVERY_DIR.is_dir():
        return
    entries = {e['code']: e for e in _entries()}
    assert 'acl_security' in entries
    assert entries['acl_security']['source_module'] == 'pns_acl_manager'


def test_cross_module_geo_target():
    """Maps discovery is owned by pns_geo when the sibling tree is present."""
    if not GEO_DISCOVERY_DIR.is_dir():
        return
    entries = {e['code']: e for e in _entries()}
    assert 'geo' in entries
    assert entries['geo']['source_module'] == 'pns_geo'


def test_guard_no_target_is_core():
    for e in _entries():
        assert e['code'] not in _CORE_CODES


def test_generic_geo_is_english_only():
    """Neutral discover stays English/technical: no spoken ES or leftover FR."""
    if not GEO_DISCOVERY_DIR.is_dir():
        return
    gen = {e['code']: e for e in _entries()}
    assert 'geo' in gen
    folded = [t.lower() for t in gen['geo']['triggers']]
    assert 'mapa' not in folded
    assert 'carte' not in folded
    assert 'geocode' in folded
    assert 'map' in folded


def test_es_ES_geo_has_mapa_and_keeps_technical():
    """es_ES unions spoken Spanish with the generic English set."""
    if not GEO_DISCOVERY_DIR.is_dir():
        return
    es = {e['code']: e for e in _spoken_entries()}
    assert 'geo' in es
    folded = [t.lower() for t in es['geo']['triggers']]
    assert 'mapa' in folded
    assert 'geocode' in folded
    assert 'carte' not in folded


def test_es_ES_union_matches_spoken_and_technical_geo():
    if not GEO_DISCOVERY_DIR.is_dir():
        return
    entries = _spoken_entries()
    spoken = di.match_domains('pon en un mapa', entries, max_packs=1)
    tech = di.match_domains('geocode estas direcciones', entries, max_packs=1)
    assert 'geo' in spoken['codes']
    assert 'geo' in tech['codes']


def test_geo_single_entry_across_locale_variants():
    """base_code collapse: geo appears once; fr_FR falls back to generic."""
    if not GEO_DISCOVERY_DIR.is_dir():
        return
    for loc in (None, 'fr_FR', 'es_ES'):
        codes = [e['code'] for e in _entries(loc)]
        assert codes.count('geo') == 1, 'loc=%s' % loc
    fr = {e['code']: e for e in _entries('fr_FR')}
    folded = [t.lower() for t in fr['geo']['triggers']]
    assert 'carte' not in folded
    assert 'mapa' not in folded
    assert 'geocode' in folded


def test_soft_depends_payroll():
    entries = _spoken_entries()
    result = di.match_domains('nóminas de marzo con neto', entries, max_packs=1)
    assert 'hr_payroll' in result['codes']
    assert 'hr_payroll_accounting_present' in result['codes']


def test_soft_depends_invoice_partners():
    entries = _spoken_entries()
    result = di.match_domains('facturas de clientes morosos', entries, max_packs=1)
    assert 'invoice_concepts' in result['codes']
    assert 'partners' in result['codes']
    assert 'business_documents' in result['codes']
    assert result['codes'][0] == 'invoice_concepts'


def test_business_documents_wins_on_concrete_picking_or_quote():
    entries = _spoken_entries()
    picking = di.match_domains('líneas del albarán WH/OUT/00012', entries)
    quote = di.match_domains('detalle del presupuesto SO42', entries)
    assert picking['codes'][0] == 'business_documents'
    assert quote['codes'][0] == 'business_documents'
    assert 'partners' in picking['codes']
    invoice_list = di.match_domains(
        'lista de facturas de cliente ACME', entries, max_packs=1,
    )
    assert invoice_list['codes'][0] == 'invoice_concepts'
    assert 'business_documents' in invoice_list['codes']


def test_pay_ranking_opens_payroll():
    """Spoken pay ranking is payroll. A punch question is not."""
    entries = _spoken_entries()
    for text in (
        'quién gana más dinero',
        'los que menos cobran',
        'sueldos del equipo',
    ):
        result = di.match_domains(text, entries)
        assert result['codes'][:1] == ['hr_payroll'], (text, result['codes'])
    punches = di.match_domains('fichajes de hoy', entries)
    assert 'hr_payroll' not in (punches['codes'] or [])


def test_business_documents_wins_on_create_or_discount():
    entries = _spoken_entries()
    create = di.match_domains('créame un presupuesto para Galvatec', entries)
    discount = di.match_domains('ponle un 10% de descuento', entries)
    assert create['codes'][0] == 'business_documents'
    assert discount['codes'][0] == 'business_documents'


def test_match_latency_under_50ms():
    entries = _spoken_entries()
    times = []
    for text, _exp in FIXTURE_CASES:
        t0 = time.perf_counter()
        di.match_domains(text, entries)
        times.append((time.perf_counter() - t0) * 1000.0)
    p50 = statistics.median(times)
    p95 = sorted(times)[max(0, int(len(times) * 0.95) - 1)]
    assert p50 < 50.0, 'p50=%.3f ms' % p50
    assert p95 < 50.0, 'p95=%.3f ms' % p95


def test_hit_rate_at_least_80_percent():
    entries = _spoken_entries()
    cases = list(FIXTURE_CASES)
    if not ACL_DISCOVERY_DIR.is_dir():
        cases = [(t, e) for t, e in cases if e != 'acl_security']
    if not GEO_DISCOVERY_DIR.is_dir():
        cases = [(t, e) for t, e in cases if e != 'geo']
    ok = 0
    failures = []
    for text, expected in cases:
        result = di.match_domains(text, entries)
        codes = result['codes']
        primary = codes[0] if codes else None
        matched_primaries = [m['code'] for m in (result['matches'] or [])[:2]]
        if expected is None:
            first = matched_primaries[0] if matched_primaries else None
            hit = first not in _NOISE_FORBIDDEN_FIRST
            if not hit:
                failures.append((text, expected, first, result))
            else:
                ok += 1
        else:
            hit = expected in matched_primaries or expected in codes
            if hit:
                ok += 1
            else:
                failures.append((text, expected, primary, result))
    rate = ok / float(len(cases))
    assert rate >= 0.80, 'hit_rate=%.2f failures=%s' % (rate, failures)


def test_inject_header_lists_codes():
    header = di.format_inject_header(['geo', 'partners'], 1.5)
    assert 'DOMAIN_PACKS' in header
    assert 'geo' in header
    assert 'partners' in header


def test_index_catalog_lists_codes():
    entries = [
        {'code': 'geo', 'triggers': ['mapa', 'map']},
        {'code': 'hr_payroll', 'triggers': ['nómina', 'payroll']},
    ]
    cat = di.format_index_catalog(entries)
    assert 'DOMAIN_INDEX catalog' in cat
    assert 'geo' in cat
    assert 'hr_payroll' in cat
    assert 'mapa' in cat


def test_indexed_codes_includes_soft_depends():
    entries = _entries()
    codes = di.indexed_codes_from_entries(entries)
    assert 'hr_payroll' in codes
    assert 'hr_payroll_accounting_present' in codes
    assert ('geo' in codes) == GEO_DISCOVERY_DIR.is_dir()
    assert 'partners' in codes
    assert 'business_documents' in codes


def test_dates_pack_is_not_discovery_indexed():
    """Always-on ORM date hygiene: no discovery row (stays in cached_content)."""
    xml = (
        Path(__file__).resolve().parents[1]
        / 'common' / 'ai' / 'contexts' / 'domain' / 'dates.xml'
    )
    assert xml.is_file(), 'missing dates seed'
    text = xml.read_text(encoding='utf-8')
    assert '<code>dates</code>' in text
    assert 'year_from_date_field' in text
    generic = di.indexed_codes_from_entries(_entries())
    spoken = di.indexed_codes_from_entries(_spoken_entries())
    assert 'dates' not in generic
    assert 'dates' not in spoken
    for path in _discovery_files():
        row = _read_discovery_file(path)
        assert row['target'] != 'dates', (
            '%s must not index dates' % path.name
        )


def test_icp_flag_enabled_defaults():
    assert di.icp_flag_enabled(None, default=True) is True
    assert di.icp_flag_enabled('', default=True) is True
    assert di.icp_flag_enabled('False', default=True) is False
    assert di.icp_flag_enabled('0', default=True) is False
    assert di.icp_flag_enabled('True', default=False) is True


def test_format_inject_header():
    header = di.format_inject_header(['geo', 'hr_payroll'], 1.5)
    assert 'DOMAIN_PACKS' in header
    assert 'geo' in header
    assert 'hr_payroll' in header
    assert di.format_inject_header([], 0.0) == ''
    carried = di.format_inject_header(
        ['invoice_concepts', 'custom_acme_crm_team'],
        1.5,
        carried=['custom_acme_crm_team'],
    )
    assert 'previous_turn=custom_acme_crm_team' in carried


def test_union_drops_previous_when_sentence_names_another_topic():
    """A sentence that hits other packs does not keep the previous topic."""
    out = di.union_domain_codes(
        matched=['invoice_concepts', 'partners', 'business_documents'],
        carried=['custom_acme_crm_team'],
    )
    assert out['mode'] == 'injected'
    assert out['matched'][0] == 'invoice_concepts'
    assert out['codes'] == [
        'invoice_concepts', 'partners', 'business_documents',
    ]
    assert out['carried'] == []


def test_union_keeps_previous_when_sentence_overlaps():
    """One shared pack means the same topic: the rest of the previous turn stays."""
    out = di.union_domain_codes(
        matched=['partners'],
        carried=['partners', 'geo'],
    )
    assert out['mode'] == 'union'
    assert out['codes'] == ['partners', 'geo']
    assert out['carried'] == ['geo']


def test_a_held_pack_survives_a_sentence_that_names_another_topic():
    """«Add a tab with business-area profit» names the data, not the open page."""
    merged = di.union_domain_codes(
        matched=['custom_acme_crm_team'], carried=['invoice_concepts'],
    )
    assert merged['carried'] == []
    codes = di.hold_domain_codes(merged['codes'], ['page_tab'])
    assert codes == ['custom_acme_crm_team', 'page_tab']
    assert 'page_tab' not in merged['matched']
    assert di.hold_domain_codes(['page_tab', 'geo'], ['page_tab']) == [
        'page_tab', 'geo',
    ]
    assert di.hold_domain_codes(['geo'], None) == ['geo']
    assert di.hold_domain_codes([], ['page_tab']) == ['page_tab']


def test_every_discovery_path_keeps_the_held_packs():
    src = (
        _ROOT / 'common' / 'utils' / 'engine_discovery.py'
    ).read_text(encoding='utf-8')
    unions = src.count('merged = union_domain_codes(')
    assert unions == 3
    assert src.count(
        "codes = hold_domain_codes(\n"
        "            merged.get('codes') or [], "
        "getattr(self, '_held_domain_codes', None),\n"
    ) == unions
    engine = (
        _ROOT / 'common' / 'utils' / 'agent_engine.py'
    ).read_text(encoding='utf-8')
    assert 'held_domain_codes=None' in engine
    assert 'self._held_domain_codes = parse_domain_codes(held_domain_codes)' in engine


def test_skill_domain_context_codes_from_index():
    """Only codes that the live index can inject; no copied catalog."""
    indexed = ['invoice_concepts', 'geo', 'partners']
    assert di.skill_domain_context_codes(
        ['invoice_concepts', 'system_prompt', 'geo'],
        indexed,
    ) == ['invoice_concepts', 'geo']
    assert di.skill_domain_context_codes(['system_prompt'], indexed) == []
    assert di.skill_domain_context_codes([], indexed) == []
    assert di.skill_domain_context_codes(
        ['geo'], set(indexed),
    ) == ['geo']


def test_union_skill_context_plus_prior():
    merged = di.union_domain_codes(
        matched=di.skill_domain_context_codes(
            ['invoice_concepts'], ['invoice_concepts', 'geo'],
        ),
        carried=['custom_acme_crm_team'],
        keep_disjoint=True,
    )
    assert merged['mode'] == 'union'
    assert merged['matched'] == ['invoice_concepts']
    assert merged['carried'] == ['custom_acme_crm_team']
    ages = di.age_domain_codes(
        merged['codes'], merged['matched'],
        prior_ages={'custom_acme_crm_team': 2},
    )
    assert ages['invoice_concepts'] == 1
    assert ages['custom_acme_crm_team'] == 3


def test_union_sticky_only_and_injected_only():
    sticky = di.union_domain_codes(matched=[], carried=['geo'])
    assert sticky['mode'] == 'sticky'
    assert sticky['codes'] == ['geo']
    injected = di.union_domain_codes(matched=['partners'], carried=[])
    assert injected['mode'] == 'injected'
    assert injected['codes'] == ['partners']
    none = di.union_domain_codes([], [])
    assert none['mode'] == 'none'
    assert none['codes'] == []


def test_parse_domain_codes():
    assert di.parse_domain_codes('["geo","partners"]') == ['geo', 'partners']
    assert di.parse_domain_codes('geo, partners') == ['geo', 'partners']
    assert di.parse_domain_codes(['geo', '', 'partners']) == ['geo', 'partners']
    assert di.parse_domain_codes('') == []
    assert di.parse_domain_codes(None) == []
    assert di.parse_domain_codes('{"geo": 2, "partners": 1}') == ['geo', 'partners']
    assert di.parse_domain_codes({'geo': 2}) == ['geo']


def test_age_and_log_line_have_no_duplicate_carried():
    ages = di.age_domain_codes(
        codes=['invoice_concepts', 'partners', 'custom_acme_crm_team'],
        matched=['invoice_concepts', 'partners'],
        prior_ages={'custom_acme_crm_team': 1},
    )
    assert ages['invoice_concepts'] == 1
    assert ages['custom_acme_crm_team'] == 2
    line = di.format_codes_with_age(ages, [
        'invoice_concepts', 'partners', 'custom_acme_crm_team',
    ])
    assert line == (
        'invoice_concepts (1), partners (1), custom_acme_crm_team (2)'
    )
    assert line.count('custom_acme_crm_team') == 1


def test_union_log_contract_drops_other_topic():
    """ai.log prompt_data: another topic does not list previous_turn=."""
    merged = di.union_domain_codes(
        matched=['invoice_concepts', 'partners', 'business_documents'],
        carried=['custom_acme_crm_team'],
    )
    prompt_data = {
        'codes': merged['codes'],
        'matched': merged['matched'],
        'carried': merged['carried'],
        'mode': merged['mode'],
    }
    assert prompt_data['mode'] == 'injected'
    assert 'custom_acme_crm_team' not in prompt_data['codes']
    assert prompt_data['carried'] == []
    header = di.format_inject_header(
        prompt_data['codes'], 0.98, carried=prompt_data['carried'],
    )
    assert 'previous_turn=' not in header


def test_system_prompt_mentions_previous_turn_packs():
    xml = (
        Path(__file__).resolve().parents[1]
        / 'common' / 'ai' / 'contexts' / 'core' / 'system_prompt.xml'
    ).read_text(encoding='utf-8')
    assert 'DOMAIN PACKS FROM THE PREVIOUS TURN' in xml
    assert 'previous_turn=' in xml


def test_detection_row_code_stable():
    assert di.detection_row_code('my-svc') == 'discovery_api_my_svc'
    assert di.detection_row_code('my-svc', 'es_ES') == 'discovery_api_my_svc_es_ES'
    assert di.detection_row_code('').startswith('discovery_api_')


def test_product_ships_no_api_discovery_for_tenant_services():
    """Factory discovery names no tenant APIs; naming helper stays generic."""
    codes = []
    for path in DISCOVERY_DIR.glob('discovery_api_*.json'):
        row = _read_discovery_file(path)
        codes.append(row['code'])
        assert not names_tenant(str(row.get('target') or ''))
    assert not names_tenant(' '.join(codes))
    assert di.detection_row_code('ext-api') == 'discovery_api_ext_api'
    assert di.detection_row_code('ext-api', 'es_ES') == (
        'discovery_api_ext_api_es_ES'
    )
    assert not names_tenant(' '.join(e['code'] for e in _entries()))


def test_compose_skips_core_and_inactive_server():
    rows = [
        {'target': 'system_prompt', 'target_kind': 'domain', 'triggers': ['x']},
        {'target': 'geo', 'target_kind': 'domain', 'triggers': ['mapa']},
        {'target': 'ghost-api', 'target_kind': 'api_server', 'triggers': ['ghost']},
        {'target': 'live-api', 'target_kind': 'api_server', 'triggers': ['live']},
    ]
    entries = di.compose_discovery_entries(
        rows,
        core_codes={'system_prompt'},
        active_server_codes={'live-api'},
    )
    by_code = {e['code']: e for e in entries}
    assert 'system_prompt' not in by_code
    assert 'ghost-api' not in by_code
    assert by_code['geo']['target_kind'] == 'domain'
    assert by_code['live-api']['target_kind'] == 'api_server'


def test_compose_seen_targets_are_kind_scoped():
    """Same code as domain pack and as server can coexist."""
    rows = [
        {'target': 'shared', 'target_kind': 'domain', 'triggers': ['pack']},
        {'target': 'shared', 'target_kind': 'api_server', 'triggers': ['svc']},
    ]
    entries = di.compose_discovery_entries(
        rows, core_codes=set(), active_server_codes={'shared'},
    )
    assert len(entries) == 2
    kinds = {e['target_kind'] for e in entries}
    assert kinds == {'domain', 'api_server'}


def test_indexed_codes_skips_api_server():
    entries = [
        {'code': 'geo', 'target_kind': 'domain', 'soft_depends': ['extra']},
        {'code': 'live-api', 'target_kind': 'api_server', 'soft_depends': []},
    ]
    codes = di.indexed_codes_from_entries(entries)
    assert 'geo' in codes
    assert 'extra' in codes
    assert 'live-api' not in codes


def test_index_catalog_skips_api_server():
    entries = [
        {'code': 'geo', 'target_kind': 'domain', 'triggers': ['mapa']},
        {'code': 'live-api', 'target_kind': 'api_server', 'triggers': ['svc']},
    ]
    cat = di.format_index_catalog(entries)
    assert 'geo' in cat
    assert 'mapa' in cat
    assert 'live-api' not in cat


def test_domain_and_service_hits_coexist():
    entries = [
        {
            'code': 'geo',
            'target_kind': 'domain',
            'triggers': ['mapa'],
            'priority': 10,
            'soft_depends': [],
        },
        {
            'code': 'ext-svc',
            'target_kind': 'api_server',
            'triggers': ['dominios'],
            'priority': 50,
            'soft_depends': [],
        },
    ]
    domain = di.filter_entries_by_kind(entries, di.TARGET_KIND_DOMAIN)
    service = di.filter_entries_by_kind(entries, di.TARGET_KIND_API_SERVER)
    domain_res = di.match_domains('pon un mapa y lista dominios', domain)
    service_res = di.match_domains(
        'pon un mapa y lista dominios', service, max_packs=4,
    )
    assert 'geo' in domain_res['codes']
    assert 'ext-svc' in service_res['codes']
    hint = di.format_service_detect_hint(service_res['matches'])
    assert 'EXTERNAL_SERVICE' in hint
    assert 'ext-svc' in hint
    assert 'api_call' in hint
    assert di.format_service_detect_hint([]) == ''


def test_identity_detection_triggers_from_code_and_name():
    tokens = di.identity_detection_triggers('my-svc', 'My Service Desk')
    folded = {di.normalize_text(t) for t in tokens}
    assert 'my-svc' in folded
    assert 'my' in folded
    assert 'svc' in folded
    assert 'service' in folded
    assert 'desk' in folded
    assert 'api' not in folded


def test_merge_trigger_lists_dedupes_accents():
    merged = di.merge_trigger_lists(['Café', 'dominios'], ['cafe', 'DNS'])
    folded = [di.normalize_text(t) for t in merged]
    assert folded.count('cafe') == 1
    assert 'dominios' in folded
    assert 'dns' in folded


def test_build_detection_triggers_prompt_is_json_only():
    system, user = di.build_detection_triggers_prompt(
        locale='es_ES',
        code='my-svc',
        name='My Service',
        usage_guide='List records with list_items.',
        already=['my-svc', 'Service'],
    )
    assert 'JSON' in system
    assert 'triggers' in system
    assert 'my-svc' in user
    assert 'List records' in user
    assert 'ReAct' not in system
    assert 'payroll' in system
    assert 'salary' in system
