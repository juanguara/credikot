from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    loan_state = fields.Selection(
        [
            ("VIG", "Vigente"),
            ("CAN", "Cancelado"),
        ],
        string="Estado del Préstamo",
        default="VIG",
        tracking=True,
    )
    loan_total_installments = fields.Integer(string="Total de Cuotas", default=0)
    loan_paid_installments = fields.Integer(string="Cuotas Pagas", default=0)
    loan_overdue_installments = fields.Integer(string="Cuotas en Mora", default=0)
    loan_settlement_date = fields.Date(string="Fecha de Liquidación")
    loan_last_payment_date = fields.Date(string="Fecha Último Pago")
    loan_signed_capital = fields.Monetary(string="Capital Firmado")
    loan_disbursed_capital = fields.Monetary(string="Capital Liquidado")
    loan_cancellation_balance = fields.Monetary(string="Saldo de Cancelación")
    loan_total_overdue_days = fields.Integer(string="Días Totales en Mora", default=0)
    loan_interest_mora = fields.Monetary(string="Intereses por Mora")
    loan_interest_punitory = fields.Monetary(string="Intereses Punitorios")
    loan_interest_compensatory = fields.Monetary(string="Intereses Compensatorios")
