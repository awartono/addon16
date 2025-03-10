from odoo import models, fields, api
from datetime import datetime
from odoo.http import request


class UserSessions(models.Model):
    _name = 'user.sessions'
    _description = 'User Sessions'
    _order = 'login_time desc'

    user_id = fields.Many2one('res.users', string='User', required=True)
    login_time = fields.Datetime('Login Time', default=fields.Datetime.now)
    last_activity = fields.Datetime('Last Activity', default=fields.Datetime.now)
    ip_address = fields.Char('IP Address')
    status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive')
    ], default='active', string='Status')

    def init(self):
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS user_sessions_user_id_status_idx 
            ON user_sessions (user_id, status)
        """)

class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        result = super(IrHttp, self).session_info()
        if self.env.user.id:
            self.env['user.sessions'].sudo().create({
                'user_id': self.env.user.id,
                'ip_address': request.httprequest.remote_addr,
            })
        return result 