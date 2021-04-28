# -*- encoding: utf-8 -*-

{
    'name' : 'Kardex',
    'version' : '1.1',
    'category': 'Operations/Inventory',
    'description': """Modulo para reporte de kardex""",
    'author': 'aquíH',
    'website': 'http://aquih.com/',
    'depends' : [ 'stock_account' ],
    'data' : [
        'views/report.xml',
        'views/reporte_kardex.xml',
        'views/report_stockinventory.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
}
