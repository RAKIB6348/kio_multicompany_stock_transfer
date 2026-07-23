# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.tools import float_compare


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    multicompany_transfer_id = fields.Many2one(
        comodel_name='kio.multicompany.stock.transfer',
        string='Multi-Company Transfer',
        ondelete='set null',
        copy=False,
        index=True,
    )
    multicompany_transfer_role = fields.Selection(
        selection=[
            ('source', 'Source'),
            ('destination', 'Destination'),
        ],
        string='Transfer Role',
        copy=False,
    )
    source_dispatch_picking_id = fields.Many2one(
        comodel_name='stock.picking',
        string='Source Dispatch Picking',
        ondelete='set null',
        copy=False,
        index=True,
    )
    destination_receipt_ids = fields.One2many(
        comodel_name='stock.picking',
        inverse_name='source_dispatch_picking_id',
        string='Destination Receipts',
    )

    def _action_done(self):
        res = super()._action_done()
        self._create_destination_receipts_from_source()
        return res

    def _create_destination_receipts_from_source(self):
        source_pickings = self.filtered(
            lambda p: p.multicompany_transfer_role == 'source'
            and p.multicompany_transfer_id
            and p.state == 'done'
        )
        for picking in source_pickings:
            picking._create_destination_receipt()

    def _create_destination_receipt(self):
        self.ensure_one()
        if self.multicompany_transfer_role != 'source':
            return False
        if not self.multicompany_transfer_id:
            return False
        transfer = self.multicompany_transfer_id
        existing = self.env['stock.picking'].search([
            ('source_dispatch_picking_id', '=', self.id),
            ('multicompany_transfer_role', '=', 'destination'),
        ], limit=1)
        if existing:
            return False
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        moves_to_receive = self.env['stock.move']
        for move in self.move_ids:
            qty_done = move.quantity_done
            if float_compare(qty_done, 0.0, precision_digits=precision) <= 0:
                continue
            moves_to_receive += move
        if not moves_to_receive:
            return False
        picking_type = transfer.route_id.destination_picking_type_id
        source_location = transfer.transit_location_id
        dest_location = transfer.destination_warehouse_id.lot_stock_id
        scheduled_date = self.date_done or self.scheduled_date
        picking_vals = {
            'picking_type_id': picking_type.id if picking_type else False,
            'location_id': source_location.id,
            'location_dest_id': dest_location.id,
            'scheduled_date': scheduled_date,
            'origin': '%s - %s' % (transfer.name, self.name),
            'company_id': transfer.destination_company_id.id,
            'multicompany_transfer_id': transfer.id,
            'multicompany_transfer_role': 'destination',
            'source_dispatch_picking_id': self.id,
        }
        dest_picking = self.env['stock.picking'].with_company(transfer.destination_company_id).create(picking_vals)
        for move in moves_to_receive:
            move_vals = {
                'name': '%s: %s' % (transfer.name, move.product_id.name),
                'product_id': move.product_id.id,
                'product_uom_qty': move.quantity_done,
                'product_uom': move.product_uom.id,
                'picking_id': dest_picking.id,
                'location_id': source_location.id,
                'location_dest_id': dest_location.id,
                'company_id': transfer.destination_company_id.id,
            }
            self.env['stock.move'].with_company(transfer.destination_company_id).create(move_vals)
        dest_picking.with_company(transfer.destination_company_id).action_confirm()
        return dest_picking
