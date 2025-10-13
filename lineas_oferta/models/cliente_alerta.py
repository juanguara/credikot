# -*- coding: utf-8 -*-
from odoo import fields, models


class ClienteAlerta(models.Model):
    _name = "cliente.alerta"
    _description = "Alertas de Cliente"
    _order = "fecha desc, id desc"

    lead_id = fields.Many2one(
        "crm.lead",
        required=True,
        ondelete="cascade",
        index=True,
        string="Oportunidad",
    )
    vat = fields.Char(string="CUIT/CUIL", required=True, index=True)
    tipo = fields.Char(string="Tipo de Alerta", required=True)
    fecha = fields.Date(string="Fecha", required=True)

    _sql_constraints = [
        (
            "uniq_alerta_lead",
            "unique(lead_id, tipo, fecha)",
            "Ya existe una alerta con el mismo tipo y fecha para esta oportunidad.",
        ),
    ]
