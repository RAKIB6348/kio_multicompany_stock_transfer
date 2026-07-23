# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MulticompanyTransferRoute(models.Model):
    _name = 'kio.multicompany.transfer.route'
    _description = 'Multi-Company Transfer Route'
    _order = 'sequence, id'

    name = fields.Char(
        string='Route Name',
        required=True,
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
    )
    source_company_id = fields.Many2one(
        comodel_name='res.company',
        string='Source Company',
        required=True,
    )
    source_warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse',
        string='Source Warehouse',
        required=True,
        domain="[('company_id', '=', source_company_id)]",
        check_company=True,
    )
    destination_company_id = fields.Many2one(
        comodel_name='res.company',
        string='Destination Company',
        required=True,
    )
    destination_warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse',
        string='Destination Warehouse',
        required=True,
        domain="[('company_id', '=', destination_company_id)]",
        check_company=True,
    )
    transit_location_id = fields.Many2one(
        comodel_name='stock.location',
        string='Transit Location',
        required=True,
        domain="[('usage', '=', 'transit'), ('company_id', '=', False)]",
    )
    source_picking_type_id = fields.Many2one(
        comodel_name='stock.picking.type',
        string='Source Picking Type',
        required=True,
        domain="[('warehouse_id', '=', source_warehouse_id)]",
        check_company=True,
    )
    destination_picking_type_id = fields.Many2one(
        comodel_name='stock.picking.type',
        string='Destination Picking Type',
        required=True,
        domain="[('warehouse_id', '=', destination_warehouse_id)]",
        check_company=True,
    )
    note = fields.Text(
        string='Notes',
    )

    @api.constrains('source_company_id', 'destination_company_id')
    def _check_companies_different(self):
        for route in self:
            if route.source_company_id == route.destination_company_id:
                raise ValidationError(_(
                    'Source and destination companies must be different.'
                ))

    @api.constrains('source_warehouse_id', 'destination_warehouse_id')
    def _check_warehouses_different(self):
        for route in self:
            if route.source_warehouse_id == route.destination_warehouse_id:
                raise ValidationError(_(
                    'Source and destination warehouses must be different.'
                ))

    @api.constrains('source_warehouse_id', 'source_company_id')
    def _check_source_warehouse_company(self):
        for route in self:
            if route.source_warehouse_id.company_id != route.source_company_id:
                raise ValidationError(_(
                    'Source warehouse must belong to source company.'
                ))

    @api.constrains('destination_warehouse_id', 'destination_company_id')
    def _check_destination_warehouse_company(self):
        for route in self:
            if route.destination_warehouse_id.company_id != route.destination_company_id:
                raise ValidationError(_(
                    'Destination warehouse must belong to destination company.'
                ))

    @api.constrains('transit_location_id')
    def _check_transit_location(self):
        for route in self:
            if route.transit_location_id.usage != 'transit':
                raise ValidationError(_(
                    'Transit location usage must be "transit".'
                ))
            if route.transit_location_id.company_id:
                raise ValidationError(_(
                    'Transit location must be shared (company must be empty).'
                ))

    @api.constrains('source_picking_type_id', 'source_company_id')
    def _check_source_picking_type_company(self):
        for route in self:
            if route.source_picking_type_id.warehouse_id.company_id != route.source_company_id:
                raise ValidationError(_(
                    'Source picking type must belong to source company.'
                ))

    @api.constrains('destination_picking_type_id', 'destination_company_id')
    def _check_destination_picking_type_company(self):
        for route in self:
            if route.destination_picking_type_id.warehouse_id.company_id != route.destination_company_id:
                raise ValidationError(_(
                    'Destination picking type must belong to destination company.'
                ))

    @api.constrains('source_warehouse_id', 'destination_warehouse_id', 'active')
    def _check_unique_active_route(self):
        for route in self:
            if not route.active:
                continue
            domain = [
                ('id', '!=', route.id),
                ('active', '=', True),
                ('source_warehouse_id', '=', route.source_warehouse_id.id),
                ('destination_warehouse_id', '=', route.destination_warehouse_id.id),
            ]
            if self.search_count(domain) > 0:
                raise ValidationError(_(
                    'An active route already exists for this warehouse pair.'
                ))
