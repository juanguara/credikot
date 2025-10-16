# -*- coding: utf-8 -*-
import json
import logging
from datetime import datetime

import requests

from odoo import fields, models, _
from odoo.exceptions import UserError

from .ckt_card_validation import VENDOR_SELECTION

_logger = logging.getLogger(__name__)

ALLOWED_VENDORS = {vendor for vendor, _label in VENDOR_SELECTION}
CARD_VALIDATION_ENDPOINT = "http://sms.cooperativacredikot.com.ar/ServicioConsultas3_WS.aspx"


class ResPartner(models.Model):
    _inherit = "res.partner"

    cktc_card_validation_ids = fields.One2many(
        comodel_name="ckt.card.validation",
        inverse_name="partner_id",
        string="Validaciones de Tarjeta",
    )


class CrmLead(models.Model):
    _inherit = "crm.lead"

    cktc_card_validation_ids = fields.One2many(
        comodel_name="ckt.card.validation",
        inverse_name="lead_id",
        string="Validaciones de Tarjeta",
    )

    def _parse_card_validation_datetime(self, value):
        if not value:
            return False
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            cleaned = value.strip().replace("T", " ")
            for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S"):
                try:
                    return datetime.strptime(cleaned, pattern)
                except ValueError:
                    continue
        return False

    def _parse_card_validation_date(self, value):
        if not value:
            return False
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            cleaned = value.strip().replace("T", " ")
            for pattern in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
                try:
                    return datetime.strptime(cleaned, pattern).date()
                except ValueError:
                    continue
        return False

    def _normalize_vendor(self, value):
        if not value:
            return "other"
        vendor = value.strip().lower()
        return vendor if vendor in ALLOWED_VENDORS else "other"

    def action_actualizar_validaciones_tarjeta(self):
        self.ensure_one()
        solicitud_id = (self.x_studio_solicitud or "").strip()
        if not solicitud_id:
            raise UserError(_("La oportunidad debe tener un número de solicitud (x_studio_solicitud) para consultar validaciones."))

        headers = {
            "User-Agent": "Request-Promise",
            "version": "QUERY",
            "parametros": f"@QUERY=validacionescc;@RiePedId={solicitud_id}",
            "Content-Type": "application/json",
        }

        _logger.info("Consultando validaciones de tarjeta | lead_id=%s solicitud=%s", self.id, solicitud_id)
        try:
            response = requests.post(CARD_VALIDATION_ENDPOINT, headers=headers, data="", timeout=60)
            response.raise_for_status()
        except requests.RequestException as exc:
            _logger.error("Error al invocar API de validaciones: %s", exc)
            raise UserError(_("No se pudo conectar con el API de validaciones (%s).") % exc) from exc

        raw_text = (response.text or "").lstrip("\ufeff\r\n\t ")
        if not raw_text:
            raise UserError(_("El API de validaciones respondió vacío."))

        try:
            payload = response.json()
        except ValueError:
            try:
                payload = json.loads(raw_text)
            except Exception as exc:
                _logger.error("Respuesta inválida del API de validaciones: %s", exc)
                raise UserError(_("El API de validaciones devolvió un formato inválido: %s") % exc) from exc

        data = payload.get("DATOS") if isinstance(payload, dict) else None
        if not isinstance(data, list):
            raise UserError(_("El API de validaciones no devolvió datos válidos."))

        card_env = self.env["ckt.card.validation"].sudo()
        processed = 0
        vat_clean = "".join(ch for ch in (self.partner_id.vat or "") if ch.isdigit())

        for item in data:
            if not isinstance(item, dict):
                continue

            pan_obfuscated = (item.get("tarjofuscada") or "").strip()
            if not pan_obfuscated:
                continue

            validation_dt = self._parse_card_validation_datetime(item.get("fecha") or item.get("FechaAlta"))
            if not validation_dt:
                validation_dt = fields.Datetime.now()

            expiry_date = self._parse_card_validation_date(item.get("Tarjeta_Vence"))
            if expiry_date:
                expiry_date = fields.Date.to_date(expiry_date)

            vendor = self._normalize_vendor(item.get("TjReEmisor"))
            source_system = (item.get("Procesadora") or "").strip() or "Legacy"
            validation_result = (item.get("LegTjTipoToken") or "").strip()

            vals = {
                "lead_id": self.id,
                "lead_x_solicitud": solicitud_id,
                "partner_id": self.partner_id.id if self.partner_id else False,
                "partner_vat": "".join(ch for ch in (item.get("cuit") or vat_clean) if ch.isdigit()),
                "pan_obfuscated": pan_obfuscated,
                "vendor": vendor,
                "card_holder_name": (item.get("nombre") or "").strip(),
                "expiry_date": expiry_date,
                "validation_datetime": validation_dt,
                "validation_result": validation_result or _("Resultado no informado"),
                "source_system": source_system,
            }

            domain = [
                ("pan_obfuscated", "=", pan_obfuscated),
                ("validation_datetime", "=", fields.Datetime.to_string(validation_dt)),
                ("source_system", "=", source_system),
            ]
            existing = card_env.search(domain, limit=1)
            if existing:
                existing.write(vals)
            else:
                card_env.create(vals)
                processed += 1

        _logger.info(
            "Validaciones de tarjeta sincronizadas | lead_id=%s solicitud=%s registros=%s",
            self.id,
            solicitud_id,
            processed,
        )
        return processed
