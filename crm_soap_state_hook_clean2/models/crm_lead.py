# -*- coding: utf-8 -*-
import html
import logging
from xml.etree import ElementTree as ET

from odoo import api, models, _
from odoo.exceptions import UserError


_LOGGER_NAME = "odoo.addons.crm_soap_state_hook.models.crm_lead"


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

    def _soap_post_exact(self, url: str, payload: bytes, timeout: int = 15):
        import requests

        url = (url or "").strip()
        if "?" in url:
            url = url.split("?", 1)[0]  # sin ?WSDL ni querystring

        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "GX#RiesgoSeguimientoMsgAdd_2_WS.Execute",
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

        resp = self._soap_post_exact(url, payload, timeout=timeout)

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
        wsdl_url = url if url.lower().endswith("?wsdl") else f"{url}?WSDL"

        self._log_db("INFO", f"Intentando obtener WSDL E03: {wsdl_url}", "action_call_ws_e03")
        try:
            import requests
        except ImportError as exc:
            raise UserError(_("No se encontró 'requests'. Revise el entorno del servidor.")) from exc

        try:
            response = requests.get(wsdl_url, timeout=timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            self._logger().error("Error al obtener WSDL E03: %s", exc)
            self._log_db("ERROR", f"WS E03 error: {exc}", "action_call_ws_e03")
            raise UserError(
                _("No se pudo conectar con el servicio WS E03 (%s).") % exc
            ) from exc

        operations = self._crm_soap_parse_wsdl_operations(response.content)
        if operations:
            ops_str = ", ".join(operations[:8])
            if len(operations) > 8:
                ops_str += ", ..."
            message = _("Operaciones detectadas: %s") % ops_str
        else:
            message = _("WSDL descargado correctamente, sin operaciones detectadas.")

        self._log_db("INFO", message, "action_call_ws_e03")
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("WS E03"),
                "message": message,
                "type": "success",
                "sticky": False,
            },
        }

    def _crm_soap_parse_wsdl_operations(self, wsdl_bytes):
        try:
            root = ET.fromstring(wsdl_bytes)
        except ET.ParseError:
            return []

        ns = {
            "wsdl": "http://schemas.xmlsoap.org/wsdl/",
        }
        operations = []
        for operation in root.findall(".//wsdl:operation", ns):
            name = operation.get("name")
            if name:
                operations.append(name)
        return operations
