# -*- coding: utf-8 -*-

from openerp import models, fields, api, _
from openerp.exceptions import UserError, ValidationError
import time

class AsistenteKardex(models.TransientModel):
    _name = 'kardex.asistente_kardex'
    _description = 'Kardex'

    def _default_producto(self):
        if len(self.env.context.get('active_ids', [])) > 0:
            return self.env.context.get('active_ids')[0]
        else:
            return None

    ubicacion_id = fields.Many2one("stock.location", string="Ubicacion", required=True)
    producto_id = fields.Many2one("product.product", string="Producto", required=True, default=_default_producto)
    fecha_desde = fields.Date(string="Fecha Inicial", required=True, default=lambda self: time.strftime('%Y-%m-01'))
    fecha_hasta = fields.Date(string="Fecha Final", required=True, default=lambda self: time.strftime('%Y-%m-%d'))

    def print_report(self):
        active_ids = self.env.context.get('active_ids', [])
        data = {
             'ids': active_ids,
             'model': self.env.context.get('active_model', 'ir.ui.menu'),
             'form': self.read()[0]
        }
        return self.env['report'].get_action([], 'kardex.reporte_kardex', data=data)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
