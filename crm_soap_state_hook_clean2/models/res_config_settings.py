# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # Toggle principal
    crm_soap_enable = fields.Boolean(string="Habilitar llamada SOAP", default=True)

    # Etapa "perdida" (opcional, sólo referencial). No existe is_lost en Odoo 18,
    # por eso NO aplicamos dominio. Seleccioná la etapa que uses como "Perdido".
    crm_lost_stage_id = fields.Many2one(
        "crm.stage",
        string="Etapa Perdida (referencia)",
        help="Etapa que usás como 'Perdido' (opcional, sólo a modo referencial).",
    )

    # Parámetros de conexión
    crm_soap_url = fields.Char(string="URL SOAP", help="Sin ?WSDL")
    crm_soap_timeout = fields.Integer(string="Timeout (s)", default=15)
    crm_soap_usucod = fields.Char(string="Usucod")

    # Nuevo WS E03
    crm_soap_ws_e03_url = fields.Char(string="URL WS E03", help="Sin ?WSDL")
    crm_soap_ws_e03_timeout = fields.Integer(string="Timeout WS E03 (s)", default=15)

    # Parámetros de negocio
    crm_soap_riepedinfrespcod_won = fields.Char(
        string="Riepedinfrespcod (Ganado)", default="OP-A-LIQ"
    )
    crm_soap_riepedinfrespcod_lost = fields.Char(
        string="Riepedinfrespcod (Perdido)", default="DE"
    )
    crm_soap_msg_won = fields.Char(string="Mensaje Ganado", default="Oportunidad Ganada")
    crm_soap_msg_lost = fields.Char(string="Mensaje Perdido", default="Oportunidad Perdida")

    # Lógica de cambio (global o por estado) — acepta X, U, M
    crm_soap_logica_cambio = fields.Selection(
        selection=[("X", "X"), ("U", "U"), ("M", "M")],
        string="Lógica cambio (global)",
        default="U",
        help="Si no se define por estado, se usa este valor.",
    )
    crm_soap_logica_cambio_won = fields.Selection(
        selection=[("X", "X"), ("U", "U"), ("M", "M")],
        string="Lógica cambio para Ganado",
    )
    crm_soap_logica_cambio_lost = fields.Selection(
        selection=[("X", "X"), ("U", "U"), ("M", "M")],
        string="Lógica cambio para Perdido",
    )

    # Logging a archivo
    crm_soap_log_enable = fields.Boolean(string="Log a archivo", default=True)
    crm_soap_log_payload = fields.Boolean(string="Log payload", default=True)
    crm_soap_log_response = fields.Boolean(string="Log respuesta", default=True)
    crm_soap_log_snippet_len = fields.Integer(string="Tamaño snippet", default=600)
    crm_soap_log_mask_usucod = fields.Boolean(string="Enmascarar Usucod", default=True)

    # Logging a BD (ir.logging) para el menú
    crm_soap_log_db_enable = fields.Boolean(string="Log en BD (ir.logging)", default=True)
    crm_soap_log_db_payload = fields.Boolean(string="Logear payload en BD", default=False)
    crm_soap_log_db_response = fields.Boolean(string="Logear respuesta en BD", default=False)

    @api.model
    def get_values(self):
        res = super().get_values()
        ICP = self.env["ir.config_parameter"].sudo()

        def gp(key, default=None):
            v = ICP.get_param(key, default if default is not None else "")
            return v

        res.update(
            crm_soap_enable=gp("crm_soap_state_hook.enable", "True") in ("True", "1"),
            crm_soap_url=gp("crm_soap_state_hook.url", ""),
            crm_soap_timeout=int(gp("crm_soap_state_hook.timeout", "15") or 15),
            crm_soap_usucod=gp("crm_soap_state_hook.usucod", ""),
            crm_soap_riepedinfrespcod_won=gp(
                "crm_soap_state_hook.riepedinfrespcod_won", "OP-A-LIQ"
            ),
            crm_soap_riepedinfrespcod_lost=gp(
                "crm_soap_state_hook.riepedinfrespcod_lost", "DE"
            ),
            crm_soap_msg_won=gp("crm_soap_state_hook.msg_won", "Oportunidad Ganada"),
            crm_soap_msg_lost=gp("crm_soap_state_hook.msg_lost", "Oportunidad Perdida"),
            crm_soap_logica_cambio=gp("crm_soap_state_hook.logica_cambio", "U") or "U",
            crm_soap_logica_cambio_won=gp("crm_soap_state_hook.logica_cambio_won", "") or False,
            crm_soap_logica_cambio_lost=gp("crm_soap_state_hook.logica_cambio_lost", "") or False,
            crm_soap_log_enable=gp("crm_soap_state_hook.log.enable", "True") in ("True", "1"),
            crm_soap_log_payload=gp("crm_soap_state_hook.log.payload", "True") in ("True", "1"),
            crm_soap_log_response=gp("crm_soap_state_hook.log.response", "True") in ("True", "1"),
            crm_soap_log_snippet_len=int(gp("crm_soap_state_hook.log.snippet_len", "600") or 600),
            crm_soap_log_mask_usucod=gp("crm_soap_state_hook.log.mask_usucod", "True")
            in ("True", "1"),
            crm_soap_log_db_enable=gp("crm_soap_state_hook.log.db.enable", "True")
            in ("True", "1"),
            crm_soap_log_db_payload=gp("crm_soap_state_hook.log.db.payload", "False")
            in ("True", "1"),
            crm_soap_log_db_response=gp("crm_soap_state_hook.log.db.response", "False")
            in ("True", "1"),
            crm_soap_ws_e03_url=gp("crm_soap_state_hook.ws_e03.url", ""),
            crm_soap_ws_e03_timeout=int(gp("crm_soap_state_hook.ws_e03.timeout", "15") or 15),
        )
        # etapa perdida (opcional)
        lost_stage_xmlid = gp("crm_soap_state_hook.lost_stage_xmlid", "")
        if lost_stage_xmlid:
            try:
                _, rec_id = self.env["ir.model.data"]._xmlid_to_res_model_res_id(
                    lost_stage_xmlid, raise_if_not_found=False
                ) or (None, None)
                if rec_id:
                    res["crm_lost_stage_id"] = rec_id
            except Exception:
                pass
        return res

    def set_values(self):
        super().set_values()
        ICP = self.env["ir.config_parameter"].sudo()

        def sp(key, val):
            if val in (False, None):
                ICP.set_param(key, "")
            else:
                ICP.set_param(key, str(val))

        sp("crm_soap_state_hook.enable", self.crm_soap_enable)
        sp("crm_soap_state_hook.url", self.crm_soap_url or "")
        sp("crm_soap_state_hook.timeout", self.crm_soap_timeout or 15)
        sp("crm_soap_state_hook.usucod", self.crm_soap_usucod or "")
        sp(
            "crm_soap_state_hook.riepedinfrespcod_won",
            self.crm_soap_riepedinfrespcod_won or "",
        )
        sp(
            "crm_soap_state_hook.riepedinfrespcod_lost",
            self.crm_soap_riepedinfrespcod_lost or "",
        )
        sp("crm_soap_state_hook.msg_won", self.crm_soap_msg_won or "")
        sp("crm_soap_state_hook.msg_lost", self.crm_soap_msg_lost or "")

        sp("crm_soap_state_hook.logica_cambio", self.crm_soap_logica_cambio or "U")
        sp(
            "crm_soap_state_hook.logica_cambio_won",
            self.crm_soap_logica_cambio_won or "",
        )
        sp(
            "crm_soap_state_hook.logica_cambio_lost",
            self.crm_soap_logica_cambio_lost or "",
        )

        sp("crm_soap_state_hook.log.enable", self.crm_soap_log_enable)
        sp("crm_soap_state_hook.log.payload", self.crm_soap_log_payload)
        sp("crm_soap_state_hook.log.response", self.crm_soap_log_response)
        sp("crm_soap_state_hook.log.snippet_len", self.crm_soap_log_snippet_len or 600)
        sp("crm_soap_state_hook.log.mask_usucod", self.crm_soap_log_mask_usucod)

        sp("crm_soap_state_hook.log.db.enable", self.crm_soap_log_db_enable)
        sp("crm_soap_state_hook.log.db.payload", self.crm_soap_log_db_payload)
        sp("crm_soap_state_hook.log.db.response", self.crm_soap_log_db_response)
        sp("crm_soap_state_hook.ws_e03.url", self.crm_soap_ws_e03_url or "")
        sp("crm_soap_state_hook.ws_e03.timeout", self.crm_soap_ws_e03_timeout or 15)

        # etapa perdida (opcional) — guardamos xmlid si existe
        if self.crm_lost_stage_id:
            xmlid = self.env["ir.model.data"]._get_xmlid(self.crm_lost_stage_id)
            sp("crm_soap_state_hook.lost_stage_xmlid", xmlid or "")
        else:
            sp("crm_soap_state_hook.lost_stage_xmlid", "")
