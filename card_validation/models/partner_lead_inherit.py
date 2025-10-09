# -*- coding: utf-8 -*-
from odoo import fields, models

class ResPartner(models.Model):
    _inherit = "res.partner"

    cktc_card_validation_ids = fields.One2many(
        comodel_name="ckt.card.validation",
        inverse_name="partner_id",
        string="Validaciones de Tarjeta",
    )

class CrmLead(models.Model):
    _inherit = "crm.lead"

    cktc_card_validation_ids = fields.One2many(
        comodel_name="ckt.card.validation",
        inverse_name="lead_id",
        string="Validaciones de Tarjeta",
    )

