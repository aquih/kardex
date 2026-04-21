{
    'name' : 'Kardex',
    'version' : '2.0',
    'category': 'Inventory/Inventory',
    'description': """Modulo para reporte de kardex""",
    'author': 'aquíH',
    'website': 'http://www.aquih.com/',
    'depends' : [ 'stock_account' ],
    'data' : [
        'report/reporte_kardex_views.xml',
        'wizard/product_product_reporte_kardex_views.xml',
        'security/ir.model.access.csv',
    ],
    'license': 'Other OSI approved licence',
    'installable': True,
}
