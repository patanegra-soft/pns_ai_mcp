# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Tests: prose linkify + structural gate (no verb lexicon)."""
from __future__ import annotations

import json
import unittest

from _load_addon import engine_source, load_module

linkify_mod = load_module('pns_ai_mcp_record_linkify', 'utils', 'record_linkify.py')
gate_mod = load_module('pns_ai_mcp_record_delivery_gate', 'utils', 'record_delivery_gate.py')
render_mod = load_module('pns_ai_mcp_relaxaicode_render', 'utils', 'relaxaicode_render.py')

linkify_prose = linkify_mod.linkify_prose
drop_unverified_record_links = linkify_mod.drop_unverified_record_links
seal_record_links = linkify_mod.seal_record_links
should_force_turn_payload = gate_mod.should_force_turn_payload
bubble_with_delivered = gate_mod.bubble_with_delivered
first_tabular_rows = gate_mod.first_tabular_rows
rows_from_safe_plan_steps = gate_mod.rows_from_safe_plan_steps
previous_result_envelope_from_safe_plan = gate_mod.previous_result_envelope_from_safe_plan
get_safe_plan_steps = gate_mod.get_safe_plan_steps
parse_safe_plan_step_body = gate_mod.parse_safe_plan_step_body
row_label_for_record = render_mod.row_label_for_record
render_result_html = render_mod.render_result_html


class TestAllTablesForNextTurn(unittest.TestCase):
    def _two_groups(self):
        return {
            'summary': 'Dos grupos',
            'tables': [
                {'title': 'Más de 3.000', 'data': [
                    {'id': 1, 'Cliente': 'A', 'Rentabilidad': 5000.0},
                    {'Cliente': 'Total', 'Rentabilidad': 5000.0, '_tfoot': True},
                ]},
                {'title': 'Resto', 'data': [
                    {'id': 2, 'Cliente': 'B', 'Rentabilidad': 100.0},
                ]},
            ],
        }

    def test_rows_of_every_table_come_back_as_the_same_tables(self):
        rows = gate_mod.all_tabular_rows(self._two_groups())
        self.assertEqual(len(rows), 3)
        envelope = gate_mod.previous_result_envelope(
            json.loads(json.dumps(rows)),
        )
        self.assertEqual(
            [t['title'] for t in envelope['tables']], ['Más de 3.000', 'Resto'],
        )
        self.assertEqual(len(envelope['tables'][0]['data']), 2)
        self.assertTrue(envelope['tables'][0]['data'][1]['_tfoot'])
        self.assertNotIn(gate_mod.TABLE_KEY, envelope['tables'][1]['data'][0])
        self.assertEqual(len(envelope['data']), 3)

    def test_one_table_stays_plain_rows(self):
        payload = {'data': [{'id': 1, 'name': 'A'}]}
        rows = gate_mod.all_tabular_rows(payload)
        self.assertEqual(rows, first_tabular_rows(payload))
        self.assertEqual(
            gate_mod.previous_result_envelope(rows), {'data': rows},
        )


class TestRowLabelForRecord(unittest.TestCase):
    def test_prefers_display_name(self):
        self.assertEqual(
            row_label_for_record({
                'id': 1, 'display_name': 'Acme', 'name': 'Other',
            }),
            'Acme',
        )

    def test_number_column_when_no_name(self):
        self.assertEqual(
            row_label_for_record({
                'id': 10951,
                'number': 'FactC/2025/0796',
                'base': 18500.0,
            }),
            'FactC/2025/0796',
        )

    def test_no_domain_literals_required(self):
        self.assertEqual(
            row_label_for_record({
                'id': 3, 'Usuario': 'Ana', 'Login': 'ana@x.com',
            }),
            'Ana',
        )


class TestLinkifyProse(unittest.TestCase):
    def test_multi_model_same_code(self):
        text = (
            'Partner Acme Corp, product Desk, invoice FactC/2025/0796 '
            'and event Team sync.'
        )
        records = [
            {'model': 'res.partner', 'id': 10, 'name': 'Acme Corp'},
            {'model': 'product.product', 'id': 20, 'name': 'Desk'},
            {'model': 'account.move', 'id': 10951, 'name': 'FactC/2025/0796'},
            {'model': 'calendar.event', 'id': 5, 'name': 'Team sync'},
        ]
        out = linkify_prose(text, records)
        self.assertIn('[Acme Corp](/web#id=10&model=res.partner&view_type=form)', out)
        self.assertIn('[Desk](/web#id=20&model=product.product&view_type=form)', out)
        self.assertIn(
            '[FactC/2025/0796](/web#id=10951&model=account.move&view_type=form)',
            out,
        )
        self.assertIn(
            '[Team sync](/web#id=5&model=calendar.event&view_type=form)', out,
        )

    def test_no_invented_ids_and_opt_out(self):
        text = 'Hello Acme Corp'
        self.assertEqual(linkify_prose(text, []), text)
        self.assertEqual(
            linkify_prose(
                text,
                [{'model': 'res.partner', 'id': 1, 'name': 'Acme Corp'}],
                links_off=True,
            ),
            text,
        )

    def test_does_not_double_link(self):
        text = '[Acme Corp](/web#id=10&model=res.partner&view_type=form)'
        out = linkify_prose(
            text, [{'model': 'res.partner', 'id': 10, 'name': 'Acme Corp'}],
        )
        self.assertEqual(out.count('/web#id=10'), 1)


