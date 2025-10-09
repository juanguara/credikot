from odoo import models, fields, _
from odoo.exceptions import ValidationError

class CrmReferenteWizard(models.TransientModel):
    _name = 'crm.referente.wizard'
    _description = 'Buscar/Crear Referente por Teléfono (E.164 AR +54)'

    partner_id = fields.Many2one('res.partner', required=True, string="Contacto")
    lead_id = fields.Many2one('crm.lead', required=True, string="Oportunidad")

    phone = fields.Char("Teléfono (E.164 +54)", required=True)
    name = fields.Char("Nombre y Apellido", required=True)
    relation = fields.Selection([
        ('padre', 'Padre'), ('madre', 'Madre'), ('hermano', 'Hermano'),
        ('amigo', 'Amigo'), ('compañero', 'Compañero'), ('otro', 'Otro'),
    ], string="Relación", required=True)
    observations = fields.Text("Observaciones")

    def action_confirm(self):
        self.ensure_one()
        Referente = self.env['res.partner.referente']
        ref = Referente.search([('phone', '=', self.phone)], limit=1)
        if not ref:
            ref = Referente.create({
                'phone': self.phone,
                'name': self.name,
                'relation': self.relation,
                'observations': self.observations or False,
            })
        if self.partner_id.id not in ref.partner_ids.ids:
            if len(ref.partner_ids) >= 5:
                raise ValidationError(_("Este referente ya está asociado al máximo de 5 contactos."))
            ref.partner_ids = [(4, self.partner_id.id)]
        self.lead_id.referente_id = ref.id
        self.lead_id.message_post(
            body=_("Se vinculó el referente <b>%s</b> (tel. %s) al contacto <b>%s</b>.") %
                 (ref.name, ref.phone or '-', self.partner_id.display_name)
        )
        return {'type': 'ir.actions.act_window_close'}
