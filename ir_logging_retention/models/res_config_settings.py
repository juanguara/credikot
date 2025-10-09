# -*- coding: utf-8 -*-
from odoo import fields, models

PARAM_KEY = "credikot.ir_logging_retention_days"

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ir_logging_retention_days = fields.Integer(
        string="Retención de ir.logging (días)",
        config_parameter=PARAM_KEY,
        default=30,
        help="Cantidad de días a conservar en ir.logging. 0 deshabilita el purge."
    )
