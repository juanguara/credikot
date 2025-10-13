from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import phonenumbers

def _to_e164_argentina(raw):
    if not raw:
        return False
    raw = (raw or '').strip()
    try:
        num = phonenumbers.parse(raw, "AR")
        if not phonenumbers.is_valid_number(num):
            return False
        e164 = phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)
        if not e164.startswith("+54"):
            return False
        return e164
    except Exception:
        return False

class ResPartnerReferente(models.Model):
    _name = "res.partner.referente"
    _description = "Referentes de Contactos"
    _rec_name = "name"

    name = fields.Char("Nombre y Apellido", required=True)
    relation = fields.Selection([
        ('padre', 'Padre'), ('madre', 'Madre'), ('hermano', 'Hermano'),
        ('amigo', 'Amigo'), ('compañero', 'Compañero'), ('otro', 'Otro'),
    ], string="Relación", required=True)
    phone = fields.Char("Teléfono (E.164 +54)", required=True, index=True)
    observations = fields.Text("Observaciones")

    partner_ids = fields.Many2many(
        'res.partner',
        'res_partner_referente_rel',
        'referente_id',
        'partner_id',
        string="Contactos vinculados"
    )
    partner_count = fields.Integer(compute="_compute_partner_count", store=False)

    _sql_constraints = [
        ('uniq_phone', 'unique (phone)', 'Ya existe un referente con ese teléfono.'),
    ]

    @api.depends('partner_ids')
    def _compute_partner_count(self):
        for r in self:
            r.partner_count = len(r.partner_ids)

    @api.constrains('partner_ids')
    def _check_partner_limit(self):
        for r in self:
            if len(r.partner_ids) > 5:
                raise ValidationError(_("Un referente no puede estar asociado a más de 5 contactos."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            phone_in = vals.get('phone')
            e164 = _to_e164_argentina(phone_in)
            if not e164:
                raise ValidationError(_("El teléfono debe ser válido en Argentina y estar en formato E.164 (+54...)."))
            vals['phone'] = e164
        return super().create(vals_list)

    def write(self, vals):
        if 'phone' in vals:
            e164 = _to_e164_argentina(vals.get('phone'))
            if not e164:
                raise ValidationError(_("El teléfono debe ser válido en Argentina y estar en formato E.164 (+54...)."))
            vals['phone'] = e164
        return super().write(vals)
