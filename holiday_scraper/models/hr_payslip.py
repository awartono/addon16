from odoo import models, api

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def get_inputs(self, contracts, date_from, date_to):
        res = super(HrPayslip, self).get_inputs(contracts, date_from, date_to)
        
        # Cari cuti bersama yang belum diproses
        for contract in contracts:
            joint_leaves = self.env['hr.joint.leave'].search([
                ('employee_id', '=', contract.employee_id.id),
                ('date_from', '>=', date_from),
                ('date_to', '<=', date_to)
            ])

            if joint_leaves:
                # Hitung total potongan
                total_deduction = sum(joint_leaves.mapped('amount'))
                
                # Tambahkan input untuk potongan cuti bersama
                res.append({
                    'name': 'Potongan Cuti Bersama',
                    'code': 'CUTBER',
                    'amount': total_deduction,
                    'contract_id': contract.id,
                })
                
                # Update status cuti bersama
                # joint_leaves.write({
                #     'state': 'done',
                #     'processed_in_payslip_id': self.id
                # })
        
        return res 