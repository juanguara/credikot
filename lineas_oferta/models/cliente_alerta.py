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
    rec_importe_rechazado = fields.Monetary(
        string="Importe Rechazado",
        currency_field='currency_id',
        help="Importe rechazado informado por el sistema legacy."
    )
    rec_observaciones = fields.Char(string="Observaciones")
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        default=lambda self: self.env.company.currency_id.id,
        required=True
    )

    _sql_constraints = [
        (
            "uniq_alerta_lead",
            "unique(lead_id, tipo, fecha)",
            "Ya existe una alerta con el mismo tipo y fecha para esta oportunidad.",
        ),
    ]
