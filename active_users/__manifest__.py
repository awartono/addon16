{
    'name': 'Active Users Tracking',
    'version': '1.0',
    'category': 'Tools',
    'summary': 'Track active users in Odoo',
    'description': """
        This module allows you to track active users in Odoo system.
        Shows login time, last activity and IP address.
    """,
    'author': 'Your Name',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/user_sessions_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
} 