class TestDropUnverifiedRecordLinks(unittest.TestCase):
    RECORDS = [{'model': 'res.partner', 'id': 10, 'name': 'Acme Corp'}]

    def test_invented_markdown_becomes_the_label(self):
        text = 'See [Acme Corp](/web#id=999&model=res.partner&view_type=form).'
        out = drop_unverified_record_links(text, self.RECORDS)
        self.assertEqual(out, 'See Acme Corp.')
        self.assertNotIn('/web#id=999', out)

    def test_tool_id_stays(self):
        text = 'See [Acme Corp](/web#id=10&model=res.partner&view_type=form).'
        out = drop_unverified_record_links(text, self.RECORDS)
        self.assertIn('/web#id=10', out)

    def test_no_records_drops_every_prose_link(self):
        text = 'See [X](/web#id=1&model=res.partner&view_type=form).'
        self.assertEqual(drop_unverified_record_links(text, []), 'See X.')

    def test_namelink_from_the_table_is_kept(self):
        html = (
            '<a href="/web#id=10&amp;model=res.partner&amp;view_type=form" '
            'class="o_ai_namelink">Acme</a>'
        )
        self.assertEqual(drop_unverified_record_links(html, self.RECORDS), html)
        self.assertEqual(drop_unverified_record_links(html, []), html)

    def test_invented_html_anchor_becomes_the_label(self):
        html = '<a href="/web#id=999&model=res.partner">Acme</a>'
        self.assertEqual(
            drop_unverified_record_links(html, self.RECORDS), 'Acme',
        )

    def test_seal_rewrites_the_label_to_the_tool_id(self):
        text = 'Acme Corp is [here](/web#id=999&model=res.partner).'
        out = seal_record_links(text, self.RECORDS)
        self.assertNotIn('/web#id=999', out)
        self.assertIn('/web#id=10', out)
        self.assertIn('Acme Corp', out)

    def test_the_delivery_gate_seals_every_close(self):
        from pathlib import Path
        src = (
            Path(__file__).resolve().parents[1]
            / 'common' / 'utils' / 'engine_direct_delivery.py'
        ).read_text(encoding='utf-8')
        gate = src.split('def _tool_loop_delivery_gate', 1)[1].split(
            '\n    def _tool_loop_render_forced', 1,
        )[0]
        self.assertIn('seal_record_links', gate)
        self.assertNotIn('linkify_prose(', gate)


class TestDeliveryGate(unittest.TestCase):
    def test_1a_forces_when_payload_and_prose_only(self):
        self.assertTrue(should_force_turn_payload(
            'Here is the invoice.',
            last_tabulable_payload={'data': [{'id': 1, 'name': 'X'}]},
            table_already_delivered=False,
        ))
        self.assertFalse(should_force_turn_payload(
            '<div class="o_ai_table_block">x</div>',
            last_tabulable_payload={'data': [{'id': 1}]},
            table_already_delivered=False,
        ))
        self.assertFalse(should_force_turn_payload(
            'prose',
            last_tabulable_payload={'data': [{'id': 1}]},
            table_already_delivered=True,
        ))

    def test_1a_skips_when_final_is_substantial(self):
        # The AI already narrated (inspect + substantial prose): do not re-inject the grid.
        long_prose = (
            'Para el contable: el cobro de facturas pendientes concentra '
            'el riesgo de liquidez este ejercicio. Tres deudores acumulan '
            'la mayor parte del saldo abierto y conviene priorizar llamadas '
            'y planes de cobro antes que pelearse con tickets de desayuno. '
            'Los importes y conteos salen del dataset de este mismo turno.'
        )
        self.assertFalse(should_force_turn_payload(
            long_prose,
            last_tabulable_payload={'data': [{'id': 1, 'name': 'X'}]},
            table_already_delivered=False,
        ))

    def test_first_tabular_rows_without_data_key(self):
        rows = [{'id': 1, 'name': 'A'}]
        self.assertEqual(first_tabular_rows(rows), rows)
        self.assertEqual(first_tabular_rows({'items': rows}), rows)
        self.assertEqual(
            first_tabular_rows({'by_units': rows, 'summary': 'x'}), rows,
        )

    def test_forced_render_single_row_namelink(self):
        html = render_result_html({
            'data': [{
                '__model': 'account.move',
                'id': 10951,
                'number': 'FactC/2025/0796',
                'base': 18500.0,
            }],
        })
        self.assertIn('o_ai_namelink', html)
        self.assertIn('/web#id=10951', html)
        self.assertIn('FactC/2025/0796', html)
        self.assertNotIn('fa-external-link', html)


