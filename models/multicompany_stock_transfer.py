# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
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
    notes = fields.Text(
        string='Notes',
    )
    cancellation_reason = fields.Text(
        string='Cancellation Reason',
    )
    source_picking_count = fields.Integer(
        string='Source Picking Count',
        compute='_compute_picking_counts',
    )
    destination_picking_count = fields.Integer(
        string='Destination Picking Count',
        compute='_compute_picking_counts',
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

    @api.depends('source_picking_id', 'destination_picking_id')
    def _compute_picking_counts(self):
        for transfer in self:
            transfer.source_picking_count = 1 if transfer.source_picking_id else 0
            transfer.destination_picking_count = 1 if transfer.destination_picking_id else 0

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

    def action_confirm(self):
        for transfer in self:
            if transfer.state != 'draft':
                raise ValidationError(_('Only draft transfers can be confirmed.'))
            if not transfer.line_ids:
                raise ValidationError(_('Cannot confirm transfer without lines.'))
            transfer.write({'state': 'confirmed'})
        return True

    def action_ready(self):
        for transfer in self:
            if transfer.state != 'confirmed':
                raise ValidationError(_('Only confirmed transfers can be set to ready.'))
            transfer.write({'state': 'ready'})
        return True

    def action_cancel(self):
        for transfer in self:
            if transfer.state in ('done', 'cancelled'):
                raise ValidationError(_('Done or already cancelled transfers cannot be cancelled.'))
            transfer.write({'state': 'cancelled'})
        return True

    def action_draft(self):
        for transfer in self:
            if transfer.state != 'cancelled':
                raise ValidationError(_('Only cancelled transfers can be reset to draft.'))
            transfer.write({
                'state': 'draft',
                'cancellation_reason': False,
            })
        return True

    def action_view_source_picking(self):
        self.ensure_one()
        if not self.source_picking_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': _('Source Picking'),
            'res_model': 'stock.picking',
            'res_id': self.source_picking_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_destination_picking(self):
        self.ensure_one()
        if not self.destination_picking_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': _('Destination Picking'),
            'res_model': 'stock.picking',
            'res_id': self.destination_picking_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
