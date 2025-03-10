from odoo import models, fields, api

class HrJointLeave(models.Model):
    _name = 'hr.joint.leave'
    _description = 'Joint Leave Records'

    name = fields.Char(string='Description', required=True)
    date_from = fields.Datetime(string='Date From', required=True)
    date_to = fields.Datetime(string='Date To', required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    state = fields.Selection([
        ('draft', 'To Process'),
        ('done', 'Processed'),
        ('cancel', 'Cancelled')
    ], string='Status', default='draft')
    amount = fields.Float(string='Deduction Amount', required=True)
    processed_in_payslip_id = fields.Many2one('hr.payslip', string='Processed in Payslip') 