class TestRowsFromSafePlanSteps(unittest.TestCase):
    def test_parses_body_json_lists_and_singles(self):
        steps = [
            {
                'op': 'api_call',
                'server': 'ext',
                'tool': 'ListThings',
                'success': True,
                'body': json.dumps({
                    'data': [{'id': 1, 'name': 'A'}, {'id': 2, 'name': 'B'}],
                }),
            },
            {
                'op': 'api_call',
                'server': 'ext',
                'tool': 'GetThing',
                'success': True,
                'body': json.dumps({'data': {'id': 3, 'name': 'C'}}),
            },
        ]
        rows = rows_from_safe_plan_steps(steps)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['name'], 'A')

    def test_concatenates_multiple_list_bodies(self):
        steps = [
            {
                'op': 'fetch_url',
                'success': True,
                'body': json.dumps({'data': [{'id': 1}]}),
            },
            {
                'op': 'api_call',
                'success': True,
                'body': json.dumps({'items': [{'id': 2}, {'id': 3}]}),
            },
        ]
        rows = rows_from_safe_plan_steps(steps)
        self.assertEqual([r['id'] for r in rows], [1, 2, 3])


class TestSafePlanEnvelope(unittest.TestCase):
    def test_envelope_keeps_steps_and_data(self):
        steps = [
            {
                'op': 'api_call',
                'tool': 'post__info',
                'success': True,
                'body': json.dumps({'data': {'result': {'domain': 'x.test'}}}),
            },
            {
                'op': 'api_call',
                'tool': 'post__status',
                'success': False,
                'error': 'HTTP 500',
                'body': '',
            },
        ]
        env = previous_result_envelope_from_safe_plan(steps)
        self.assertIn('safe_plan_steps', env)
        self.assertEqual(len(env['safe_plan_steps']), 2)
        self.assertTrue(get_safe_plan_steps(env))
        self.assertEqual(get_safe_plan_steps(env)[1]['error'], 'HTTP 500')
        # Flattened data may be present; must not be mistaken for steps alone.
        self.assertEqual(
            get_safe_plan_steps({'data': [{'domain': 'x.test'}]}),
            [],
        )

    def test_parse_step_body_json_string(self):
        step = {
            'op': 'api_call',
            'body': json.dumps({'data': {'result': [1, 2]}}),
        }
        body = parse_safe_plan_step_body(step)
        self.assertEqual(body['data']['result'], [1, 2])


class TestBubbleKeepsWhatWasDelivered(unittest.TestCase):
    """A closing replace cannot wipe the rows the user is about to tap."""

    TABLE = (
        '<div class="o_ai_table_block"><table '
        'class="o_ai_data_table"><tr><td>ACEROS ACME\u00d1A SUR, SL'
        '</td></tr></table></div>'
    )

    def test_a_closing_line_of_prose_keeps_the_table_above_it(self):
        out = bubble_with_delivered(
            self.TABLE, '\u00bfCu\u00e1l de esos tres es?',
        )
        self.assertTrue(out.startswith(self.TABLE))
        self.assertIn('\u00bfCu\u00e1l de esos tres es?', out)

    def test_nothing_painted_leaves_the_close_alone(self):
        self.assertEqual(bubble_with_delivered('', 'Listo.'), 'Listo.')

    def test_a_close_that_already_carries_the_table_is_not_doubled(self):
        out = bubble_with_delivered(self.TABLE, self.TABLE + '\n\nListo.')
        self.assertEqual(out.count('o_ai_table_block'), 1)

    def test_an_empty_close_leaves_the_table_alone(self):
        self.assertEqual(bubble_with_delivered(self.TABLE, ''), self.TABLE)


class TestEngineUsesTheDeliveredBubble(unittest.TestCase):
    """Wiring: the engine remembers what it painted and closes with it."""

    def test_the_engine_keeps_the_painted_table_on_every_closing_replace(self):
        src = engine_source()
        self.assertIn('turn.delivered_html = turn.direct_formatted', src)
        self.assertIn('bubble_with_delivered(turn.delivered_html, html)', src)
        self.assertEqual(
            src.count('_tool_loop_keep_delivered(turn, '), 3,
        )


if __name__ == '__main__':
    unittest.main()
