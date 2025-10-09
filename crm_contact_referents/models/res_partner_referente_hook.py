from odoo import models, api

class ResPartnerReferenteHook(models.Model):
    _inherit = 'res.partner.referente'

    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        # Si la creación vino desde un formulario de res.partner, asociar automáticamente
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')
        if active_model == 'res.partner' and isinstance(active_id, int):
            for rec in recs.sudo():
                if 'partner_ids' in rec._fields and not rec.partner_ids:
                    rec.partner_ids = [(4, active_id)]
        return recs
