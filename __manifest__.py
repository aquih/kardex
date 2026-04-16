# -*- encoding: utf-8 -*-

{
    'name' : 'Kardex',
    'version' : '1.5',
    'category': 'Inventory/Inventory',
    'description': """Modulo para reporte de kardex""",
    'author': 'aquíH, gomezgleonardob',
    'website': 'http://www.aquih.com/',
    'depends' : [ 'stock_account' ],
    'data' : [
        'report/reporte_kardex_views.xml',
        'wizard/asistente_kardex_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
}
