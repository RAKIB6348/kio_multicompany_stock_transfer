# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare


class MulticompanyStockTransfer(models.Model):
    _name = 'kio.multicompany.stock.transfer'
    _description = 'Multi-Company Stock Transfer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Transfer Reference',
        required=True,
        copy=False,
        readonly=True,
        default='New',
    )
    route_id = fields.Many2one(
        comodel_name='kio.multicompany.transfer.route',
        string='Transfer Route',
        required=True,
        tracking=True,
    )
    source_company_id = fields.Many2one(
        comodel_name='res.company',
        string='Source Company',
        related='route_id.source_company_id',
        store=True,
        readonly=True,
    )
    destination_company_id = fields.Many2one(
        comodel_name='res.company',
        string='Destination Company',
        related='route_id.destination_company_id',
        store=True,
        readonly=True,
    )
    source_warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse',
        string='Source Warehouse',
        related='route_id.source_warehouse_id',
        store=True,
        readonly=True,
    )
    destination_warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse',
        string='Destination Warehouse',
        related='route_id.destination_warehouse_id',
        store=True,
        readonly=True,
    )
    transit_location_id = fields.Many2one(
        comodel_name='stock.location',
        string='Transit Location',
        related='route_id.transit_location_id',
        store=True,
        readonly=True,
    )
    scheduled_date = fields.Datetime(
        string='Scheduled Date',
        required=True,
        default=fields.Datetime.now,
        tracking=True,
    )
    responsible_id = fields.Many2one(
        comodel_name='res.users',
        string='Responsible',
        default=lambda self: self.env.user,
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('ready', 'Ready'),
            ('partially_dispatched', 'Partially Dispatched'),
            ('in_transit', 'In Transit'),
            ('partially_received', 'Partially Received'),
            ('done', 'Done'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        required=True,
        copy=False,
        tracking=True,
    )
    line_ids = fields.One2many(
        comodel_name='kio.multicompany.stock.transfer.line',
        inverse_name='transfer_id',
        string='Transfer Lines',
    )
    source_picking_id = fields.Many2one(
        comodel_name='stock.picking',
        string='Source Picking',
        readonly=True,
        copy=False,
    )
    destination_picking_id = fields.Many2one(
        comodel_name='stock.picking',
        string='Destination Picking',
        readonly=True,
        copy=False,
    )
    source_picking_ids = fields.One2many(
        comodel_name='stock.picking',
        inverse_name='multicompany_transfer_id',
        string='Source Pickings',
        domain="[('multicompany_transfer_role', '=', 'source')]",
    )
    source_picking_count = fields.Integer(
        string='Source Picking Count',
        compute='_compute_source_picking_count',
    )
    destination_picking_ids = fields.One2many(
        comodel_name='stock.picking',
        inverse_name='source_dispatch_picking_id',
        string='Destination Pickings',
    )
    destination_picking_count = fields.Integer(
        string='Destination Picking Count',
        compute='_compute_destination_picking_count',
    )
    notes = fields.Text(
        string='Notes',
    )
    cancellation_reason = fields.Text(
        string='Cancellation Reason',
    )
    requested_quantity = fields.Float(
        string='Requested Quantity',
        compute='_compute_quantities',
        digits='Product Unit of Measure',
    )
    dispatched_quantity = fields.Float(
        string='Dispatched Quantity',
        compute='_compute_quantities',
        digits='Product Unit of Measure',
    )
    received_quantity = fields.Float(
        string='Received Quantity',
        compute='_compute_quantities',
        digits='Product Unit of Measure',
    )
    remaining_quantity = fields.Float(
        string='Remaining Quantity',
        compute='_compute_quantities',
        digits='Product Unit of Measure',
    )

    @api.depends('source_picking_ids')
    def _compute_source_picking_count(self):
        for transfer in self:
            transfer.source_picking_count = len(transfer.source_picking_ids)

    @api.depends('destination_picking_ids')
    def _compute_destination_picking_count(self):
        for transfer in self:
            transfer.destination_picking_count = len(transfer.destination_picking_ids)

    @api.depends('line_ids.requested_qty', 'line_ids.dispatched_qty', 'line_ids.received_qty')
    def _compute_quantities(self):
        for transfer in self:
            lines = transfer.line_ids
            transfer.requested_quantity = sum(lines.mapped('requested_qty'))
            transfer.dispatched_quantity = sum(lines.mapped('dispatched_qty'))
            transfer.received_quantity = sum(lines.mapped('received_qty'))
            transfer.remaining_quantity = transfer.requested_quantity - transfer.dispatched_quantity

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'kio.multicompany.stock.transfer'
                ) or 'New'
        return super().create(vals_list)

    def _validate_transfer_for_confirmation(self):
        self.ensure_one()
        group = self.env.ref('kio_multicompany_stock_transfer.group_multicompany_transfer_manager', raise_if_not_found=False)
        if group and not self.env.user.has_group('kio_multicompany_stock_transfer.group_multicompany_transfer_manager'):
            raise UserError(_('Only Manager group users can confirm transfers.'))
        if self.state != 'draft':
            raise UserError(_('Only draft transfers can be confirmed.'))
        if not self.route_id:
            raise UserError(_('Transfer route is required.'))
        if self.source_company_id == self.destination_company_id:
            raise UserError(_('Source and destination companies must be different.'))
        if not self.line_ids:
            raise UserError(_('Cannot confirm transfer without lines.'))
        for line in self.line_ids:
            if float_compare(line.requested_qty, 0.0, precision_digits=self.env['decimal.precision'].precision_get('Product Unit of Measure')) <= 0:
                raise UserError(_('All line quantities must be greater than zero.'))
            if not line.product_id:
                raise UserError(_('All lines must have a product.'))
            if not line.product_uom_id:
                raise UserError(_('All lines must have a unit of measure.'))
        if self.source_picking_id:
            raise UserError(_('Source picking already exists.'))

    def _get_source_picking_type(self):
        picking_type = self.env['stock.picking.type'].search([
            ('warehouse_id', '=', self.source_warehouse_id.id),
            ('code', '=', 'outgoing'),
        ], limit=1)
        if not picking_type:
            picking_type = self.env['stock.picking.type'].search([
                ('warehouse_id', '=', self.source_warehouse_id.id),
            ], limit=1)
        return picking_type

    def _create_source_picking(self):
        self.ensure_one()
        picking_type = self._get_source_picking_type()
        picking_vals = {
            'picking_type_id': picking_type.id if picking_type else False,
            'location_id': self.source_warehouse_id.lot_stock_id.id,
            'location_dest_id': self.transit_location_id.id,
            'scheduled_date': self.scheduled_date,
            'origin': self.name,
            'company_id': self.source_company_id.id,
            'multicompany_transfer_id': self.id,
            'multicompany_transfer_role': 'source',
        }
        picking = self.env['stock.picking'].with_company(self.source_company_id).create(picking_vals)
        for line in self.line_ids:
            move_vals = {
                'name': '%s: %s' % (self.name, line.product_id.name),
                'product_id': line.product_id.id,
                'product_uom_qty': line.requested_qty,
                'product_uom': line.product_uom_id.id,
                'picking_id': picking.id,
                'location_id': self.source_warehouse_id.lot_stock_id.id,
                'location_dest_id': self.transit_location_id.id,
                'company_id': self.source_company_id.id,
            }
            self.env['stock.move'].with_company(self.source_company_id).create(move_vals)
        return picking

    def action_confirm(self):
        for transfer in self:
            transfer._validate_transfer_for_confirmation()
            source_picking = transfer._create_source_picking()
            transfer.source_picking_id = source_picking
            source_picking.with_company(transfer.source_company_id).action_confirm()
            source_picking.with_company(transfer.source_company_id).action_assign()
            transfer.write({'state': 'confirmed'})
        return True

    def action_ready(self):
        for transfer in self:
            if transfer.state != 'confirmed':
                raise UserError(_('Only confirmed transfers can be set to ready.'))
            transfer.write({'state': 'ready'})
        return True

    def action_cancel(self):
        for transfer in self:
            if transfer.state in ('done', 'cancelled'):
                raise UserError(_('Done or already cancelled transfers cannot be cancelled.'))
            transfer.write({'state': 'cancelled'})
        return True

    def action_draft(self):
        for transfer in self:
            if transfer.state != 'cancelled':
                raise UserError(_('Only cancelled transfers can be reset to draft.'))
            transfer.write({
                'state': 'draft',
                'cancellation_reason': False,
            })
        return True

    def action_view_source_pickings(self):
        self.ensure_one()
        pickings = self.source_picking_ids
        if not pickings:
            return False
        if len(pickings) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Source Picking'),
                'res_model': 'stock.picking',
                'res_id': pickings.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {
            'type': 'ir.actions.act_window',
            'name': _('Source Pickings'),
            'res_model': 'stock.picking',
            'domain': [('id', 'in', pickings.ids)],
            'view_mode': 'tree,form',
            'target': 'current',
        }

    def action_view_destination_pickings(self):
        self.ensure_one()
        pickings = self.destination_picking_ids
        if not pickings:
            return False
        if len(pickings) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Destination Picking'),
                'res_model': 'stock.picking',
                'res_id': pickings.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {
            'type': 'ir.actions.act_window',
            'name': _('Destination Pickings'),
            'res_model': 'stock.picking',
            'domain': [('id', 'in', pickings.ids)],
            'view_mode': 'tree,form',
            'target': 'current',
        }
