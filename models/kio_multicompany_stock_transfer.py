# -*- coding: utf-8 -*-
from odoo import models, fields, api


class KioMulticompanyStockTransfer(models.Model):
    _name = 'kio.multicompany.stock.transfer'
    _description = 'Multi-Company Stock Transfer'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Transfer Reference',
        required=True,
        copy=False,
        readonly=True,
        default='New'
    )
    source_company_id = fields.Many2one(
        comodel_name='res.company',
        string='Source Company',
        required=True,
        tracking=True,
    )
    destination_company_id = fields.Many2one(
        comodel_name='res.company',
        string='Destination Company',
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('done', 'Done'),
            ('cancel', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        required=True,
        copy=False,
        tracking=True,
    )
    picking_ids = fields.One2many(
        comodel_name='stock.picking',
        inverse_name='multicompany_transfer_id',
        string='Related Pickings',
    )
    note = fields.Text(
        string='Notes',
    )
