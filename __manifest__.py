{
    'name': 'KIO Multi-Company Stock Transfer',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Manage stock transfers between different companies',
    'description': """
        KIO Multi-Company Stock Transfer
        =================================
        Manage stock transfers between two different companies inside the same Odoo database.
    """,
    'author': 'KIO',
    'website': '',
    'license': 'LGPL-3',
    'depends': [
        'stock',
        'mail',
    ],
    'data': [
        'security/multicompany_transfer_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/multicompany_transfer_route_views.xml',
        'views/multicompany_stock_transfer_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
