# -*- coding: utf-8 -*-

from odoo import api, models
import datetime
import logging

class ReporteKardex(models.AbstractModel):
    _name = 'report.kardex.reporte_kardex'
    _description = 'Kardex'

    def inicial(self, fecha_desde, producto_id, ubicacion_id):
        self.env.cr.execute("select sum(qty_in) as entrada, sum(qty_out) as salida, product_id \
            from ( \
               select sum(quantity) as qty_in, 0 as qty_out, product_id \
               from stock_move_line \
               where state = 'done' and product_id = %s and location_dest_id = %s and date <= %s \
               group by product_id \
               union \
               select 0 as qty_in, sum(quantity) as qty_out, product_id \
               from stock_move_line \
               where state = 'done' and product_id = %s and location_id = %s and date <= %s \
               group by product_id \
            ) movimientos\
            group by product_id",
            (producto_id, ubicacion_id, fecha_desde, producto_id, ubicacion_id, fecha_desde))
        lineas = self.env.cr.dictfetchall()

        total = 0
        for l in lineas:
            total += l['entrada'] - l['salida']

        return total

    def costos_a_fecha(self, producto, fecha):
        # Es necesario usar SQL por qué el ORM no funciona. Al parecer, cuando se usa la condicion de 'date', tal
        # tal vez por ser una vista, no toma en cuenta el costo que debería.
        self.env.cr.execute("select * from stock_avco_report where product_id = %s and date <= %s order by date desc limit 1",
            (producto.id, fecha))
        lineas = self.env.cr.dictfetchall()
        return lineas

    def lineas(self, fecha_desde, fecha_hasta, producto_id, ubicacion_id):
        totales = {}
        totales['entrada'] = 0
        totales['salida'] = 0
        totales['inicio'] = 0

        producto = self.env['product.product'].browse(producto_id)
        ubicacion = self.env['stock.location'].browse(ubicacion_id)

        totales['inicio'] = self.inicial(fecha_desde, producto_id, ubicacion_id)

        saldo = totales['inicio']
        lineas = []
        for m in self.env['stock.move.line'].search([('product_id','=',producto.id), ('date','>=',fecha_desde), ('date','<=',fecha_hasta), ('state','=','done'), '|', ('location_id','=',ubicacion.id), ('location_dest_id','=',ubicacion.id)], order = 'date'):
            detalle = {
                'empresa':'-',
                'unidad_medida': m.product_id.uom_id.name,
                'lotes': ', '.join(m.lot_id.mapped('name')),
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

            if m.location_dest_id.id == ubicacion.id:
                detalle['tipo'] = 'Ingreso'
                detalle['entrada'] = m.quantity
                totales['entrada'] += m.quantity
            elif m.location_id.id == ubicacion.id:
                detalle['tipo'] = 'Salida'
                detalle['salida'] = -m.quantity
                totales['salida'] -= m.quantity

            saldo += detalle['entrada'] + detalle['salida']
            detalle['saldo'] = saldo
            detalle['costo'] = 0
            detalle['total'] = 0

            if self.env.user.has_group('sales_team.group_sale_manager') or self.env.user.has_group('account.group_account_user'):
                for costo in self.costos_a_fecha(m.product_id, m.date):
                    detalle['costo'] = self.env.company.currency_id.round(costo['value'])
                    detalle['total'] = self.env.company.currency_id.round(costo['value'] * saldo)

            lineas.append(detalle)

        return {'producto': producto.display_name, 'ubicacion': ubicacion.display_name, 'lineas': lineas, 'totales': totales}
    
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
            'mostrar_costo': self.env.user.has_group('sales_team.group_sale_manager') or self.env.user.has_group('account.group_account_user'),
        }

