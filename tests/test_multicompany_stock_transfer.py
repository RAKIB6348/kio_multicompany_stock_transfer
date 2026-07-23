# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare


@tagged('post_install', '-at_install')
class TestMulticompanyStockTransfer(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env['res.company'].create({
            'name': 'Test Company A',
        })
        cls.company_b = cls.env['res.company'].create({
            'name': 'Test Company B',
        })
        cls.company_c = cls.env['res.company'].create({
            'name': 'Test Company C',
        })
        cls.warehouse_a = cls.env['stock.warehouse'].create({
            'name': 'Warehouse A',
            'company_id': cls.company_a.id,
        })
        cls.warehouse_b = cls.env['stock.warehouse'].create({
            'name': 'Warehouse B',
            'company_id': cls.company_b.id,
        })
        cls.warehouse_c = cls.env['stock.warehouse'].create({
            'name': 'Warehouse C',
            'company_id': cls.company_c.id,
        })
        cls.transit_location = cls.env['stock.location'].create({
            'name': 'Shared Transit',
            'usage': 'transit',
            'company_id': False,
        })
        cls.company_location = cls.env['stock.location'].create({
            'name': 'Company A Location',
            'usage': 'internal',
            'company_id': cls.company_a.id,
        })
        cls.product_a = cls.env['product.product'].create({
            'name': 'Test Product A',
            'type': 'product',
            'tracking': 'lot',
            'list_price': 10.0,
        })
        cls.product_b = cls.env['product.product'].create({
            'name': 'Test Product B',
            'type': 'product',
            'tracking': 'lot',
            'list_price': 20.0,
        })
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.uom_dozen = cls.env.ref('uom.product_uom_dozen')
        cls.picking_type_out_a = cls.env['stock.picking.type'].create({
            'name': 'Test Outgoing A',
            'code': 'outgoing',
            'warehouse_id': cls.warehouse_a.id,
            'sequence_code': 'OUTA/TEST',
        })
        cls.picking_type_in_b = cls.env['stock.picking.type'].create({
            'name': 'Test Incoming B',
            'code': 'incoming',
            'warehouse_id': cls.warehouse_b.id,
            'sequence_code': 'INB/TEST',
        })
        cls.picking_type_out_b = cls.env['stock.picking.type'].create({
            'name': 'Test Outgoing B',
            'code': 'outgoing',
            'warehouse_id': cls.warehouse_b.id,
            'sequence_code': 'OUTB/TEST',
        })
        cls.route = cls.env['kio.multicompany.transfer.route'].create({
            'name': 'Test Route A to B',
            'source_company_id': cls.company_a.id,
            'source_warehouse_id': cls.warehouse_a.id,
            'destination_company_id': cls.company_b.id,
            'destination_warehouse_id': cls.warehouse_b.id,
            'transit_location_id': cls.transit_location.id,
            'source_picking_type_id': cls.picking_type_out_a.id,
            'destination_picking_type_id': cls.picking_type_in_b.id,
        })
        cls.user_a = cls.env['res.users'].create({
            'name': 'User A',
            'login': 'test_user_a',
            'company_id': cls.company_a.id,
            'company_ids': [(6, 0, [cls.company_a.id])],
        })
        cls.user_b = cls.env['res.users'].create({
            'name': 'User B',
            'login': 'test_user_b',
            'company_id': cls.company_b.id,
            'company_ids': [(6, 0, [cls.company_b.id])],
        })
        cls.user_multi = cls.env['res.users'].create({
            'name': 'User Multi',
            'login': 'test_user_multi',
            'company_id': cls.company_a.id,
            'company_ids': [(6, 0, [cls.company_a.id, cls.company_b.id])],
        })
        cls.user_unrelated = cls.env['res.users'].create({
            'name': 'User Unrelated',
            'login': 'test_user_unrelated',
            'company_id': cls.company_c.id,
            'company_ids': [(6, 0, [cls.company_c.id])],
        })

    def _create_transfer_with_line(self, qty=100.0):
        transfer = self.env['kio.multicompany.stock.transfer'].with_user(self.env.user).create({
            'route_id': self.route.id,
            'scheduled_date': '2026-01-01 10:00:00',
        })
        self.env['kio.multicompany.stock.transfer.line'].create({
            'transfer_id': transfer.id,
            'product_id': self.product_a.id,
            'product_uom_id': self.uom_unit.id,
            'requested_qty': qty,
        })
        return transfer

    def _set_stock_for_product(self, product, location, qty):
        quant = self.env['stock.quant'].with_company(self.company_a).create({
            'product_id': product.id,
            'location_id': location.id,
            'inventory_quantity': qty,
        })
        quant.action_apply_inventory()

    def test_01_valid_route(self):
        self.assertTrue(self.route.id, 'Route should be created')
        self.assertEqual(self.route.source_company_id, self.company_a)
        self.assertEqual(self.route.destination_company_id, self.company_b)

    def test_02_same_company_rejected(self):
        with self.assertRaises(ValidationError):
            self.env['kio.multicompany.transfer.route'].create({
                'name': 'Invalid Route',
                'source_company_id': self.company_a.id,
                'source_warehouse_id': self.warehouse_a.id,
                'destination_company_id': self.company_a.id,
                'destination_warehouse_id': self.warehouse_a.id,
                'transit_location_id': self.transit_location.id,
                'source_picking_type_id': self.picking_type_out_a.id,
                'destination_picking_type_id': self.picking_type_out_a.id,
            })

    def test_03_warehouse_company_mismatch_rejected(self):
        with self.assertRaises(ValidationError):
            self.env['kio.multicompany.transfer.route'].create({
                'name': 'Invalid Route',
                'source_company_id': self.company_a.id,
                'source_warehouse_id': self.warehouse_b.id,
                'destination_company_id': self.company_b.id,
                'destination_warehouse_id': self.warehouse_b.id,
                'transit_location_id': self.transit_location.id,
                'source_picking_type_id': self.picking_type_out_a.id,
                'destination_picking_type_id': self.picking_type_in_b.id,
            })

    def test_04_company_transit_location_rejected(self):
        company_transit = self.env['stock.location'].create({
            'name': 'Company Transit',
            'usage': 'transit',
            'company_id': self.company_a.id,
        })
        with self.assertRaises(ValidationError):
            self.env['kio.multicompany.transfer.route'].create({
                'name': 'Invalid Route',
                'source_company_id': self.company_a.id,
                'source_warehouse_id': self.warehouse_a.id,
                'destination_company_id': self.company_b.id,
                'destination_warehouse_id': self.warehouse_b.id,
                'transit_location_id': company_transit.id,
                'source_picking_type_id': self.picking_type_out_a.id,
                'destination_picking_type_id': self.picking_type_in_b.id,
            })

    def test_05_transfer_without_lines_rejected(self):
        transfer = self.env['kio.multicompany.stock.transfer'].with_user(self.env.user).create({
            'route_id': self.route.id,
            'scheduled_date': '2026-01-01 10:00:00',
        })
        with self.assertRaises(UserError):
            transfer.action_confirm()

    def test_06_zero_quantity_rejected(self):
        transfer = self.env['kio.multicompany.stock.transfer'].with_user(self.env.user).create({
            'route_id': self.route.id,
            'scheduled_date': '2026-01-01 10:00:00',
        })
        with self.assertRaises(ValidationError):
            self.env['kio.multicompany.stock.transfer.line'].create({
                'transfer_id': transfer.id,
                'product_id': self.product_a.id,
                'product_uom_id': self.uom_unit.id,
                'requested_qty': 0.0,
            })

    def test_07_source_picking_created(self):
        transfer = self._create_transfer_with_line()
        transfer.action_confirm()
        self.assertTrue(transfer.source_picking_ids, 'Source picking should be created')
        self.assertEqual(transfer.source_picking_ids.company_id, self.company_a)

    def test_08_source_picking_locations(self):
        transfer = self._create_transfer_with_line()
        transfer.action_confirm()
        picking = transfer.source_picking_ids[0]
        self.assertEqual(picking.location_id, self.warehouse_a.lot_stock_id)
        self.assertEqual(picking.location_dest_id, self.transit_location)

    def test_09_no_destination_before_dispatch(self):
        transfer = self._create_transfer_with_line()
        transfer.action_confirm()
        self.assertFalse(transfer.destination_picking_ids,
                         'Destination receipt should not be created before dispatch')

    def test_10_dispatch_creates_destination(self):
        self._set_stock_for_product(self.product_a, self.warehouse_a.lot_stock_id, 100.0)
        transfer = self._create_transfer_with_line()
        transfer.action_confirm()
        picking = transfer.source_picking_ids[0]
        picking.action_confirm()
        picking.action_assign()
        picking.move_ids[0].quantity_done = 100.0
        picking.button_validate()
        self.assertTrue(transfer.destination_picking_ids,
                        'Destination receipt should be created after dispatch')

    def test_11_destination_company(self):
        self._set_stock_for_product(self.product_a, self.warehouse_a.lot_stock_id, 100.0)
        transfer = self._create_transfer_with_line()
        transfer.action_confirm()
        picking = transfer.source_picking_ids[0]
        picking.action_confirm()
        picking.action_assign()
        picking.move_ids[0].quantity_done = 100.0
        picking.button_validate()
        dest_picking = transfer.destination_picking_ids[0]
        self.assertEqual(dest_picking.company_id, self.company_b)

    def test_12_receipt_quantity_matches_dispatched(self):
        self._set_stock_for_product(self.product_a, self.warehouse_a.lot_stock_id, 100.0)
        transfer = self._create_transfer_with_line()
        transfer.action_confirm()
        picking = transfer.source_picking_ids[0]
        picking.action_confirm()
        picking.action_assign()
        picking.move_ids[0].quantity_done = 100.0
        picking.button_validate()
        dest_picking = transfer.destination_picking_ids[0]
        self.assertEqual(dest_picking.move_ids[0].product_uom_qty, 100.0)

    def test_13_no_duplicate_destination_receipt(self):
        self._set_stock_for_product(self.product_a, self.warehouse_a.lot_stock_id, 100.0)
        transfer = self._create_transfer_with_line()
        transfer.action_confirm()
        picking = transfer.source_picking_ids[0]
        picking.action_confirm()
        picking.action_assign()
        picking.move_ids[0].quantity_done = 100.0
        picking.button_validate()
        dest_count = len(transfer.destination_picking_ids)
        self.assertEqual(dest_count, 1, 'Should have only one destination receipt')

    def test_14_partial_dispatch_creates_partial_receipt(self):
        self._set_stock_for_product(self.product_a, self.warehouse_a.lot_stock_id, 100.0)
        transfer = self._create_transfer_with_line(100.0)
        transfer.action_confirm()
        picking = transfer.source_picking_ids[0]
        picking.action_confirm()
        picking.action_assign()
        picking.move_ids[0].quantity_done = 60.0
        picking.button_validate()
        self.assertTrue(transfer.destination_picking_ids)
        dest_picking = transfer.destination_picking_ids[0]
        self.assertEqual(dest_picking.move_ids[0].product_uom_qty, 60.0)

    def test_15_backorder_dispatch_creates_another_receipt(self):
        self._set_stock_for_product(self.product_a, self.warehouse_a.lot_stock_id, 100.0)
        transfer = self._create_transfer_with_line(100.0)
        transfer.action_confirm()
        picking = transfer.source_picking_ids[0]
        picking.action_confirm()
        picking.action_assign()
        picking.move_ids[0].quantity_done = 60.0
        picking.button_validate()
        first_dest_count = len(transfer.destination_picking_ids)
        self.assertEqual(first_dest_count, 1)
        backorder = transfer.source_picking_ids.filtered(lambda p: p.state != 'done')
        if backorder:
            bo = backorder[0]
            bo.action_confirm()
            bo.action_assign()
            bo.move_ids[0].quantity_done = 40.0
            bo.button_validate()
            second_dest_count = len(transfer.destination_picking_ids)
            self.assertEqual(second_dest_count, 2)

    def test_16_over_receipt_blocked(self):
        self._set_stock_for_product(self.product_a, self.warehouse_a.lot_stock_id, 100.0)
        transfer = self._create_transfer_with_line(60.0)
        transfer.action_confirm()
        picking = transfer.source_picking_ids[0]
        picking.action_confirm()
        picking.action_assign()
        picking.move_ids[0].quantity_done = 60.0
        picking.button_validate()
        dest_picking = transfer.destination_picking_ids[0]
        dest_picking.move_ids[0].quantity_done = 70.0
        with self.assertRaises(ValidationError):
            dest_picking.button_validate()

    def test_17_partial_destination_receipt(self):
        self._set_stock_for_product(self.product_a, self.warehouse_a.lot_stock_id, 100.0)
        transfer = self._create_transfer_with_line(100.0)
        transfer.action_confirm()
        picking = transfer.source_picking_ids[0]
        picking.action_confirm()
        picking.action_assign()
        picking.move_ids[0].quantity_done = 100.0
        picking.button_validate()
        dest_picking = transfer.destination_picking_ids[0]
        dest_picking.move_ids[0].quantity_done = 50.0
        dest_picking.button_validate()
        self.assertIn(dest_picking.state, ['done', 'assigned'])

    def test_18_transfer_totals(self):
        self._set_stock_for_product(self.product_a, self.warehouse_a.lot_stock_id, 100.0)
        self._set_stock_for_product(self.product_b, self.warehouse_a.lot_stock_id, 50.0)
        transfer = self.env['kio.multicompany.stock.transfer'].with_user(self.env.user).create({
            'route_id': self.route.id,
            'scheduled_date': '2026-01-01 10:00:00',
        })
        self.env['kio.multicompany.stock.transfer.line'].create({
            'transfer_id': transfer.id,
            'product_id': self.product_a.id,
            'product_uom_id': self.uom_unit.id,
            'requested_qty': 100.0,
        })
        self.env['kio.multicompany.stock.transfer.line'].create({
            'transfer_id': transfer.id,
            'product_id': self.product_b.id,
            'product_uom_id': self.uom_unit.id,
            'requested_qty': 50.0,
        })
        self.assertEqual(transfer.requested_quantity, 150.0)
        transfer.action_confirm()
        picking = transfer.source_picking_ids[0]
        picking.action_confirm()
        picking.action_assign()
        for move in picking.move_ids:
            move.quantity_done = move.product_uom_qty
        picking.button_validate()
        self.assertEqual(transfer.dispatched_quantity, 150.0)

    def test_19_transfer_states(self):
        transfer = self._create_transfer_with_line(100.0)
        self.assertEqual(transfer.state, 'draft')
        transfer.action_confirm()
        self.assertEqual(transfer.state, 'confirmed')
        self._set_stock_for_product(self.product_a, self.warehouse_a.lot_stock_id, 100.0)
        transfer = self._create_transfer_with_line(100.0)
        transfer.action_confirm()
        picking = transfer.source_picking_ids[0]
        picking.action_confirm()
        picking.action_assign()
        picking.move_ids[0].quantity_done = 100.0
        picking.button_validate()
        self.assertNotEqual(transfer.state, 'confirmed')

    def test_20_cancellation_before_dispatch(self):
        transfer = self._create_transfer_with_line()
        transfer.action_confirm()
        transfer.action_cancel()
        self.assertEqual(transfer.state, 'cancelled')

    def test_21_cancellation_after_dispatch_blocked(self):
        self._set_stock_for_product(self.product_a, self.warehouse_a.lot_stock_id, 100.0)
        transfer = self._create_transfer_with_line(100.0)
        transfer.action_confirm()
        picking = transfer.source_picking_ids[0]
        picking.action_confirm()
        picking.action_assign()
        picking.move_ids[0].quantity_done = 100.0
        picking.button_validate()
        with self.assertRaises(UserError):
            transfer.action_cancel()

    def test_22_company_users_access(self):
        transfer = self._create_transfer_with_line()
        transfer_user_a = transfer.with_user(self.user_a)
        self.assertTrue(transfer_user_a.read(['name']))
        transfer_multi = transfer.with_user(self.user_multi)
        self.assertTrue(transfer_multi.read(['name']))

    def test_23_unrelated_company_no_access(self):
        transfer = self._create_transfer_with_line()
        transfer_unrelated = transfer.with_user(self.user_unrelated)
        result = transfer_unrelated.read(['name'])
        self.assertFalse(result, 'Unrelated user should not access the record')

    def test_24_no_direct_quant_manipulation(self):
        import os
        import re
        models_dir = os.path.dirname(os.path.abspath(
            __import__('odoo.addons.kio_multicompany_stock_transfer.models', fromlist=['models']).__file__
        ))
        pattern = re.compile(r'\.write\s*\(\s*\[?\s*\{\s*[\'"](?:inventory_)?quantity')
        for fname in os.listdir(models_dir):
            if not fname.endswith('.py') or fname.startswith('__'):
                continue
            fpath = os.path.join(models_dir, fname)
            with open(fpath) as f:
                content = f.read()
            matches = pattern.findall(content)
            self.assertFalse(matches,
                             'Direct stock.quant quantity manipulation found in %s' % fname)

    def test_25_no_raw_sql(self):
        import os
        import re
        models_dir = os.path.dirname(os.path.abspath(
            __import__('odoo.addons.kio_multicompany_stock_transfer.models', fromlist=['models']).__file__
        ))
        sql_pattern = re.compile(r'\.execute\s*\(|\.mogrify\s*\(|\.executemany\s*\(|FROM\s+stock_quant\s+WHERE')
        for fname in os.listdir(models_dir):
            if not fname.endswith('.py') or fname.startswith('__'):
                continue
            fpath = os.path.join(models_dir, fname)
            with open(fpath) as f:
                content = f.read()
            matches = sql_pattern.findall(content)
            self.assertFalse(matches,
                             'Raw SQL or direct quant manipulation found in %s' % fname)
