# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
import datetime
from openerp.report import report_sxw
from openerp.osv import osv

class reporte_kardex(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(reporte_kardex, self).__init__(cr, uid, name, context)
        self.totales = {'entrada':0, 'salida':0, 'inicio': 0}
        self.localcontext.update( {
            'time': time,
            'datetime': datetime,
            'lineas': self.lineas,
            'totales': self.totales,
        })
        self.lineas = None
        self.context = context
        self.cr = cr

    def lineas(self, datos):
        result = self.pool.get('kardex.asistente').lineas(self.cr, self.uid, datos)
        self.totales['entrada'] = result['totales']['entrada']
        self.totales['salida'] = result['totales']['salida']
        self.totales['inicio'] = result['totales']['inicio']
        return result['lineas']

report_sxw.report_sxw('report.kardex', 'kardex.asistente', 'addons/kardex/reportes/kardex_reporte.rml', parser=reporte_kardex, header=False)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
