# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import hashlib
import re
from datetime import date

VENDOR_SELECTION = [
    ("visa", "VISA"),
    ("mastercard", "Mastercard"),
    ("amex", "American Express"),
    ("maestro", "Maestro"),
    ("cabal", "CABAL"),
    ("naranja", "Naranja"),
    ("other", "Otro"),
]

def _only_digits(s):
    return re.sub(r"\D", "", s or "")

class CktCardValidation(models.Model):
    _name = "ckt.card.validation"
    _description = "Validación de Tarjeta (CKT)"
    _order = "validation_datetime desc, id desc"
    _rec_name = "display_name"
    _sql_constraints = [
        # Evita duplicados en la combinación lógica
        ("uniq_validation_key",
         "unique(validation_key)",
         "Ya existe una validación con la misma combinación (partner/lead/vendor/last4/vencimiento/resultado/fecha)."),
    ]

    # Relaciones
    partner_id = fields.Many2one(
        "res.partner", string="Contacto", index=True, ondelete="set null"
    )
    partner_vat = fields.Char("VAT del Contacto", index=True)

    lead_id = fields.Many2one(
        "crm.lead", string="Oportunidad", index=True, ondelete="set null"
    )
    lead_x_solicitud = fields.Char(
        "x_studio_solicitud", index=True,
        help="ID de la solicitud (campo personalizado en CRM) para enlazar la oportunidad."
    )

    # Datos de tarjeta (ofuscados/derivados)
    pan_obfuscated = fields.Char(
        "Tarjeta (ofuscada)", required=True, index=True,
        help="Nunca almacenar PAN completo. Solo valores ofuscados."
    )
    pan_last4 = fields.Char("Últimos 4", compute="_compute_last4", store=True, index=True)
    pan_hash = fields.Char("Hash (ofuscado)", compute="_compute_hash", store=True, index=True)

    vendor = fields.Selection(VENDOR_SELECTION, string="Vendor", required=True, index=True)

    # Vencimiento: guardamos la fecha como día 1 del mes (YYYY-MM-01) y un helper MM/YY
    expiry_date = fields.Date("Vencimiento (YYYY-MM-01)", index=True, required=True)
    expiry_mm_yy = fields.Char("Vencimiento (MM/YY)", compute="_compute_mm_yy", store=True, index=True)

    # Resultado
    validation_datetime = fields.Datetime("Fecha/Hora Validación", required=True, index=True)
    validation_result = fields.Text("Resultado (texto)", required=True)

    # Gestión/operativa
    source_system = fields.Char("Origen", help="Nombre del sistema legacy que envía el registro.")
    validation_key = fields.Char("Clave de Idempotencia", compute="_compute_validation_key", store=True, index=True)

    # Nombre mostrado
    display_name = fields.Char("Descripción", compute="_compute_display_name", store=True)

    # Índices adicionales (a nivel ORM). Odoo ya indexa Many2one y campos index=True.
    _sql_constraints += [
        ("check_expiry_future", "CHECK (expiry_date IS NOT NULL)", "El vencimiento es obligatorio."),
    ]

    @api.depends("pan_obfuscated")
    def _compute_last4(self):
        for rec in self:
            digits = _only_digits(rec.pan_obfuscated)
            rec.pan_last4 = digits[-4:] if digits else False

    @api.depends("pan_obfuscated")
    def _compute_hash(self):
        for rec in self:
            norm = (rec.pan_obfuscated or "").strip()
            rec.pan_hash = hashlib.sha256(norm.encode("utf-8")).hexdigest() if norm else False

    @api.depends("expiry_date")
    def _compute_mm_yy(self):
        for rec in self:
            if rec.expiry_date:
                rec.expiry_mm_yy = fields.Date.to_date(rec.expiry_date).strftime("%m/%y")
            else:
                rec.expiry_mm_yy = False

    @api.depends("partner_id", "lead_id", "vendor", "pan_last4", "expiry_mm_yy", "validation_result", "validation_datetime")
    def _compute_validation_key(self):
        for rec in self:
            parts = [
                f"P:{rec.partner_id.id or 0}",
                f"L:{rec.lead_id.id or 0}",
                f"V:{rec.vendor or ''}",
                f"4:{rec.pan_last4 or ''}",
                f"E:{rec.expiry_mm_yy or ''}",
                f"R:{(rec.validation_result or '').strip()[:64]}",
                f"D:{fields.Datetime.to_string(rec.validation_datetime) if rec.validation_datetime else ''}",
            ]
            rec.validation_key = "|".join(parts)

    @api.depends("partner_id", "lead_id", "vendor", "pan_last4", "expiry_mm_yy", "validation_datetime")
    def _compute_display_name(self):
        for rec in self:
            lead = f"Lead:{rec.lead_id.id}" if rec.lead_id else "Lead:-"
            partner = rec.partner_id.display_name if rec.partner_id else "Contacto:-"
            when = fields.Datetime.context_timestamp(rec, rec.validation_datetime).strftime("%Y-%m-%d %H:%M") if rec.validation_datetime else "-"
            rec.display_name = f"[{rec.vendor.upper() if rec.vendor else 'VND'} • ****{rec.pan_last4 or '----'} • {rec.expiry_mm_yy or '--/--'}] {partner} | {lead} @ {when}"

    @api.constrains("expiry_date")
    def _check_expiry_date(self):
        for rec in self:
            # Permitimos vencidos para historial, pero bloqueá fechas imposibles (<1990 o >+20 años)
            if rec.expiry_date:
                if rec.expiry_date.year < 1990 or rec.expiry_date.year > date.today().year + 20:
                    raise ValidationError(_("Fecha de vencimiento inválida."))

    @api.model_create_multi
    def create(self, vals_list):
        # Resolución automática de partner_id por VAT y lead_id por x_studio_solicitud si vienen informados
        for vals in vals_list:
            if not vals.get("partner_id") and vals.get("partner_vat"):
                partner = self.env["res.partner"].search([("vat", "=", vals["partner_vat"])], limit=1)
                if partner:
                    vals["partner_id"] = partner.id
            if not vals.get("lead_id") and vals.get("lead_x_solicitud"):
                lead = self.env["crm.lead"].search([("x_studio_solicitud", "=", vals["lead_x_solicitud"])], limit=1)
                if lead:
                    vals["lead_id"] = lead.id
        return super().create(vals_list)

    def write(self, vals):
        # Si actualizan VAT o x_studio_solicitud, refrescar relaciones
        res = super().write(vals)
        for rec in self:
            if vals.get("partner_vat") and not vals.get("partner_id"):
                partner = self.env["res.partner"].search([("vat", "=", rec.partner_vat)], limit=1)
                if partner:
                    rec.partner_id = partner.id
            if vals.get("lead_x_solicitud") and not vals.get("lead_id"):
                lead = self.env["crm.lead"].search([("x_studio_solicitud", "=", rec.lead_x_solicitud)], limit=1)
                if lead:
                    rec.lead_id = lead.id
        return res
    class ResPartner(models.Model):
        _inherit = "res.partner"
        cktc_card_validation_ids = fields.One2many(
            "ckt.card.validation", "partner_id", string="Validaciones de Tarjeta"
        )

    class CrmLead(models.Model):
        _inherit = "crm.lead"
        cktc_card_validation_ids = fields.One2many(
            "ckt.card.validation", "lead_id", string="Validaciones de Tarjeta"
        )

