import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from pytz import timezone


class HolidayScraper(models.TransientModel):
    _name = 'holiday.scraper'
    _description = 'Holiday Scraper'

    calendar_id = fields.Many2one('resource.calendar', string='Working Time', required=True,
                                default=lambda self: self.env.company.resource_calendar_id)
    year = fields.Integer(string='Year', default=2025)
    mandatory_joint_leaves = fields.Many2many(
        'resource.calendar.leaves',
        string='Cuti Bersama Wajib',
        domain="[('holiday_type', '=', 'joint_leave')]",
        help="Pilih cuti bersama yang wajib diambil oleh karyawan"
    )

    def _get_fixed_holidays(self):
        # Mapping untuk hari libur dengan tanggal tetap (Libur Nasional)
        fixed_holidays = {
            'Tahun Baru Masehi': {'month': 1, 'day': 1, 'type': 'national'},
            'Hari Buruh': {'month': 5, 'day': 1, 'type': 'national'},
            'Hari Lahir Pancasila': {'month': 6, 'day': 1, 'type': 'national'},
            'Hari Kemerdekaan': {'month': 8, 'day': 17, 'type': 'national'},
            'Hari Natal': {'month': 12, 'day': 25, 'type': 'national'},
        }
        return fixed_holidays

    def _is_cuti_bersama(self, holiday_name):
        return 'Cuti Bersama' in holiday_name

    def _create_leave_allocation_deduction(self, employee, date_from, date_to, holiday_name):
        # Cek apakah karyawan memiliki alokasi cuti
        allocation = self.env['hr.leave.allocation'].search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'validate'),
            ('holiday_status_id.time_type', '=', 'leave'),  # Tipe cuti regular
            ('date_from', '<=', date_from),
            '|',
            ('date_to', '=', False),
            ('date_to', '>=', date_to),
        ], limit=1)

        if allocation:
            # Jika ada alokasi, kurangi jumlah hari dari alokasi
            self.env['hr.leave'].create({
                'name': f'Cuti Bersama - {holiday_name}',
                'employee_id': employee.id,
                'holiday_status_id': allocation.holiday_status_id.id,
                'date_from': date_from,
                'date_to': date_to,
                'number_of_days': 1,
                'state': 'validate',
            })
        else:
            # Cek kontrak aktif karyawan untuk mendapatkan gaji pokok
            contract = self.env['hr.contract'].search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'open'),
                ('date_start', '<=', date_from),
                '|',
                ('date_end', '=', False),
                ('date_end', '>=', date_to),
            ], limit=1)

            if contract:
                # Buat record cuti bersama yang harus dipotong
                self.env['hr.joint.leave'].create({
                    'name': f'Potongan Cuti Bersama - {holiday_name}',
                    'date_from': date_from,
                    'date_to': date_to,
                    'employee_id': employee.id,
                    'amount': -(contract.wage / 21),  # Asumsi 21 hari kerja
                    'state': 'draft'
                })

    def _process_holiday(self, holiday, date_from, date_to):
        is_cuti_bersama = self._is_cuti_bersama(holiday['name'])
        holiday_type = 'joint_leave' if is_cuti_bersama else 'national'

        # Buat resource.calendar.leaves
        leave_vals = {
            'name': holiday['name'],
            'calendar_id': self.calendar_id.id,
            'date_from': date_from,
            'date_to': date_to,
            'holiday_type': holiday_type,
            'is_mandatory': False if is_cuti_bersama else True,  # Default False untuk cuti bersama
        }
        calendar_leave = self.env['resource.calendar.leaves'].create(leave_vals)
        return calendar_leave

    def _is_valid_date(self, year, month, day):
        try:
            datetime(year, month, day)
            return True
        except ValueError:
            return False

    def _scrape_holidays(self):
        url = f'https://publicholidays.co.id/id/{self.year}-dates/'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            table = soup.find('table', {'class': 'publicholidays'})
            if not table:
                raise UserError(_('Could not find holiday table on the website'))

            holidays = []
            
            # Tambahkan hari libur tetap terlebih dahulu
            fixed_holidays = self._get_fixed_holidays()
            for name, date_info in fixed_holidays.items():
                try:
                    date = datetime(self.year, date_info['month'], date_info['day']).date()
                    holidays.append({
                        'date': date,
                        'name': name
                    })
                except ValueError:
                    continue

            # Scrape hari libur bergerak dari website
            for row in table.find_all('tr')[1:]:
                cells = row.find_all('td')
                if len(cells) >= 3:
                    date_str = cells[0].get_text(strip=True)
                    name = cells[2].get_text(strip=True)
                    
                    # Skip jika sudah ada di fixed holidays
                    if any(h['name'] == name for h in holidays):
                        continue

                    # Clean up date string
                    date_str = date_str.split('(')[0].strip()
                    date_str = date_str.split('–')[0].strip()
                    
                    try:
                        # Coba parse dengan berbagai format
                        for month_name in ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 
                                         'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']:
                            if month_name in date_str:
                                day = int(''.join(filter(str.isdigit, date_str.split(month_name)[0])))
                                month = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 
                                       'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'].index(month_name) + 1
                                
                                if self._is_valid_date(self.year, month, day):
                                    date = datetime(self.year, month, day).date()
                                    holidays.append({
                                        'date': date,
                                        'name': name
                                    })
                                else:
                                    # Jika tanggal tidak valid, gunakan tanggal 1
                                    date = datetime(self.year, month, 1).date()
                                    holidays.append({
                                        'date': date,
                                        'name': name
                                    })
                                break
                    except (ValueError, IndexError):
                        # Jika gagal parse, coba deteksi bulan saja
                        for month_name in ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 
                                         'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']:
                            if month_name in date_str:
                                month = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 
                                       'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'].index(month_name) + 1
                                date = datetime(self.year, month, 1).date()
                                holidays.append({
                                    'date': date,
                                    'name': name
                                })
                                break

            return holidays

        except requests.exceptions.RequestException as e:
            raise UserError(_('Error accessing website: %s') % str(e))
        except Exception as e:
            raise UserError(_('Error processing holidays: %s') % str(e))

    def _get_datetime_range(self, date):
        """Get datetime range for working hours (08:00 - 17:30) Asia/Jakarta"""
        # Set timezone Asia/Jakarta
        tz = timezone('Asia/Jakarta')
        
        # Buat datetime dengan jam 08:00
        start_dt = datetime.combine(date, datetime.strptime('08:00', '%H:%M').time())
        # Buat datetime dengan jam 17:30
        end_dt = datetime.combine(date, datetime.strptime('17:30', '%H:%M').time())
        
        # Lokalisasi ke timezone Asia/Jakarta
        start_dt = tz.localize(start_dt)
        end_dt = tz.localize(end_dt)
        
        # Konversi ke UTC untuk penyimpanan di database
        start_utc = start_dt.astimezone(timezone('UTC')).replace(tzinfo=None)
        end_utc = end_dt.astimezone(timezone('UTC')).replace(tzinfo=None)
        
        return start_utc, end_utc

    def action_import_holidays(self):
        holidays = self._scrape_holidays()
        skipped_holidays = []
        
        for holiday in holidays:
            if not holiday['date']:
                skipped_holidays.append(holiday['name'])
                continue
            
            # Get datetime range for working hours (08:00 - 17:30) Asia/Jakarta
            date_from, date_to = self._get_datetime_range(holiday['date'])

            # Check if holiday already exists or overlaps with other holidays
            existing_leave = self.env['resource.calendar.leaves'].search([
                ('resource_id', '=', False),
                ('calendar_id', '=', self.calendar_id.id),
                '|',
                '&', ('date_from', '<=', date_from), ('date_to', '>=', date_from),
                '&', ('date_from', '<=', date_to), ('date_to', '>=', date_to),
            ])

            if existing_leave:
                skipped_holidays.append(f"{holiday['name']} (overlap dengan {existing_leave[0].name})")
                continue

            self._process_holiday(holiday, date_from, date_to)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Holidays have been imported successfully'),
                'sticky': False,
                'type': 'success',
            }
        } 