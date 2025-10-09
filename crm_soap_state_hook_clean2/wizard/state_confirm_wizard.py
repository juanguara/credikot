# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class CrmSoapStateConfirmWizard(models.TransientModel):
    _name = "crm.soap.state.confirm.wizard"
    _description = "Confirmación de cambio de estado SOAP"

    action_type = fields.Selection(
        selection=[("won", "Won"), ("lost", "Lost")],
        required=True,
        default="won",
    )
    message = fields.Text(readonly=True)
    lead_ids = fields.Many2many("crm.lead", string="Oportunidades", readonly=True)

    def action_confirm(self):
        self.ensure_one()
        leads = self.lead_ids or self.env["crm.lead"].browse(
            self.env.context.get("active_ids", [])
        )
        if not leads:
            return {"type": "ir.actions.act_window_close"}

        if self.action_type == "won":
            return leads.with_context(crm_soap_skip_confirm_won=True).action_set_won()
        else:
            return leads.with_context(crm_soap_skip_confirm_lost=True).action_set_lost()

    def action_cancel(self):
        return {"type": "ir.actions.act_window_close"}
