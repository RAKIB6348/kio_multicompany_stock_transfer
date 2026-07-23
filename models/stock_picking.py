# -*- coding: utf-8 -*-
from odoo import models, fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    multicompany_transfer_id = fields.Many2one(
        comodel_name='kio.multicompany.stock.transfer',
        string='Multi-Company Transfer',
        ondelete='set null',
    )
