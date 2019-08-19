# -*- coding: utf-8 -*-

from odoo import api, models
import logging

class ReporteKardex(models.AbstractModel):
    _name = 'report.kardex.reporte_kardex'

    def inicial(self, datos):
        self.env.cr.execute("select sum(qty_in) as entrada, sum(qty_out) as salida, product_id \
            from ( \
               select sum(product_qty) as qty_in, 0 as qty_out, product_id \
               from stock_move \
               where state = 'done' and product_id = %s and location_dest_id = %s and date <= %s \
               group by product_id \
               union \
               select 0 as qty_in, sum(product_qty) as qty_out, product_id \
               from stock_move \
               where state = 'done' and product_id = %s and  location_id = %s and date <= %s \
               group by product_id \
            ) movimientos\
            group by product_id",
            (datos['producto_id'], datos['ubicacion_id'], datos['fecha_desde'], datos['producto_id'], datos['ubicacion_id'], datos['fecha_desde']))
        lineas = self.env.cr.dictfetchall()

        total = 0
        for l in lineas:
            total += l['entrada'] - l['salida']

        return total

    def lineas(self, datos, product_id):
        totales = {}
        totales['entrada'] = 0
        totales['salida'] = 0
        totales['inicio'] = 0

        producto = self.env['product.product'].browse([product_id])
        dict = {'producto_id': producto.id, 
                'ubicacion_id': datos['ubicacion_id'][0], 
                'fecha_desde': datos['fecha_desde']
               }

        totales['inicio'] = self.inicial(dict)

        saldo = totales['inicio']
        lineas = []
        for m in self.env['stock.move'].search([('product_id','=',producto.id), ('date','>=',datos['fecha_desde']), ('date','<=',datos['fecha_hasta']), ('state','=','done'), '|', ('location_id','=',datos['ubicacion_id'][0]), ('location_dest_id','=',datos['ubicacion_id'][0])], order = 'date'):
            detalle = {
                'empresa':'-',
                'unidad_medida': m.product_id.uom_id.name,
                'fecha': m.date,
                'entrada': 0,
                'salida': 0,
                'saldo':saldo
            }

            if m.picking_id:
                detalle['documento'] = m.picking_id.name
                if m.picking_id.partner_id:
                    detalle['empresa'] = m.picking_id.partner_id.name

            else:
                detalle['documento'] = m.name

            if m.location_dest_id.id == datos['ubicacion_id'][0]:
                detalle['tipo'] = 'Ingreso'
                detalle['entrada'] = m.product_qty
                totales['entrada'] += m.product_qty
            elif m.location_id.id == datos['ubicacion_id'][0]:
                detalle['tipo'] = 'Salida'
                detalle['salida'] = -m.product_qty
                totales['salida'] -= m.product_qty

            saldo += detalle['entrada']+detalle['salida']
            detalle['saldo'] = saldo

            costo = m.product_id.get_history_price(m.company_id.id, date=m.date)
            detalle['costo'] = costo

            lineas.append(detalle)

        return {'producto': producto.name, 'lineas': lineas, 'totales': totales}

    @api.model
    def get_report_values(self, docids, data=None):
        self.model = self.env.context.get('active_model')
        docs = self.env[self.model].browse(self.env.context.get('active_ids', []))

        return  {
            'doc_ids': self.ids,
            'doc_model': self.model,
            'data': data['form'],
            'docs': docs,
            'lineas': self.lineas,
        }
    
    @api.model
    def _get_report_values(self, docids, data=None):
        self.model = self.env.context.get('active_model')
        docs = self.env[self.model].browse(self.env.context.get('active_ids', []))

        return  {
            'doc_ids': self.ids,
            'doc_model': self.model,
            'data': data['form'],
            'docs': docs,
            'lineas': self.lineas,
        }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
