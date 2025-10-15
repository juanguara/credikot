from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class CrmTelefono(models.Model):
    _name = "crm.telefono"
    _description = "Teléfono CRM"
    _order = "celprincipal desc, id"

    lead_id = fields.Many2one(
        "crm.lead",
        string="Oportunidad",
        ondelete="cascade",
        index=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Contacto",
        ondelete="cascade",
        index=True,
    )
    telcelddn = fields.Char(
        string="Característica",
        required=True,
        size=4,
        help="Código de área de hasta 4 dígitos.",
    )
    telcelnro = fields.Char(
        string="Número Local",
        required=True,
        size=8,
        help="Número local de hasta 8 dígitos.",
    )
    celprincipal = fields.Boolean(
        string="Principal",
        default=False,
        help="Marca este teléfono como principal.",
    )
    celverificado = fields.Boolean(
        string="Verificado",
        default=False,
        help="Indica si el teléfono fue verificado.",
    )
    display_name = fields.Char(
        string="Teléfono",
        compute="_compute_display_name",
        store=True,
    )

    _sql_constraints = [
        (
            "crm_telefono_unique_components",
            "unique(lead_id, partner_id, telcelddn, telcelnro)",
            "Ya existe un teléfono con la misma característica y número para este registro.",
        ),
    ]

    @api.depends("telcelddn", "telcelnro")
    def _compute_display_name(self):
        for record in self:
            ddn = record.telcelddn or ""
            number = record.telcelnro or ""
            record.display_name = f"{ddn}-{number}" if ddn and number else ddn or number or _("Teléfono")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._postprocess_principal()
        return records

    def write(self, vals):
        principal_changed = "celprincipal" in vals
        res = super().write(vals)
        if principal_changed:
            self._postprocess_principal()
        return res

    def unlink(self):
        principals = self.filtered("celprincipal")
        if principals:
            raise UserError(_("No se puede eliminar un teléfono marcado como principal."))
        return super().unlink()

    def _postprocess_principal(self):
        for record in self.filtered("celprincipal"):
            record._reset_other_principal()

    def _reset_other_principal(self):
        self.ensure_one()
        domain = [("id", "!=", self.id), ("celprincipal", "=", True)]
        if self.lead_id:
            self.search(domain + [("lead_id", "=", self.lead_id.id)]).write({"celprincipal": False})
        if self.partner_id:
            self.search(domain + [("partner_id", "=", self.partner_id.id)]).write({"celprincipal": False})

    @api.constrains("lead_id", "partner_id")
    def _check_related_records(self):
        for record in self:
            if not record.lead_id and not record.partner_id:
                raise ValidationError(
                    _("El teléfono debe estar vinculado al menos a una oportunidad o a un contacto.")
                )

    @api.constrains("telcelddn", "telcelnro")
    def _check_phone_components(self):
        for record in self:
            if record.telcelddn:
                if not record.telcelddn.isdigit() or len(record.telcelddn) > 4:
                    raise ValidationError(_("La característica debe contener hasta 4 dígitos numéricos."))
            if record.telcelnro:
                if not record.telcelnro.isdigit() or len(record.telcelnro) > 8:
                    raise ValidationError(_("El número local debe contener hasta 8 dígitos numéricos."))

    @api.constrains("celprincipal", "lead_id", "partner_id")
    def _check_unique_principal(self):
        for record in self.filtered("celprincipal"):
            if record.lead_id:
                duplicates = self.search_count(
                    [
                        ("id", "!=", record.id),
                        ("lead_id", "=", record.lead_id.id),
                        ("celprincipal", "=", True),
                    ]
                )
                if duplicates:
                    raise ValidationError(_("Ya existe un teléfono principal para esta oportunidad."))
            if record.partner_id:
                duplicates = self.search_count(
                    [
                        ("id", "!=", record.id),
                        ("partner_id", "=", record.partner_id.id),
                        ("celprincipal", "=", True),
                    ]
                )
                if duplicates:
                    raise ValidationError(_("Ya existe un teléfono principal para este contacto."))


class CrmLead(models.Model):
    _inherit = "crm.lead"

    crm_telefono_ids = fields.One2many(
        "crm.telefono",
        "lead_id",
        string="Teléfonos",
        copy=False,
    )


class ResPartner(models.Model):
    _inherit = "res.partner"

    crm_telefono_ids = fields.One2many(
        "crm.telefono",
        "partner_id",
        string="Teléfonos CRM",
        copy=False,
    )

