# ============================================
# models/lineas_oferta.py
# ============================================
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import json
import logging

_logger = logging.getLogger(__name__)


class LineasOferta(models.Model):
    _name = 'lineas.oferta'
    _description = 'Líneas de Oferta'
    _rec_name = 'display_name'
    _order = 'rie_ped_rpta_lin_r_capital desc, rie_ped_id, rie_ped_rpta_lin_r_ren'
    
    # Clave primaria compuesta
    rie_ped_id = fields.Integer(
        string='ID Pedido',
        required=True,
        readonly=True
    )
    
    rie_ped_rpta_lin_r_ren = fields.Integer(
        string='Renglón',
        required=True,
        readonly=True
    )
    
    # Relación con CRM Lead
    lead_id = fields.Many2one(
        'crm.lead',
        string='Oportunidad',
        required=True,
        ondelete='cascade',
        readonly=True,
        index=True
    )
    
    # Campos de datos
    rie_ped_rpta_lin_r_auditor = fields.Datetime(
        string='Fecha Auditor',
        readonly=True
    )
    
    rie_ped_rpta_lin_r_lin_cred = fields.Integer(
        string='Línea Crédito',
        readonly=True
    )
    
    rie_ped_rpta_lin_r_lin_cred_des = fields.Text(
        string='Descripción Línea Crédito',
        readonly=True
    )
    
    rie_ped_rpta_lin_r_tasa = fields.Float(
        string='Tasa',
        digits=(12, 4),
        readonly=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        related='lead_id.company_id.currency_id',
        store=True,
        readonly=True
    )

    rie_ped_rpta_lin_r_capital = fields.Monetary(
        string='Capital',
        currency_field='currency_id',
        readonly=True
    )
    
    rie_ped_rpta_lin_r_capital_en_mano = fields.Monetary(
        string='Capital en Mano',
        currency_field='currency_id',
        readonly=True
    )
    
    rie_ped_rpta_lin_r_capital_neto_ren = fields.Monetary(
        string='Capital Neto Ren',
        currency_field='currency_id',
        readonly=True
    )
    
    rie_ped_rpta_lin_r_cuotas = fields.Integer(
        string='Cuotas',
        readonly=True
    )
    
    rie_ped_rpta_lin_r_imp_cuota = fields.Monetary(
        string='Importe Cuota',
        currency_field='currency_id',
        readonly=True
    )
    
    rie_ped_rpta_lin_r_lin_cred_ren = fields.Integer(
        string='Línea Crédito Ren',
        readonly=True
    )
    
    rie_ped_rpta_lin_r_seleccion = fields.Selection([
        ('S', 'Oferta Seleccionada'),
        ('N', 'Oferta No Seleccionada')
    ], string='Selección', default='N', required=True)

    is_selected = fields.Boolean(
        string='Seleccionada',
        default=False
    )
    
    rie_ped_rpta_lin_r_rima_id_des = fields.Text(
        string='Descripción RIMA',
        readonly=True
    )
    
    rie_ped_rpta_lin_r_tir = fields.Float(
        string='TIR',
        digits=(12, 4),
        readonly=True
    )
    
    rie_ped_rpta_lin_r_tea = fields.Float(
        string='TEA',
        digits=(12, 4),
        readonly=True
    )
    
    rie_ped_rpta_lin_r_tem = fields.Float(
        string='TEM',
        digits=(12, 4),
        readonly=True
    )
    
    rie_ped_rpta_lin_r_servicio = fields.Monetary(
        string='Servicio',
        currency_field='currency_id',
        readonly=True
    )
    
    rie_ped_rpta_lin_r_gastos = fields.Monetary(
        string='Gastos',
        currency_field='currency_id',
        readonly=True
    )
    
    # Campo computado para mostrar nombre
    display_name = fields.Char(
        string='Nombre',
        compute='_compute_display_name',
        store=True
    )
    
    @api.depends('rie_ped_id', 'rie_ped_rpta_lin_r_ren')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"Oferta {record.rie_ped_id}-{record.rie_ped_rpta_lin_r_ren}"

    @api.onchange('is_selected')
    def _onchange_is_selected(self):
        """
        Mantener la exclusividad en modo edición (por ejemplo dentro del O2M)
        antes de guardar los cambios.
        """
        for record in self:
            if not record.lead_id:
                continue
            if record.is_selected:
                record.rie_ped_rpta_lin_r_seleccion = 'S'
                siblings = record.lead_id.lineas_oferta_ids - record
                for sibling in siblings:
                    if sibling.is_selected:
                        sibling.is_selected = False
                        sibling.rie_ped_rpta_lin_r_seleccion = 'N'
            else:
                record.rie_ped_rpta_lin_r_seleccion = 'N'

    # Restricción de unicidad para clave primaria compuesta
    _sql_constraints = [
        ('unique_linea_oferta', 
         'unique(rie_ped_id, rie_ped_rpta_lin_r_ren)',
         'Ya existe una línea de oferta con este ID y Renglón!')
    ]
    
    @api.constrains('rie_ped_rpta_lin_r_seleccion')
    def _check_single_selection(self):
        """
        Garantizar que solo quede una oferta seleccionada por oportunidad.
        Si otra oferta ya estaba marcada, se desmarca automáticamente.
        """
        for record in self:
            if record.rie_ped_rpta_lin_r_seleccion == 'S' and record.lead_id:
                self._reset_other_selected_offers_by_lead(record.lead_id.id, exclude_ids=[record.id])

    def _normalize_selection_vals(self, vals):
        normalized = vals.copy()
        if 'is_selected' in normalized:
            is_selected_value = bool(normalized['is_selected'])
            normalized['is_selected'] = is_selected_value
            normalized['rie_ped_rpta_lin_r_seleccion'] = 'S' if is_selected_value else 'N'
        elif 'rie_ped_rpta_lin_r_seleccion' in normalized:
            normalized['is_selected'] = normalized['rie_ped_rpta_lin_r_seleccion'] == 'S'
        return normalized

    def _reset_other_selected_offers_by_lead(self, lead_id, exclude_ids=None):
        if not lead_id:
            return
        domain = [
            ('lead_id', '=', lead_id),
            ('rie_ped_rpta_lin_r_seleccion', '=', 'S'),
        ]
        if exclude_ids:
            domain.append(('id', 'not in', exclude_ids))
        other_lines = self.search(domain)
        if other_lines:
            other_lines.write({
                'is_selected': False,
                'rie_ped_rpta_lin_r_seleccion': 'N'
            })

    @api.model_create_multi
    def create(self, vals_list):
        normalized_vals = []
        leads_to_reset = set()
        selected_seen_per_lead = {}

        for vals in vals_list:
            normalized = self._normalize_selection_vals(vals)
            lead_id = normalized.get('lead_id')
            if normalized.get('is_selected') and lead_id:
                leads_to_reset.add(lead_id)
                if selected_seen_per_lead.get(lead_id):
                    # Solo una oferta puede quedar seleccionada; las adicionales se marcan como no seleccionadas
                    normalized['is_selected'] = False
                    normalized['rie_ped_rpta_lin_r_seleccion'] = 'N'
                else:
                    selected_seen_per_lead[lead_id] = True
            normalized_vals.append(normalized)

        records = super(LineasOferta, self).create(normalized_vals)

        for lead_id in leads_to_reset:
            new_selected = records.filtered(lambda r: r.lead_id.id == lead_id and r.rie_ped_rpta_lin_r_seleccion == 'S')
            self.env['lineas.oferta']._reset_other_selected_offers_by_lead(
                lead_id,
                exclude_ids=new_selected.ids
            )
            for line in new_selected:
                line._apply_selected_offer_values_to_lead()
        return records

    def write(self, vals):
        """
        Sobrescribir write para permitir solo edición del campo selección
        """
        normalized_vals = self._normalize_selection_vals(vals)

        # Permitir actualizaciones completas cuando se ejecuta con sudo() (desde API)
        if self.env.su:
            if normalized_vals.get('rie_ped_rpta_lin_r_seleccion') == 'S':
                processed_leads = set()
                for record in self:
                    lead_id = record.lead_id.id
                    if lead_id and lead_id not in processed_leads:
                        self._reset_other_selected_offers_by_lead(lead_id, exclude_ids=self.ids)
                        processed_leads.add(lead_id)
            return super(LineasOferta, self).write(normalized_vals)

        if normalized_vals.get('rie_ped_rpta_lin_r_seleccion') == 'S':
            processed_leads = set()
            for record in self:
                lead_id = record.lead_id.id
                if lead_id and lead_id not in processed_leads:
                    self._reset_other_selected_offers_by_lead(lead_id, exclude_ids=self.ids)
                    processed_leads.add(lead_id)
        
        # Para usuarios normales, solo permitir cambio de selección y campos del sistema
        allowed_fields = {
            'rie_ped_rpta_lin_r_seleccion',
            'is_selected',
            '__last_update',
            'write_date',
            'write_uid'
        }
        if not set(normalized_vals.keys()).issubset(allowed_fields):
            raise UserError(_('Solo puede modificar el campo de Selección'))
        result = super(LineasOferta, self).write(normalized_vals)
        if normalized_vals.get('is_selected') or normalized_vals.get('rie_ped_rpta_lin_r_seleccion'):
            for record in self:
                if record.is_selected and record.lead_id:
                    record._apply_selected_offer_values_to_lead()
        return result

    def action_toggle_selection(self):
        """
        Alternar selección desde la interfaz (botón). Guarda inmediatamente
        y refresca la vista para reflejar los cambios en todas las filas.
        """
        self.ensure_one()
        new_state = not self.is_selected
        self.write({'is_selected': new_state})
        if new_state and self.lead_id:
            self._apply_selected_offer_values_to_lead()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def _apply_selected_offer_values_to_lead(self):
        """Actualizar campos de la oportunidad con datos de la oferta seleccionada."""
        self.ensure_one()
        if not self.lead_id:
            return
        values = {}
        if self.rie_ped_rpta_lin_r_capital:
            values['expected_revenue'] = self.rie_ped_rpta_lin_r_capital
        if self.rie_ped_rpta_lin_r_cuotas:
            values['x_studio_cant_cuotas'] = self.rie_ped_rpta_lin_r_cuotas
        if self.rie_ped_rpta_lin_r_imp_cuota:
            values['x_studio_monto_cuotas'] = self.rie_ped_rpta_lin_r_imp_cuota
        if values:
            self.lead_id.write(values)
