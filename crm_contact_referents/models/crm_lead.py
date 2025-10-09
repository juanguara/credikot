from odoo import models, fields, _

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    referente_id = fields.Many2one(
        'res.partner.referente',
        string="Referente",
        domain="[('partner_ids', 'in', [partner_id])]"
    )

    referente_ids_rel = fields.Many2many(
        'res.partner.referente',
        string="Referentes del Contacto",
        related='partner_id.referente_ids',
        readonly=False
    )

    def action_buscar_referente_por_telefono(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Buscar/Asociar Referente'),
            'res_model': 'crm.referente.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_lead_id': self.id,
            }
        }

    def action_open_referentes_kanban(self):
        self.ensure_one()
        action = self.env.ref('crm_contact_referents.action_referentes_kanban_for_partner').read()[0]
        action['domain'] = [('partner_ids', 'in', [self.partner_id.id])]
        action.setdefault('context', {})
        if isinstance(action['context'], str):
            action['context'] = {}
        action['context'].update({
            'default_partner_ids': [(4, self.partner_id.id)],
        })
        return action
