from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    referente_ids = fields.Many2many(
        'res.partner.referente',
        'res_partner_referente_rel',
        'partner_id',
        'referente_id',
        string="Referentes"
    )
