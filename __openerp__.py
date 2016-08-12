# -*- encoding: utf-8 -*-

#
# Este es el modulo para toda la configuracion y funcionalidad del proyecto
# de Tubelite.
#
# Status 1.0 - tested on Open ERP 6.0.3
#

{
    'name' : 'kardex',
    'version' : '1.0',
    'category': 'Custom',
    'description': """Modulo para reporte de kardex""",
    'author': 'Rodrigo Fernandez',
    'website': 'http://solucionesprisma.com/',
    'depends' : ['stock'],
    'init_xml' : [ ],
    'demo_xml' : [ ],
    'update_xml' : ['kardex.xml'],
    'installable': True,
    'certificate': '',
}
