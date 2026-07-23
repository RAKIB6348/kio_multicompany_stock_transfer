# -*- coding: utf-8 -*-
from odoo import models, fields


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
