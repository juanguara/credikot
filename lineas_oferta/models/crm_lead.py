from datetime import datetime, date

from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError
import requests
import json
import logging

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = 'crm.lead'
    
    def _log_db_lineas_oferta(self, level: str, message: str, func: str = ""):
        """Persiste en ir.logging para el menú de líneas de oferta - SIEMPRE ejecuta sin validaciones."""
        try:
            vals = {
                "name": "lineas_oferta_api",
                "type": "server",
                "dbname": self.env.cr.dbname,
                "level": (level or "INFO").upper(),
                "message": message or "",
                "path": __name__,
                "line": "0",
                "func": func or "_log_db_lineas_oferta",
            }
            _logger.info(f"Creando log en ir.logging con valores: {vals}")
            log_record = self.env["ir.logging"].sudo().create(vals)
            _logger.info(f"Log creado exitosamente con ID: {log_record.id}")
            
        except Exception as e:
            _logger.error(f"Error al crear log en BD: {str(e)}")
            import traceback
            _logger.error(f"Traceback: {traceback.format_exc()}")
    
    lineas_oferta_ids = fields.One2many(
        'lineas.oferta',
        'lead_id',
        string='Líneas de Oferta'
    )
    
    lineas_oferta_count = fields.Integer(
        string='Cantidad de Ofertas',
        compute='_compute_lineas_oferta_count'
    )

    cliente_alerta_ids = fields.One2many(
        'cliente.alerta',
        'lead_id',
        string='Alertas del Cliente'
    )

    cliente_alerta_count = fields.Integer(
        string='Alertas',
        compute='_compute_cliente_alerta_count'
    )

    partner_birthdate = fields.Date(
        string='Fecha de Nacimiento',
        compute='_compute_partner_birthdate',
        readonly=True,
        store=False,
    )

    partner_age = fields.Integer(
        string='Edad',
        compute='_compute_partner_age',
        readonly=True,
        store=False,
    )
    
    @api.depends('lineas_oferta_ids')
    def _compute_lineas_oferta_count(self):
        for lead in self:
            lead.lineas_oferta_count = len(lead.lineas_oferta_ids)

    @api.depends('cliente_alerta_ids')
    def _compute_cliente_alerta_count(self):
        for lead in self:
            lead.cliente_alerta_count = len(lead.cliente_alerta_ids)

    @api.depends('partner_id', 'partner_id.x_studio_fechanacimiento')
    def _compute_partner_birthdate(self):
        for lead in self:
            partner = lead.partner_id
            birthdate = False
            if partner:
                birthdate = getattr(partner, "x_studio_fechanacimiento", False)
                if not birthdate:
                    birthdate = getattr(partner, "x_studio_FechaNacimiento", False)
            lead.partner_birthdate = birthdate

    @api.depends('partner_birthdate')
    def _compute_partner_age(self):
        today = fields.Date.context_today(self)
        if isinstance(today, str):
            today = fields.Date.from_string(today)
        for lead in self:
            birthdate = lead.partner_birthdate
            if isinstance(birthdate, str):
                birthdate = fields.Date.from_string(birthdate)
            if not birthdate:
                lead.partner_age = False
                continue
            age = today.year - birthdate.year - (
                (today.month, today.day) < (birthdate.month, birthdate.day)
            )
            lead.partner_age = max(age, 0)

    def _format_vat_as_cuit(self, vat_value):
        digits = "".join(ch for ch in (vat_value or "") if ch.isdigit())
        if len(digits) != 11:
            return False
        return f"{digits[:2]}-{digits[2:10]}-{digits[10:]}"

    def _sync_lineas_oferta_records(self):
        """
        Invoca el API de líneas de oferta y sincroniza los registros locales.
        Devuelve la cantidad de líneas recibidas desde el servicio externo.
        """
        self.ensure_one()
        
        # Log inicial
        _logger.info(f'Iniciando action_actualizar_lineas_oferta para lead_id: {self.id}')
        self._log_db_lineas_oferta("INFO", f"Método iniciado para lead_id: {self.id}", "action_actualizar_lineas_oferta")
        
        # Log de prueba para verificar que funciona
        _logger.info('Logging de prueba - esto debería aparecer en el log del servidor')
        self._log_db_lineas_oferta("INFO", "Log de prueba - esto debería aparecer en ir.logging", "test_log")
        
        # Verificar que existe x_studio_solicitud
        if not hasattr(self, 'x_studio_solicitud') or not self.x_studio_solicitud:
            error_msg = 'La oportunidad debe tener un número de solicitud (x_studio_solicitud)'
            _logger.error(error_msg)
            self._log_db_lineas_oferta("ERROR", error_msg, "action_actualizar_lineas_oferta")
            raise UserError(_(error_msg))
        
        solicitud_id = self.x_studio_solicitud
        self._log_db_lineas_oferta("INFO", f"Solicitud ID encontrada: {solicitud_id}", "action_actualizar_lineas_oferta")
        
        try:
            # Log inicial del try
            _logger.info("=== INICIANDO BLOQUE TRY ===")
            self._log_db_lineas_oferta("INFO", "=== INICIANDO BLOQUE TRY ===", "action_actualizar_lineas_oferta")
            
            # Configurar la petición a la API (POST con headers como en el curl)
            url = "http://sms.cooperativacredikot.com.ar/ServicioConsultas3_WS.aspx"
            headers = {
                'User-Agent': 'Request-Promise',
                'version': 'QUERY',
                'parametros': f'@QUERY=lineasdeoferta;@riepedid={solicitud_id}',
                'Content-Type': 'application/json'
            }
            # Para POST, no necesitamos params, solo headers y data vacío
            data = ''
            
            _logger.info(f'Llamando a API para solicitud: {solicitud_id}')
            self._log_db_lineas_oferta("INFO", f"Configurando petición API para solicitud: {solicitud_id}", "action_actualizar_lineas_oferta")
            
            # Log de configuración
            self._log_db_lineas_oferta("INFO", f"URL configurada: {url}", "action_actualizar_lineas_oferta")
            self._log_db_lineas_oferta("INFO", f"Headers configurados: {headers}", "action_actualizar_lineas_oferta")
            self._log_db_lineas_oferta("INFO", f"Data configurado: '{data}'", "action_actualizar_lineas_oferta")
            
            # Realizar la petición POST
            self._log_db_lineas_oferta("INFO", "Iniciando petición HTTP POST", "action_actualizar_lineas_oferta")
            _logger.info("Iniciando petición HTTP POST")
            
            try:
                response = requests.post(url, headers=headers, data=data, timeout=30)
                self._log_db_lineas_oferta("INFO", f"Petición HTTP POST completada. Status: {response.status_code}", "action_actualizar_lineas_oferta")
                _logger.info(f"Petición HTTP POST completada. Status: {response.status_code}")
            except Exception as http_error:
                self._log_db_lineas_oferta("ERROR", f"Error en petición HTTP POST: {str(http_error)}", "action_actualizar_lineas_oferta")
                _logger.error(f"Error en petición HTTP POST: {str(http_error)}")
                raise
            
            response.raise_for_status()
            self._log_db_lineas_oferta("INFO", "Status HTTP verificado exitosamente", "action_actualizar_lineas_oferta")
            
            # Log de la respuesta raw
            self._log_db_lineas_oferta("DEBUG", f"Status Code: {response.status_code}", "action_actualizar_lineas_oferta")
            self._log_db_lineas_oferta("DEBUG", f"Content-Type: {response.headers.get('content-type', 'No especificado')}", "action_actualizar_lineas_oferta")
            self._log_db_lineas_oferta("DEBUG", f"Response text (primeros 500 chars): {response.text[:500]}", "action_actualizar_lineas_oferta")
            
            # Validaciones previas al parseo
            raw_text = (response.text or "").lstrip("\ufeff\n\r\t ")
            if not raw_text.strip():
                self._log_db_lineas_oferta("ERROR", "Respuesta vacía de la API", "action_actualizar_lineas_oferta")
                raise UserError(_('La API respondió vacío'))
            if raw_text[:1] == '<':
                # Probable HTML de error
                snippet = raw_text[:500]
                self._log_db_lineas_oferta("ERROR", f"La API retornó HTML (posible error). Snippet: {snippet}", "action_actualizar_lineas_oferta")
                raise UserError(_('La API retornó HTML (posible error). Ver logs'))

            # Parsear respuesta JSON
            try:
                response_data = response.json()
                self._log_db_lineas_oferta("DEBUG", f"JSON parseado exitosamente: {type(response_data)}", "action_actualizar_lineas_oferta")
            except ValueError as json_error:
                self._log_db_lineas_oferta("ERROR", f"Error JSON directo: {str(json_error)}", "action_actualizar_lineas_oferta")
                # Respuestas que llegan como texto JSON embebido
                try:
                    response_data = json.loads(raw_text)
                    self._log_db_lineas_oferta("DEBUG", f"JSON parseado desde text exitosamente: {type(response_data)}", "action_actualizar_lineas_oferta")
                except Exception as text_error:
                    self._log_db_lineas_oferta("ERROR", f"Error JSON desde text: {str(text_error)}", "action_actualizar_lineas_oferta")
                    raise UserError(_('La respuesta de la API no es un JSON válido: %s') % str(text_error))
            
            # La API retorna {"DATOS": [...]}
            if not isinstance(response_data, dict) or 'DATOS' not in response_data:
                raise UserError(_('La respuesta de la API no tiene el formato esperado (falta DATOS)'))
            
            data = response_data['DATOS']
            if not isinstance(data, list):
                raise UserError(_('La respuesta de la API no contiene una lista de datos'))
            
            _logger.info(f'API respondió con {len(data)} registros')
            self._log_db_lineas_oferta("INFO", f"API respondió con {len(data)} registros", "action_actualizar_lineas_oferta")
            
            # Log de la respuesta completa
            response_snippet = json.dumps(data, indent=2)[:1000]  # Primeros 1000 caracteres
            self._log_db_lineas_oferta("DEBUG", f"Respuesta API (snippet): {response_snippet}", "action_actualizar_lineas_oferta")
            
            # Obtener IDs actuales en la base de datos
            existing_lines = self.env['lineas.oferta'].sudo().search([
                ('lead_id', '=', self.id)
            ])
            
            # Crear conjunto de claves compuestas de la respuesta API
            api_keys = set()
            lines_to_create = []
            selected_records = self.env['lineas.oferta']
            
            for item in data:
                rie_ped_id = int(item.get('RiePedID', 0))
                rie_ped_ren = int(item.get('RiePedRptaLinRRen', 0))
                api_keys.add((rie_ped_id, rie_ped_ren))
                
                # Log detallado del parsing
                self._log_db_lineas_oferta("DEBUG", f"Parseando registro: ID={rie_ped_id}, Ren={rie_ped_ren}, Selección={item.get('RiePedRptaLinRSeleccion')}", "action_actualizar_lineas_oferta")
                
                # Preparar valores para crear/actualizar
                vals = {
                    'lead_id': self.id,
                    'rie_ped_id': rie_ped_id,
                    'rie_ped_rpta_lin_r_ren': rie_ped_ren,
                    'rie_ped_rpta_lin_r_auditor': item.get('RiePedRptaLinRAuditor'),
                    'rie_ped_rpta_lin_r_lin_cred': int(item.get('RiePedRptaLinRLinCred', 0)),
                    'rie_ped_rpta_lin_r_lin_cred_des': item.get('RiePedRptaLinRLinCredDes', ''),
                    'rie_ped_rpta_lin_r_tasa': float(item.get('RiePedRptaLinRTasa', 0)),
                    'rie_ped_rpta_lin_r_capital': float(item.get('RiePedRptaLinRCapital', 0)),
                    'rie_ped_rpta_lin_r_capital_en_mano': float(item.get('RiePedRptaLinRCapitalEnMano', 0)),
                    'rie_ped_rpta_lin_r_capital_neto_ren': float(item.get('RiePedRptaLinRCapitalNetoRen', 0)),
                    'rie_ped_rpta_lin_r_cuotas': int(item.get('RiePedRptaLinRCuotas', 0)),
                    'rie_ped_rpta_lin_r_imp_cuota': float(item.get('RiePedRptaLinRImpCuota', 0)),
                    'rie_ped_rpta_lin_r_lin_cred_ren': int(item.get('RiePedRptaLinRLinCredRen', 0)),
                    'rie_ped_rpta_lin_r_rima_id_des': item.get('RiePedRptaLinRRimaID_Des', ''),
                    'rie_ped_rpta_lin_r_tir': float(item.get('RiePedRptaLinRTIR', 0)),
                    'rie_ped_rpta_lin_r_tea': float(item.get('RiePedRptaLinRTEA', 0)),
                    'rie_ped_rpta_lin_r_tem': float(item.get('RiePedRptaLinRTEM', 0)),
                    'rie_ped_rpta_lin_r_servicio': float(item.get('RiePedRptaLinRServicio', 0)),
                    'rie_ped_rpta_lin_r_gastos': float(item.get('RiePedRptaLinRGastos', 0)),
                }
                selection_raw = (item.get('RiePedRptaLinRSeleccion') or "").strip().upper()
                selection_value = 'S' if selection_raw == 'S' else 'N'
                vals['rie_ped_rpta_lin_r_seleccion'] = selection_value
                vals['is_selected'] = selection_value == 'S'
                
                # Buscar si existe
                existing = existing_lines.filtered(
                    lambda l: l.rie_ped_id == rie_ped_id and 
                             l.rie_ped_rpta_lin_r_ren == rie_ped_ren
                )
                
                if existing:
                    update_vals = vals.copy()
                    update_vals.pop('lead_id', None)
                    existing.sudo().write(update_vals)
                    if selection_value == 'S':
                        selected_records = (selected_records | existing)
                else:
                    # Crear nuevo
                    lines_to_create.append(vals)
            
            # Crear nuevas líneas
            if lines_to_create:
                new_lines = self.env['lineas.oferta'].sudo().create(lines_to_create)
                selected_records = (selected_records | new_lines.filtered(lambda l: l.is_selected))
            
            # Eliminar líneas que no están en la respuesta de la API
            lines_to_delete = existing_lines.filtered(
                lambda l: (l.rie_ped_id, l.rie_ped_rpta_lin_r_ren) not in api_keys
            )
            if lines_to_delete:
                lines_to_delete.sudo().unlink()
            for record in selected_records:
                try:
                    record._apply_selected_offer_values_to_lead()
                except Exception as exc:
                    self._log_db_lineas_oferta(
                        "ERROR",
                        f"No se pudo aplicar valores de oferta seleccionada (id={record.id}): {exc}",
                        "action_actualizar_lineas_oferta",
                    )
                    _logger.exception("Error aplicando oferta seleccionada al lead %s", self.id)
            success_msg = f"Se actualizaron {len(data)} líneas de oferta correctamente"
            _logger.info(success_msg)
            self._log_db_lineas_oferta("INFO", success_msg, "action_actualizar_lineas_oferta")
            return len(data)

        except UserError:
            raise
        except requests.exceptions.RequestException as e:
            error_msg = f'Error al llamar a la API: {str(e)}'
            _logger.error(error_msg)
            self._log_db_lineas_oferta("ERROR", error_msg, "action_actualizar_lineas_oferta")
            self._log_db_lineas_oferta("ERROR", "=== ERROR RequestException ===", "action_actualizar_lineas_oferta")
            raise UserError(_('Error al conectar con la API: %s') % str(e))
        except Exception as e:
            error_msg = f'Error al procesar datos: {str(e)}'
            _logger.error(error_msg)
            self._log_db_lineas_oferta("ERROR", error_msg, "action_actualizar_lineas_oferta")
            self._log_db_lineas_oferta("ERROR", "=== ERROR Exception General ===", "action_actualizar_lineas_oferta")
            import traceback
            self._log_db_lineas_oferta("ERROR", f"Traceback: {traceback.format_exc()}", "action_actualizar_lineas_oferta")
            raise UserError(_('Error al procesar los datos: %s') % str(e))

    def action_actualizar_lineas_oferta(self):
        """
        Llamar a la API y actualizar las líneas de oferta junto con las alertas,
        permitiendo que cada sincronización sea independiente.
        """
        self.ensure_one()

        offer_count = 0
        alert_count = 0
        card_count = 0
        offer_error = None
        alert_error = None
        card_error = None

        def _exception_to_message(exc):
            if isinstance(exc, UserError) and exc.args:
                return exc.args[0]
            return str(exc)

        try:
            with self.env.cr.savepoint():
                offer_count = self._sync_lineas_oferta_records()
        except Exception as exc:
            offer_error = _exception_to_message(exc)
            log_level = "WARNING" if isinstance(exc, UserError) else "ERROR"
            self._log_db_lineas_oferta(log_level, f"Error al sincronizar líneas de oferta: {offer_error}", "action_actualizar_lineas_oferta")
            if isinstance(exc, UserError):
                _logger.warning("Error al sincronizar líneas de oferta para lead_id=%s: %s", self.id, offer_error)
            else:
                _logger.exception("Error inesperado al sincronizar líneas de oferta para lead_id=%s", self.id)

        try:
            with self.env.cr.savepoint():
                alert_count = self.action_actualizar_alertas()
        except Exception as exc:
            alert_error = _exception_to_message(exc)
            log_level = "WARNING" if isinstance(exc, UserError) else "ERROR"
            self._log_db_lineas_oferta(log_level, f"Error al sincronizar alertas: {alert_error}", "action_actualizar_lineas_oferta")
            if isinstance(exc, UserError):
                _logger.warning("Error al sincronizar alertas para lead_id=%s: %s", self.id, alert_error)
            else:
                _logger.exception("Error inesperado al sincronizar alertas para lead_id=%s", self.id)

        try:
            with self.env.cr.savepoint():
                card_count = self.action_actualizar_validaciones_tarjeta()
        except Exception as exc:
            card_error = _exception_to_message(exc)
            log_level = "WARNING" if isinstance(exc, UserError) else "ERROR"
            self._log_db_lineas_oferta(log_level, f"Error al sincronizar validaciones de tarjeta: {card_error}", "action_actualizar_lineas_oferta")
            if isinstance(exc, UserError):
                _logger.warning("Error al sincronizar validaciones de tarjeta para lead_id=%s: %s", self.id, card_error)
            else:
                _logger.exception("Error inesperado al sincronizar validaciones de tarjeta para lead_id=%s", self.id)

        message_parts = []
        if offer_error:
            message_parts.append(_("Ofertas: %(msg)s") % {'msg': offer_error})
        else:
            message_parts.append(_("Ofertas actualizadas: %(count)d") % {'count': offer_count})

        if alert_error:
            message_parts.append(_("Alertas: %(msg)s") % {'msg': alert_error})
        else:
            message_parts.append(_("Alertas actualizadas: %(count)d") % {'count': alert_count})

        if card_error:
            message_parts.append(_("Validaciones tarjeta: %(msg)s") % {'msg': card_error})
        else:
            message_parts.append(_("Validaciones tarjeta actualizadas: %(count)d") % {'count': card_count})

        message_type = 'success' if not (offer_error or alert_error or card_error) else 'warning'
        title = _('Éxito') if message_type == 'success' else _('Aviso')
        final_message = "\n".join(message_parts)

        log_level = "INFO" if message_type == 'success' else "WARNING"
        self._log_db_lineas_oferta(log_level, final_message, "action_actualizar_lineas_oferta")
        _logger.log(logging.INFO if message_type == 'success' else logging.WARNING, final_message)

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {
                'title': title,
                'message': final_message,
                'type': message_type,
                'sticky': False,
            }
        }

    def action_actualizar_alertas(self):
        """
        Invoca el API de alertas legacy y sincroniza registros locales.
        """
        self.ensure_one()
        vat_raw = (self.partner_id.vat or "").strip()
        if not vat_raw:
            raise UserError(_('La oportunidad debe tener un CUIT/CUIL (VAT) configurado para consultar alertas.'))

        vat_cuit = self._format_vat_as_cuit(vat_raw)
        if not vat_cuit:
            raise UserError(_('El CUIT/CUIL debe tener 11 dígitos para consultar alertas.'))

        url = "http://sms.cooperativacredikot.com.ar/ServicioConsultas3_WS.aspx"
        headers = {
            'User-Agent': 'Request-Promise',
            'version': 'QUERY',
            'parametros': f"@QUERY=odooalertas;@clicuil='{vat_cuit}'",
            'Content-Type': 'application/json'
        }

        self._log_db_lineas_oferta("INFO", f"Sync alertas | CUIT={vat_cuit}", "action_actualizar_alertas")
        self._log_db_lineas_oferta("INFO", f"Headers alertas: {headers}", "action_actualizar_alertas")
        _logger.info("Iniciando sincronización de alertas para lead_id=%s cuit=%s", self.id, vat_cuit)
        _logger.info("Headers alertas: %s", headers)

        try:
            response = requests.post(url, headers=headers, data='', timeout=30)
            response.raise_for_status()
        except requests.RequestException as exc:
            msg = f"Error al invocar API de alertas: {exc}"
            self._log_db_lineas_oferta("ERROR", msg, "action_actualizar_alertas")
            raise UserError(_('No se pudo conectar con el API de alertas (%s).') % exc) from exc

        raw_text = (response.text or "").lstrip("\ufeff\r\n\t ")
        if not raw_text:
            msg = f"La respuesta del API de alertas llegó vacía. parametros={headers.get('parametros')}"
            self._log_db_lineas_oferta("ERROR", msg, "action_actualizar_alertas")
            raise UserError(_('El API de alertas respondió vacío (parametros=%(params)s).') % {'params': headers.get('parametros')})

        try:
            payload = response.json()
        except ValueError:
            try:
                payload = json.loads(raw_text)
            except Exception as exc:
                msg = f"Respuesta del API de alertas no es JSON válido: {exc}. parametros={headers.get('parametros')}"
                self._log_db_lineas_oferta("ERROR", msg, "action_actualizar_alertas")
                raise UserError(_('El API de alertas devolvió un formato inválido (parametros=%(params)s): %(err)s') % {
                    'params': headers.get('parametros'),
                    'err': exc,
                }) from exc

        data = payload.get('DATOS') if isinstance(payload, dict) else None
        if not isinstance(data, list):
            msg = f"El API de alertas no retornó la clave DATOS con una lista. parametros={headers.get('parametros')}"
            self._log_db_lineas_oferta("ERROR", msg, "action_actualizar_alertas")
            raise UserError(_('El API de alertas no devolvió datos válidos (parametros=%(params)s).') % {
                'params': headers.get('parametros'),
            })

        alert_env = self.env['cliente.alerta'].sudo()
        alert_env.search([('lead_id', '=', self.id)]).unlink()

        to_create = []
        for item in data:
            if not isinstance(item, dict):
                continue
            tipo = (
                item.get('TIPO')
                or item.get('Tipo')
                or item.get('tipo')
                or _('Alerta')
            )
            fecha_val = (
                item.get('FECHA')
                or item.get('Fecha')
                or item.get('fecha')
                or ""
            )
            fecha_date = self._parse_alert_date(fecha_val)
            if not fecha_date:
                self._log_db_lineas_oferta(
                    "WARNING",
                    f"No se pudo interpretar la fecha '{fecha_val}' en alerta VAT={vat_clean}. Se usa la fecha actual.",
                    "action_actualizar_alertas",
                )
                today_str = fields.Date.context_today(self)
                fecha_date = fields.Date.from_string(today_str) if isinstance(today_str, str) else today_str

            fecha_str = fields.Date.to_string(fecha_date)

            to_create.append({
                'lead_id': self.id,
                'vat': vat_cuit,
                'tipo': tipo,
                'fecha': fecha_str,
                'rec_importe_rechazado': float(item.get('recimprech') or 0.0),
                'rec_observaciones': item.get('recobs') or '',
            })

        if to_create:
            alert_env.create(to_create)

        self._invalidate_cache(['cliente_alerta_ids', 'cliente_alerta_count'])
        msg = f"Alertas sincronizadas: {len(to_create)} registros para CUIT {vat_cuit}"
        self._log_db_lineas_oferta("INFO", msg, "action_actualizar_alertas")
        _logger.info(msg)
        return len(to_create)

    def action_view_cliente_alertas(self):
        """
        Actualiza (si corresponde) y muestra las alertas del cliente.
        """
        self.ensure_one()
        if not self.env.context.get('skip_alert_sync'):
            try:
                self.with_context(skip_alert_sync=True).action_actualizar_alertas()
            except UserError:
                raise
            except Exception as exc:
                self._log_db_lineas_oferta(
                    "ERROR",
                    f"Error inesperado al actualizar alertas: {exc}",
                    "action_view_cliente_alertas",
                )
                raise

        action = self.env["ir.actions.actions"]._for_xml_id("lineas_oferta.action_cliente_alerta")
        action['domain'] = [('lead_id', '=', self.id)]
        raw_ctx = action.get('context') or {}
        if isinstance(raw_ctx, str):
            raw_ctx = safe_eval(raw_ctx, {'uid': self.env.uid})
        ctx = dict(raw_ctx)
        ctx.update({
            'default_lead_id': self.id,
            'default_vat': self.partner_id.vat or "",
        })
        action['context'] = ctx
        return action

    def _parse_alert_date(self, value):
        if not value:
            return False
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            candidate = value.strip()
            if not candidate:
                return False
            try:
                cleaned = candidate.replace("Z", "+00:00") if candidate.endswith("Z") else candidate
                return datetime.fromisoformat(cleaned).date()
            except ValueError:
                for pattern in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S"):
                    try:
                        return datetime.strptime(candidate, pattern).date()
                    except ValueError:
                        continue
        return False
    
    def action_view_lineas_oferta(self):
        """
        Abrir vista de líneas de oferta
        """
        self.ensure_one()
        action = self.env.ref('lineas_oferta.action_lineas_oferta', raise_if_not_found=False)
        if action:
            action = action.read()[0]
        else:
            action = {
                'name': _('Líneas de Oferta'),
                'type': 'ir.actions.act_window',
                'res_model': 'lineas.oferta',
                'view_mode': 'list,form',
            }
        action['domain'] = [('lead_id', '=', self.id)]
        action.setdefault('context', {})
        if isinstance(action['context'], str):
            action['context'] = safe_eval(action['context'], {'uid': self.env.uid})
        context = dict(action['context'] or {})
        context.update({'default_lead_id': self.id})
        action['context'] = context
        action['views'] = [
            (self.env.ref('lineas_oferta.view_lineas_oferta_tree').id, 'list'),
            (self.env.ref('lineas_oferta.view_lineas_oferta_form').id, 'form'),
        ]
        action['view_mode'] = 'list,form'
        return action
    
    def test_logging_function(self):
        """
        Método de prueba para verificar que el logging funciona
        """
        self.ensure_one()
        _logger.info("=== INICIANDO PRUEBA DE LOGGING ===")
        
        # Probar logging básico
        self._log_db_lineas_oferta("INFO", "Prueba de logging desde método test_logging_function", "test_logging_function")
        
        # Probar con diferentes niveles
        self._log_db_lineas_oferta("DEBUG", "Log de debug", "test_logging_function")
        self._log_db_lineas_oferta("WARNING", "Log de warning", "test_logging_function")
        self._log_db_lineas_oferta("ERROR", "Log de error", "test_logging_function")
        
        _logger.info("=== FIN PRUEBA DE LOGGING ===")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Prueba completada'),
                'message': _('Revisa ir.logging para ver los logs de prueba'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_open_referentes_kanban(self):
        self.ensure_one()
        action_ref = 'crm_contact_referents.action_referentes_kanban_for_partner'
        action = self.env.ref(action_ref, raise_if_not_found=False)
        if not action:
            raise UserError(_('No se encontró la acción: %s') % action_ref)
        action = action.read()[0]
        action['domain'] = [('partner_ids', 'in', [self.partner_id.id])]
        action.setdefault('context', {})
        if isinstance(action['context'], str):
            action['context'] = {}
        action['context'].update({
            'default_partner_ids': [(4, self.partner_id.id)],
        })
        return action
