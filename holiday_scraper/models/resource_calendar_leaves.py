from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResourceCalendarLeaves(models.Model):
    _inherit = 'resource.calendar.leaves'

    holiday_type = fields.Selection([
        ('national', 'Libur Nasional'),
        ('joint_leave', 'Cuti Bersama')
    ], string='Tipe Libur', default='national', required=True)
    
    is_mandatory = fields.Boolean(
        string='Wajib', 
        default=False,
        help="Jika dicentang, karyawan wajib mengambil cuti bersama ini"
    )
    
    def action_process_joint_leave(self):
        """Proses cuti bersama setelah diputuskan sebagai wajib"""
        self.ensure_one()
        if self.holiday_type != 'joint_leave':
            return
            
        employees = self.env['hr.employee'].search([
            ('resource_calendar_id', '=', self.calendar_id.id)
        ])
        
        for employee in employees:
            # Cek apakah sudah ada cuti untuk tanggal yang sama
            existing_leave = self.env['hr.leave'].search([
                ('employee_id', '=', employee.id),
                ('state', 'not in', ['refuse', 'cancel']),
                '|',
                '&', ('date_from', '<=', self.date_from), ('date_to', '>=', self.date_from),
                '&', ('date_from', '<=', self.date_to), ('date_to', '>=', self.date_to),
            ], limit=1)

            if existing_leave:
                raise ValidationError(_(
                    'Karyawan %s sudah memiliki cuti yang overlap pada periode ini: %s'
                ) % (employee.name, existing_leave.name))

            # Cek apakah karyawan memiliki alokasi cuti
            allocation = self.env['hr.leave.allocation'].search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'validate'),
                ('holiday_status_id.time_type', '=', 'leave'),
                ('date_from', '<=', self.date_from),
                '|',
                ('date_to', '=', False),
                ('date_to', '>=', self.date_to),
            ], limit=1)

            if allocation:
                # Cek sisa alokasi cuti
                remaining_leaves = allocation.number_of_days - allocation.leaves_taken
                if remaining_leaves < 1:
                    raise ValidationError(_(
                        'Karyawan %s tidak memiliki sisa cuti yang cukup'
                    ) % employee.name)

                # Jika ada alokasi dan cukup, kurangi jumlah hari dari alokasi
                try:
                    leave = self.env['hr.leave'].create({
                        'name': f'Cuti Bersama - {self.name}',
                        'employee_id': employee.id,
                        'holiday_status_id': allocation.holiday_status_id.id,
                        'date_from': self.date_from,
                        'date_to': self.date_to,
                        'number_of_days': 1,
                        'state': 'confirm',  # Set ke confirm dulu
                    })
                    # Validasi cuti
                    leave.action_validate()
                except Exception as e:
                    raise ValidationError(_(
                        'Gagal membuat cuti untuk %s: %s'
                    ) % (employee.name, str(e)))
            else:
                # Cek kontrak aktif karyawan
                contract = self.env['hr.contract'].search([
                    ('employee_id', '=', employee.id),
                    ('state', '=', 'open'),
                    ('date_start', '<=', self.date_from),
                    '|',
                    ('date_end', '=', False),
                    ('date_end', '>=', self.date_to),
                ], limit=1)

                if contract:
                    # Buat record cuti bersama yang harus dipotong
                    try:
                        self.env['hr.joint.leave'].create({
                            'name': f'Potongan Cuti Bersama - {self.name}',
                            'date_from': self.date_from,
                            'date_to': self.date_to,
                            'employee_id': employee.id,
                            'amount': -(contract.wage / 30),
                            'state': 'draft'
                        })
                    except Exception as e:
                        raise ValidationError(_(
                            'Gagal membuat potongan gaji untuk %s: %s'
                        ) % (employee.name, str(e)))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Sukses'),
                'message': _('Cuti bersama berhasil diproses'),
                'sticky': False,
                'type': 'success',
            }
        } 