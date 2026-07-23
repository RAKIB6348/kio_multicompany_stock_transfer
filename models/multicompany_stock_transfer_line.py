# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class MulticompanyStockTransferLine(models.Model):
    _name = 'kio.multicompany.stock.transfer.line'
    _description = 'Multi-Company Stock Transfer Line'
    _order = 'id'

    transfer_id = fields.Many2one(
        comodel_name='kio.multicompany.stock.transfer',
        string='Transfer',
        required=True,
        ondelete='cascade',
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        required=True,
        domain="[('type', '=', 'product')]",
    )
    product_uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string='Unit of Measure',
        required=True,
    )
    requested_qty = fields.Float(
        string='Requested Quantity',
        required=True,
        digits='Product Unit of Measure',
    )
    dispatched_qty = fields.Float(
        string='Dispatched Quantity',
        compute='_compute_dispatched_qty',
        store=True,
        digits='Product Unit of Measure',
    )
    received_qty = fields.Float(
        string='Received Quantity',
        compute='_compute_received_qty',
        store=True,
        digits='Product Unit of Measure',
    )
    remaining_to_dispatch_qty = fields.Float(
        string='Remaining to Dispatch',
        compute='_compute_remaining_quantities',
        digits='Product Unit of Measure',
    )
    remaining_to_receive_qty = fields.Float(
        string='Remaining to Receive',
        compute='_compute_remaining_quantities',
        digits='Product Unit of Measure',
    )
    source_available_qty = fields.Float(
        string='Source Available Quantity',
        compute='_compute_source_available_qty',
        digits='Product Unit of Measure',
    )
    note = fields.Char(
        string='Note',
    )

    @api.depends('transfer_id.source_picking_id.move_ids.product_uom_qty')
    def _compute_dispatched_qty(self):
        for line in self:
            if line.transfer_id.source_picking_id:
                dispatched = sum(
                    line.transfer_id.source_picking_id.move_ids.filtered(
                        lambda m: m.product_id == line.product_id
                    ).mapped('quantity_done')
                )
                line.dispatched_qty = dispatched
            else:
                line.dispatched_qty = 0.0

    @api.depends('transfer_id.destination_picking_id.move_ids.product_uom_qty')
    def _compute_received_qty(self):
        for line in self:
            if line.transfer_id.destination_picking_id:
                received = sum(
                    line.transfer_id.destination_picking_id.move_ids.filtered(
                        lambda m: m.product_id == line.product_id
                    ).mapped('quantity_done')
                )
                line.received_qty = received
            else:
                line.received_qty = 0.0

    @api.depends('requested_qty', 'dispatched_qty', 'received_qty')
    def _compute_remaining_quantities(self):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for line in self:
            line.remaining_to_dispatch_qty = line.requested_qty - line.dispatched_qty
            line.remaining_to_receive_qty = line.dispatched_qty - line.received_qty

    @api.depends('product_id', 'transfer_id.source_warehouse_id')
    def _compute_source_available_qty(self):
        for line in self:
            if line.product_id and line.transfer_id.source_warehouse_id:
                quants = self.env['stock.quant'].search([
                    ('product_id', '=', line.product_id.id),
                    ('location_id', 'child_of', line.transfer_id.source_warehouse_id.lot_stock_id.id),
                ])
                line.source_available_qty = sum(quants.mapped('quantity')) - sum(quants.mapped('reserved_quantity'))
            else:
                line.source_available_qty = 0.0

    @api.constrains('requested_qty')
    def _check_requested_qty(self):
        for line in self:
            if float_compare(line.requested_qty, 0.0, precision_digits=self.env['decimal.precision'].precision_get('Product Unit of Measure')) <= 0:
                raise ValidationError(_('Requested quantity must be greater than zero.'))

    @api.constrains('product_id')
    def _check_product_stock_managed(self):
        for line in self:
            if not line.product_id.stock_tracking:
                raise ValidationError(_('Product must be stock-managed (use tracking by lots or serial numbers).'))

    @api.constrains('product_id', 'product_uom_id')
    def _check_uom_category(self):
        for line in self:
            if line.product_id.uom_id.category_id != line.product_uom_id.category_id:
                raise ValidationError(_('UoM category must match the product UoM category.'))

    @api.constrains('transfer_id', 'product_id', 'product_uom_id')
    def _check_duplicate_product_uom(self):
        for line in self:
            domain = [
                ('transfer_id', '=', line.transfer_id.id),
                ('product_id', '=', line.product_id.id),
                ('product_uom_id', '=', line.product_uom_id.id),
                ('id', '!=', line.id),
            ]
            if self.search_count(domain) > 0:
                raise ValidationError(_('Duplicate Product and UoM combinations are not allowed in one transfer.'))

    @api.constrains('product_id', 'requested_qty', 'transfer_id')
    def _check_no_edit_after_dispatch(self):
        for line in self:
            if line.transfer_id.state not in ('draft',):
                if line._origin.product_id != line.product_id:
                    raise ValidationError(_('Product cannot be changed after dispatch starts.'))
                if float_compare(
                    line._origin.requested_qty,
                    line.requested_qty,
                    precision_digits=self.env['decimal.precision'].precision_get('Product Unit of Measure')
                ) != 0:
                    raise ValidationError(_('Requested quantity cannot be changed after dispatch starts.'))
