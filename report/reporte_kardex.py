# -*- coding: utf-8 -*-

from odoo import api, models
import datetime
import logging

class ReporteKardex(models.AbstractModel):
    _name = 'report.kardex.reporte_kardex'

    def inicial(self, datos):
        self.env.cr.execute("select sum(qty_in) as entrada, sum(qty_out) as salida, product_id \
            from ( \
               select sum(qty_done) as qty_in, 0 as qty_out, product_id \
               from stock_move_line \
               where state = 'done' and product_id = %s and location_dest_id = %s and date <= %s \
               group by product_id \
               union \
               select 0 as qty_in, sum(qty_done) as qty_out, product_id \
               from stock_move_line \
               where state = 'done' and product_id = %s and location_id = %s and date <= %s \
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
        dict = {
            'producto_id': producto.id, 
            'ubicacion_id': datos['ubicacion_id'][0], 
            'fecha_desde': datos['fecha_desde']
        }

        totales['inicio'] = self.inicial(dict)

        saldo = totales['inicio']
        lineas = []
        for m in self.env['stock.move.line'].search([('product_id','=',producto.id), ('date','>=',datos['fecha_desde']), ('date','<=',datos['fecha_hasta']), ('state','=','done'), '|', ('location_id','=',datos['ubicacion_id'][0]), ('location_dest_id','=',datos['ubicacion_id'][0])], order = 'date'):
            detalle = {
                'empresa':'-',
                'unidad_medida': m.product_id.uom_id.name,
                'fecha': m.date,
                'entrada': 0,
                'salida': 0,
                'saldo': saldo
            }

            if m.picking_id:
                detalle['documento'] = m.picking_id.name
                if m.picking_id.partner_id:
                    detalle['empresa'] = m.picking_id.partner_id.name

            else:
                detalle['documento'] = m.reference

            if m.location_dest_id.id == datos['ubicacion_id'][0]:
                detalle['tipo'] = 'Ingreso'
                detalle['entrada'] = m.qty_done
                totales['entrada'] += m.qty_done
            elif m.location_id.id == datos['ubicacion_id'][0]:
                detalle['tipo'] = 'Salida'
                detalle['salida'] = -m.qty_done
                totales['salida'] -= m.qty_done

            saldo += detalle['entrada'] + detalle['salida']
            detalle['saldo'] = saldo
            detalle['costo'] = 0
            detalle['total'] = 0

            if self.user_has_groups('sales_team.group_sale_manager,account.group_account_user'):
                grupos = self.env['stock.valuation.layer'].read_group([('product_id', '=', m.product_id.id), ('create_date', '<=', m.date+datetime.timedelta(seconds=2))], ['value:sum', 'quantity:sum'], ['product_id'])
                for grupo in grupos:
                    if (grupo['quantity'] != 0):
                        detalle['costo'] = self.env.company.currency_id.round(grupo['value']/grupo['quantity'])
                        detalle['total'] = self.env.company.currency_id.round(grupo['value']/grupo['quantity']*saldo)

            lineas.append(detalle)

        return {'producto': producto.name, 'lineas': lineas, 'totales': totales}
    
    @api.model
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_ids', []))

        return  {
            'doc_ids': self.ids,
            'doc_model': model,
            'data': data['form'],
            'docs': docs,
            'lineas': self.lineas,
            'mostrar_costo': self.user_has_groups('stock.group_stock_manager,sales_team.group_sale_manager,account.group_account_user'),
        }

