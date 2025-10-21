from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    loan_installment_number = fields.Integer(string="Número de Cuota", default=0)
    loan_installment_due_date = fields.Date(string="Fecha de Vencimiento")
    loan_installment_paid = fields.Boolean(string="Cuota Pagada", default=False)
    loan_installment_paid_date = fields.Date(string="Fecha de Pago")
