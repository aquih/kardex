# -*- encoding: utf-8 -*-

{
    'name' : 'Kardex',
    'version' : '1.3',
    'category': 'Inventory/Inventory',
    'description': """Modulo para reporte de kardex""",
    'author': 'aquíH',
    'website': 'http://www.aquih.com/',
    'depends' : [ 'stock_account' ],
    'data' : [
        'views/reporte_kardex_views.xml',
        'wizard/asistente_kardex_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
}
