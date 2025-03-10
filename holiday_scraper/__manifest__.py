{
    'name': 'Holiday Scraper',
    'version': '16.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Import public holidays from publicholidays.co.id',
    'description': """
        This module imports Indonesian public holidays from publicholidays.co.id
        and creates resource calendar leaves automatically.
        Handles both national holidays and joint leave days differently.
        Supports automatic salary deductions for joint leave days.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'resource',
        'hr',
        'hr_holidays',
        'sh_hr_payroll',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/salary_rule_data.xml',
        'views/holiday_scraper_views.xml',
        'views/resource_calendar_leaves_views.xml',
    ],
    'external_dependencies': {
        'python': ['requests', 'beautifulsoup4'],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
} 