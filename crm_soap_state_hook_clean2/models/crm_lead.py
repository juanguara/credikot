# -*- coding: utf-8 -*-
import html
import logging
from xml.etree import ElementTree as ET

from odoo import api, models, _
from odoo.exceptions import UserError, ValidationError

from urllib.parse import urljoin


_LOGGER_NAME = "odoo.addons.crm_soap_state_hook.models.crm_lead"
E03_REPORT_BASE_URL = "http://webinterna.eft.ar/"


class CrmLead(models.Model):
    _inherit = "crm.lead"

    # ============== Helpers de logging ==============

    def _logger(self):
        return logging.getLogger(_LOGGER_NAME)

    def _log_db(self, level: str, message: str, func: str = ""):
        """Persiste en ir.logging para el menú."""
        ICP = self.env["ir.config_parameter"].sudo()
        if ICP.get_param("crm_soap_state_hook.log.db.enable", "True") not in ("True", "1"):
            return
        vals = {
            "name": "crm_soap_state_hook",
            "type": "server",
            "dbname": self.env.cr.dbname,
            "level": (level or "INFO").upper(),
            "message": message or "",
            "path": __name__,
            "line": "0",
            "func": func or "_log_db",
        }
        self.env["ir.logging"].sudo().create(vals)

    # ============== Validaciones CBU ==============

    def _get_studio_value(self, *field_names):
        for field_name in field_names:
            if field_name in self._fields:
                value = getattr(self, field_name)
                if value not in (False, None, ""):
                    return value
        return False

    @staticmethod
    def _compute_cbu_check_digit(digits, weights):
        total = sum(int(d) * w for d, w in zip(digits, weights))
        return (10 - (total % 10)) % 10

    def _validate_cbu_check_digits(self, digits: str) -> bool:
        if len(digits) != 22:
            return False
        block_one = digits[:7]
        digit_one = int(digits[7])
        block_two = digits[8:21]
        digit_two = int(digits[21])
        weights_one = (7, 1, 3, 9, 7, 1, 3)
        weights_two = (3, 9, 7, 1, 3, 9, 7, 1, 3, 9, 7, 1, 3)
        return (
            self._compute_cbu_check_digit(block_one, weights_one) == digit_one
            and self._compute_cbu_check_digit(block_two, weights_two) == digit_two
        )

    def _extract_bank_identification_code(self):
        bank = self._get_studio_value("x_studio_banco")
        if not bank:
            return ""
        candidate_fields = (
            "bank_identification_code",
            "x_studio_bank_identification_code",
            "bic",
            "code",
        )
        for field_name in candidate_fields:
            value = getattr(bank, field_name, False)
            if not value:
                continue
            digits = "".join(ch for ch in str(value) if ch.isdigit())
            if digits:
                return digits
        return ""

    def _get_clean_cbu(self):
        raw = self._get_studio_value("x_studio_cbu", "x_studio_CBU")
        if not raw:
            return ""
        return str(raw).strip()

    @api.constrains("x_studio_cbu", "x_studio_banco")
    def _check_x_studio_cbu(self):
        for lead in self:
            cbu = lead._get_clean_cbu()
            if not cbu:
                continue
            if not cbu.isdigit():
                raise ValidationError(_("El CBU sólo puede contener números."))
            if len(cbu) != 22:
                raise ValidationError(_("El CBU debe tener exactamente 22 dígitos."))
            if not lead._validate_cbu_check_digits(cbu):
                raise ValidationError(_("El CBU ingresado no supera la validación de dígitos verificadores."))
            bank_code = lead._extract_bank_identification_code()
            if not bank_code:
                raise ValidationError(_("Seleccione un banco con código de identificación para validar el CBU."))
            if len(bank_code) < 3:
                raise ValidationError(_("El código de identificación del banco debe tener al menos 3 dígitos."))
            if cbu[:3] != bank_code[:3]:
                raise ValidationError(
                    _("Los primeros 3 dígitos del CBU deben coincidir con el código de identificación del banco (%s).")
                    % bank_code[:3]
                )

    # ============== Envelope EXACTO ==============

    def _build_soap_envelope_exact(
        self, usucod: str, riepedid: str, riepedinfrespcod: str, mensaje: str, logica: str
    ) -> bytes:
        """
        Construye exactamente:
        <x:Envelope xmlns:x="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ns1="GX">
          <x:Header/>
          <x:Body>
            <ns1:RiesgoSeguimientoMsgAdd_2_WS.Execute>
              <ns1:Usucod>...</ns1:Usucod>
              <ns1:Riepedid>...</ns1:Riepedid>
              <ns1:Riepedinfrespcod_nuevo>...</ns1:Riepedinfrespcod_nuevo>
              <ns1:Riepedsegrmensaje>...</ns1:Riepedsegrmensaje>
              <ns1:Logicacambioestado>M</ns1:Logicacambioestado>
            </ns1:RiesgoSeguimientoMsgAdd_2_WS.Execute>
          </x:Body>
        </x:Envelope>
        IMPORTANTE:
         - Prefijo x y ns1 exactos
         - Header vacío presente
         - Tag 'Logicacambioestado' (con 'c' minúscula)
         - Sin declaración XML inicial
        """
        usucod_x = html.escape((usucod or "").strip())
        riepedid_x = html.escape((str(riepedid) or "").strip())
        riecod_x = html.escape((riepedinfrespcod or "").strip())
        mensaje_x = html.escape((mensaje or "").strip())
        logica_u = (logica or "").strip().upper()
        if logica_u not in ("X", "U", "M"):
            logica_u = "U"
        logica_x = html.escape(logica_u)

        envelope = (
            f'<x:Envelope xmlns:x="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ns1="GX">'
            f"<x:Header/>"
            f"<x:Body>"
            f"<ns1:RiesgoSeguimientoMsgAdd_2_WS.Execute>"
            f"<ns1:Usucod>{usucod_x}</ns1:Usucod>"
            f"<ns1:Riepedid>{riepedid_x}</ns1:Riepedid>"
            f"<ns1:Riepedinfrespcod_nuevo>{riecod_x}</ns1:Riepedinfrespcod_nuevo>"
            f"<ns1:Riepedsegrmensaje>{mensaje_x}</ns1:Riepedsegrmensaje>"
            f"<ns1:Logicacambioestado>{logica_x}</ns1:Logicacambioestado>"
            f"</ns1:RiesgoSeguimientoMsgAdd_2_WS.Execute>"
            f"</x:Body>"
            f"</x:Envelope>"
        )
        return envelope.encode("utf-8")

    def _soap_post(self, url: str, payload: bytes, soap_action: str, timeout: int = 15):
        import requests

        url = (url or "").strip()
        if "?" in url:
            url = url.split("?", 1)[0]

        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": soap_action,
            "User-Agent": "Odoo/18 SOAP Hook",
        }
        return requests.post(url, data=payload, headers=headers, timeout=timeout)

    def _pick_logica_cambio(self, is_won: bool) -> str:
        ICP = self.env["ir.config_parameter"].sudo()
        key = (
            "crm_soap_state_hook.logica_cambio_won"
            if is_won
            else "crm_soap_state_hook.logica_cambio_lost"
        )
        raw = ICP.get_param(key) or ICP.get_param("crm_soap_state_hook.logica_cambio", "U")
        v = (raw or "").strip().upper()
        return v if v in ("X", "U", "M") else "U"

    def _call_legacy_state_change(self, mensaje: str, is_won: bool) -> bool:
        self.ensure_one()
        ICP = self.env["ir.config_parameter"].sudo()

        if ICP.get_param("crm_soap_state_hook.enable", "True") not in ("True", "1"):
            return True

        riepedid = str(self.x_studio_solicitud or "").strip()
        if not riepedid:
            self._logger().warning("No hay x_studio_solicitud; se omite SOAP.")
            self._log_db("WARNING", "No hay x_studio_solicitud; se omite SOAP.", "call_legacy")
            return True

        url = ICP.get_param("crm_soap_state_hook.url") or ""
        timeout = int(ICP.get_param("crm_soap_state_hook.timeout", "15") or 15)
        usucod = ICP.get_param("crm_soap_state_hook.usucod", "") or ""
        riepedinfrespcod = (
            ICP.get_param(
                "crm_soap_state_hook.riepedinfrespcod_won" if is_won else "crm_soap_state_hook.riepedinfrespcod_lost",
                "",
            )
            or ""
        )
        logica = self._pick_logica_cambio(is_won=is_won)

        payload = self._build_soap_envelope_exact(
            usucod=usucod,
            riepedid=riepedid,
            riepedinfrespcod=riepedinfrespcod,
            mensaje=mensaje or "",
            logica=logica,
        )

        # Logs (archivo y BD)
        mask = ICP.get_param("crm_soap_state_hook.log.mask_usucod", "True") in ("True", "1")
        usucod_log = "***" if mask and usucod else usucod

        if ICP.get_param("crm_soap_state_hook.log.enable", "True") in ("True", "1"):
            self._logger().info(
                "SOAP request POST | url=%s timeout=%s is_won=%s riepedid=%s riepedinfrespcod=%s logica=%s usucod=%s",
                url,
                timeout,
                is_won,
                riepedid,
                riepedinfrespcod,
                logica,
                usucod_log,
            )

        if ICP.get_param("crm_soap_state_hook.log.db.enable", "True") in ("True", "1"):
            self._log_db(
                "INFO",
                f"SOAP request POST url={url} is_won={is_won} riepedid={riepedid} riepedinfrespcod={riepedinfrespcod} logica={logica}",
                "call_legacy",
            )

        if ICP.get_param("crm_soap_state_hook.log.payload", "True") in ("True", "1"):
            snlen = int(ICP.get_param("crm_soap_state_hook.log.snippet_len", "600") or 600)
            snippet = payload[:snlen].decode("utf-8", errors="ignore")
            self._logger().debug("SOAP payload snippet | %s", snippet)
            if ICP.get_param("crm_soap_state_hook.log.db.payload", "False") in ("True", "1"):
                self._log_db("DEBUG", f"PAYLOAD: {snippet}", "call_legacy")

        resp = self._soap_post(
            url,
            payload,
            soap_action="GX#RiesgoSeguimientoMsgAdd_2_WS.Execute",
            timeout=timeout,
        )

        if ICP.get_param("crm_soap_state_hook.log.response", "True") in ("True", "1"):
            body = (resp.text or "")
            snlen = int(ICP.get_param("crm_soap_state_hook.log.snippet_len", "600") or 600)
            self._logger().debug("SOAP response | status=%s body=%s", resp.status_code, body[:snlen])
            if ICP.get_param("crm_soap_state_hook.log.db.response", "False") in ("True", "1"):
                self._log_db("DEBUG", f"RESPONSE[{resp.status_code}]: {body[:snlen]}", "call_legacy")

        self._log_db("INFO", f"SOAP response status={resp.status_code}", "call_legacy")
        return resp.status_code == 200

    # ============== Confirmaciones ==============

    def _crm_soap_get_button_label(self, action_type: str) -> str:
        label = self.env.context.get("crm_soap_button_label")
        if label:
            return label
        return (
            _("marcar como ganada")
            if action_type == "won"
            else _("marcar como perdida")
        )

    def _crm_soap_prepare_confirmation(self, action_type: str, kwargs=None):
        button_label = self._crm_soap_get_button_label(action_type)
        message = _("¿Está seguro de %s?") % button_label
        ctx = dict(self.env.context or {})
        ctx.update(
            {
                "default_action_type": action_type,
                "default_message": message,
                "default_lead_ids": [(6, 0, self.ids)],
            }
        )
        if action_type == "lost" and kwargs:
            ctx["crm_soap_lost_kwargs"] = kwargs
        return {
            "name": _("Confirmación"),
            "type": "ir.actions.act_window",
            "res_model": "crm.soap.state.confirm.wizard",
            "view_mode": "form",
            "target": "new",
            "context": ctx,
        }

    # ============== Hooks en acciones ==============

    def action_set_won_rainbowman(self):
        if (
            not self.env.context.get("crm_soap_skip_confirm_won")
            and self.env.context.get("crm_soap_confirm_source") == "won_button"
        ):
            return self._crm_soap_prepare_confirmation("won")
        return super().action_set_won_rainbowman()

    def action_set_won(self):
        if (
            not self.env.context.get("crm_soap_skip_confirm_won")
            and self.env.context.get("crm_soap_confirm_source") == "won_button"
        ):
            return self._crm_soap_prepare_confirmation("won")
        res = super().action_set_won()
        try:
            ICP = self.env["ir.config_parameter"].sudo()
            msg = ICP.get_param("crm_soap_state_hook.msg_won", "Oportunidad Ganada")
            for lead in self:
                lead._call_legacy_state_change(msg, is_won=True)
        except Exception as e:
            self._logger().exception("Error en hook SOAP (won): %s", e)
            self._log_db("ERROR", f"Hook SOAP Won: {e}", "action_set_won")
        return res

    def action_set_lost(self, **kwargs):
        if (
            not self.env.context.get("crm_soap_skip_confirm_lost")
            and self.env.context.get("crm_soap_confirm_source") == "lost_button"
        ):
            return self._crm_soap_prepare_confirmation("lost", kwargs=kwargs)
        res = super().action_set_lost(**kwargs)
        try:
            ICP = self.env["ir.config_parameter"].sudo()
            msg = ICP.get_param("crm_soap_state_hook.msg_lost", "Oportunidad Perdida")
            for lead in self:
                lead._call_legacy_state_change(msg, is_won=False)
        except Exception as e:
            self._logger().exception("Error en hook SOAP (lost): %s", e)
            self._log_db("ERROR", f"Hook SOAP Lost: {e}", "action_set_lost")
        return res

    # ============== WS Riesgo Pedido E03 ==============

    def action_call_ws_e03(self):
        self.ensure_one()
        ICP = self.env["ir.config_parameter"].sudo()
        url = (ICP.get_param("crm_soap_state_hook.ws_e03.url") or "").strip()
        if not url:
            raise UserError(_("Configure la URL del servicio WS E03 en Ajustes."))

        timeout = int(ICP.get_param("crm_soap_state_hook.ws_e03.timeout", "15") or 15)
        usucod = (ICP.get_param("crm_soap_state_hook.usucod") or "").strip()
        if not usucod:
            raise UserError(_("Configure el Usucod en Ajustes."))

        riepedid = str(self.x_studio_solicitud or "").strip()
        if not riepedid:
            raise UserError(_("La oportunidad debe tener un número de solicitud (x_studio_solicitud)."))

        oferta_line = self._crm_soap_ws_e03_pick_offer_line()
        if not oferta_line:
            raise UserError(_("Debe seleccionar una línea de oferta para invocar el WS E03."))

        params = self._crm_soap_ws_e03_collect_params(
            usucod=usucod,
            riepedid=riepedid,
            oferta_line=oferta_line,
        )
        payload = self._crm_soap_ws_e03_build_envelope(params)

        if ICP.get_param("crm_soap_state_hook.log.enable", "True") in ("True", "1"):
            self._logger().info(
                "SOAP WS E03 | url=%s timeout=%s params=%s",
                url,
                timeout,
                {k: v for k, v in params.items() if k not in {"Firma_64"}},
            )
        if ICP.get_param("crm_soap_state_hook.log.payload", "True") in ("True", "1"):
            snlen = int(ICP.get_param("crm_soap_state_hook.log.snippet_len", "600") or 600)
            snippet = payload[:snlen].decode("utf-8", errors="ignore")
            self._logger().debug("SOAP WS E03 payload snippet | %s", snippet)
            if ICP.get_param("crm_soap_state_hook.log.db.payload", "False") in ("True", "1"):
                self._log_db("DEBUG", f"E03 PAYLOAD: {snippet}", "action_call_ws_e03")

        resp = self._soap_post(
            url,
            payload,
            soap_action="GX#RiesgoPedido_WS_E03.Execute",
            timeout=timeout,
        )

        if ICP.get_param("crm_soap_state_hook.log.response", "True") in ("True", "1"):
            snlen = int(ICP.get_param("crm_soap_state_hook.log.snippet_len", "600") or 600)
            body = resp.text or ""
            self._logger().debug("SOAP WS E03 response | status=%s body=%s", resp.status_code, body[:snlen])
            if ICP.get_param("crm_soap_state_hook.log.db.response", "False") in ("True", "1"):
                self._log_db("DEBUG", f"E03 RESPONSE[{resp.status_code}]: {body[:snlen]}", "action_call_ws_e03")

        if resp.status_code != 200:
            self._log_db("ERROR", f"WS E03 status={resp.status_code}", "action_call_ws_e03")
            raise UserError(_("WS E03 devolvió un código HTTP inesperado (%s).") % resp.status_code)

        result = self._crm_soap_ws_e03_parse_response(resp.content)
        p_ok = (result.get("p_ok") or "").strip().upper()
        if p_ok not in {"SI", "S", "OK", "1", "TRUE"}:
            message = result.get("p_msg") or _("El servicio WS E03 indicó un error.")
            self._log_db("ERROR", f"WS E03 error: {message}", "action_call_ws_e03")
            raise UserError(message)

        self._log_db("INFO", "WS E03 ejecutado correctamente.", "action_call_ws_e03")

        url_suffix = result.get("contrato_url") or result.get("link_firma") or ""
        if not url_suffix:
            raise UserError(_("WS E03 no devolvió una URL para abrir."))
        final_url = url_suffix.strip()
        if final_url and not final_url.lower().startswith(("http://", "https://")):
            final_url = urljoin(E03_REPORT_BASE_URL, final_url.lstrip("/"))

        mensaje = result.get("p_msg") or result.get("contrato_mensaje") or _("Operación completada.")
        self._logger().info("WS E03 OK | URL=%s Mensaje=%s", final_url, mensaje)
        self._log_db("INFO", f"WS E03 OK | URL={final_url} msg={mensaje}", "action_call_ws_e03")

        return {
            "type": "ir.actions.act_url",
            "target": "new",
            "url": final_url,
        }

    def _crm_soap_ws_e03_pick_offer_line(self):
        lines = getattr(self, "lineas_oferta_ids", None)
        if lines is None:
            try:
                self.env["lineas.oferta"]
            except KeyError:
                self._logger().warning("El módulo lineas_oferta no está instalado; WS E03 sin renglón seleccionado.")
            return False
        if not lines:
            return False
        selected = lines.filtered(
            lambda l: getattr(l, "rie_ped_rpta_lin_r_seleccion", "") == "S" or getattr(l, "is_selected", False)
        )
        if selected:
            return selected[0]
        return False

    def _crm_soap_ws_e03_collect_params(self, usucod: str, riepedid: str, oferta_line):
        get_attr = lambda field_name: getattr(self, field_name, False)

        cbu = (
            get_attr("x_studio_CBU")
            or get_attr("x_studio_cbu")
            or getattr(self.partner_id, "x_studio_CBU", False)
            or getattr(self.partner_id, "x_studio_cbu", False)
            or ""
        )

        lead_email = (self.email_from or self.partner_id.email or "").strip()
        telefono = (self.mobile or self.phone or "").strip()

        locality = (self.partner_id.city or self.city or "").strip()
        if not locality:
            locality = "CAPITAL FEDERAL"

        state = getattr(self, "state_id", False) or getattr(self.partner_id, "state_id", False)
        prov_code = ""
        if state:
            prov_code = (
                getattr(state, "x_studio_refexterna", False)
                or getattr(state, "x_studio_ref_externa", False)
                or getattr(state, "x_studio_refexterna_id", False)
                or ""
            )
        prov_code = 1 
        #str(prov_code or "").strip()
        if not prov_code:
            raise UserError(_("La provincia asociada a la oportunidad debe tener configurado 'x_studio_refexterna'."))

        params = {
            "Usucod": str(usucod or "").strip(),
            "Riepedimportarorigen": "ODOO-UPD",
            "Riepedid": str(riepedid or "").strip(),
            "Ofertarenglon": str(getattr(oferta_line, "rie_ped_rpta_lin_r_ren", "") or "").strip(),
            "Parametros": "",
            "Riepedemail_part": lead_email,
            "Riepedtelcelddn": "",
            "Riepedtelcelnro": "",
            "Riepedtelcelnotas": "",
            "Riepedbancocobrohaberescbu": cbu or "",
            "Riepeddompartcalle": "",
            "Riepeddompartpuerta": "",
            "Riepeddompartpiso": "",
            "Riepeddompartdpto": "",
            "Riepeddompartbarrio": "",
            "Riepeddompartblock": "",
            "Riepeddompartdistrito": "",
            "Riepeddompartentrec1": "",
            "Riepeddompartentrec2": "",
            "Riepeddomparthabitacion": "",
            "Riepeddompartindicacion": "",
            "Riepeddompartempresa": "",
            "Riepeddompartcasa": "",
            "Riepeddompartmanzana": "",
            "Riepeddompartmedidor": "",
            "Riepeddompartvivienda": "",
            "Provicod": prov_code,
            "Riepeddompartlocades": locality,
            "Firma_64": "",
        }

        if telefono:
            params["Riepedtelcelnotas"] = telefono

        return params

    def _crm_soap_ws_e03_build_envelope(self, params: dict) -> bytes:
        pieces = [
            f"<ns1:{key}>{html.escape(str(params.get(key, '') or ''))}</ns1:{key}>"
            for key in (
                "Usucod",
                "Riepedimportarorigen",
                "Riepedid",
                "Ofertarenglon",
                "Parametros",
                "Riepedemail_part",
                "Riepedtelcelddn",
                "Riepedtelcelnro",
                "Riepedtelcelnotas",
                "Riepedbancocobrohaberescbu",
                "Riepeddompartcalle",
                "Riepeddompartpuerta",
                "Riepeddompartpiso",
                "Riepeddompartdpto",
                "Riepeddompartbarrio",
                "Riepeddompartblock",
                "Riepeddompartdistrito",
                "Riepeddompartentrec1",
                "Riepeddompartentrec2",
                "Riepeddomparthabitacion",
                "Riepeddompartindicacion",
                "Riepeddompartempresa",
                "Riepeddompartcasa",
                "Riepeddompartmanzana",
                "Riepeddompartmedidor",
                "Riepeddompartvivienda",
                "Provicod",
                "Riepeddompartlocades",
                "Firma_64",
            )
        ]
        body = "".join(pieces)
        envelope = (
            f'<x:Envelope xmlns:x="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ns1="GX">'
            f"<x:Header/>"
            f"<x:Body>"
            f"<ns1:RiesgoPedido_WS_E03.Execute>"
            f"{body}"
            f"</ns1:RiesgoPedido_WS_E03.Execute>"
            f"</x:Body>"
            f"</x:Envelope>"
        )
        return envelope.encode("utf-8")

    def _crm_soap_ws_e03_parse_response(self, payload: bytes) -> dict:
        try:
            root = ET.fromstring(payload)
        except ET.ParseError as exc:
            raise UserError(_("La respuesta de WS E03 no es XML válido (%s).") % exc) from exc

        ns = {
            "soap": "http://schemas.xmlsoap.org/soap/envelope/",
            "gx": "GX",
        }
        result_node = root.find(".//gx:Riesgopedido_ws_e03_sdt", ns)
        if result_node is None:
            raise UserError(_("WS E03 no devolvió el nodo de respuesta esperado."))

        def gx_text(path):
            node = result_node.find(path, ns)
            text = node.text if node is not None and node.text is not None else ""
            return text.strip()

        data = {
            "riepedid": gx_text("gx:RiePedID"),
            "p_ok": gx_text("gx:P_OK"),
            "p_msg": gx_text("gx:P_Msj"),
            "contrato_resultado": gx_text("gx:Contrato/gx:Resultado"),
            "contrato_url": gx_text("gx:Contrato/gx:URL"),
            "contrato_mensaje": gx_text("gx:Contrato/gx:Mensaje"),
            "contrato_ruta": gx_text("gx:Contrato/gx:Ruta"),
            "contrato_archivo": gx_text("gx:Contrato/gx:Archivo"),
            "contrato_formulario": gx_text("gx:Contrato/gx:Formulario_ID"),
            "link_firma": gx_text("gx:LinkFirma"),
        }
        return data
