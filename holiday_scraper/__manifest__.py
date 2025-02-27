{
    'name': 'Holiday Scraper',
    'version': '16.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Import public holidays from publicholidays.co.id',
    'description': """
        This module imports Indonesian public holidays from publicholidays.co.id
        and creates resource calendar leaves automatically.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['base', 'resource'],
    'data': [
        'security/ir.model.access.csv',
        'views/holiday_scraper_views.xml',
    ],
    'external_dependencies': {
        'python': ['requests', 'beautifulsoup4'],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
} 