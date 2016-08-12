# -*- coding: utf-8 -*-

from openerp.osv import osv, fields
import time
import xlwt
import base64

class kardex_asistente(osv.osv_memory):
    _name = 'kardex.asistente'
    _description = 'Kardex de SBG'
    _columns = {
        'producto': fields.many2one('product.product', 'Producto'),
        'ubicacion': fields.many2one('stock.location', 'Ubicacion', required=True),
        'fecha_inicio': fields.date('Inicio', required=True),
        'fecha_fin': fields.date('Fin', required=True),
        'archivo': fields.binary('Archivo'),
    }

    def _revisar_producto(self, cr, uid, context=None):
        if 'active_id' in context:
            if 'active_model' in context and context['active_model'] == 'product.product':
                return context['active_id']
        return None

    _defaults = {
         'producto': _revisar_producto,
         'fecha_inicio': lambda *a: time.strftime('%Y-%m-01'),
    }

    def lineas(self, cr, uid, datos, context=None):

        context = context or {}

        totales = {}
        totales['entrada'] = 0
        totales['salida'] = 0
        totales['inicio'] = 0

        movimientos_ids = self.pool.get('stock.move').search(cr, uid, [('product_id','=',datos.producto.id), ('date','>=',datos.fecha_inicio), ('date','<=',datos.fecha_fin), ('state','=','done'), '|', ('location_id','=',datos.ubicacion.id), ('location_dest_id','=',datos.ubicacion.id)], order = 'date', context=context)

        context.update({'location': datos.ubicacion.id, 'to_date': datos.fecha_inicio})
        producto = self.pool.get('product.product').browse(cr, uid, datos.producto.id, context=context)
        totales['inicio'] = producto.qty_available

        saldo = totales['inicio']
        lineas = []
        for m in self.pool.get('stock.move').browse(cr, uid, movimientos_ids, context=context):

            linea = {'empresa':'', 'fecha': m.date, 'entrada': 0, 'salida': 0, 'saldo':saldo}

            if m.picking_id:

                linea['documento'] = m.picking_id.name
                if m.picking_id.partner_id:
                    linea['empresa'] = m.picking_id.partner_id.name
                else:
                    linea['empresa'] = '-'
                if m.picking_id.type == 'in':
                    linea['tipo'] = 'Ingreso'
                    linea['entrada'] = m.product_qty
                    totales['entrada'] += m.product_qty
                elif m.picking_id.type == 'out':
                    linea['tipo'] = 'Salida'
                    linea['salida'] = -m.product_qty
                    totales['salida'] -= m.product_qty
                elif m.picking_id.type == 'internal':
                    linea['tipo'] = 'Traslado'
                    if m.location_dest_id.id == datos.ubicacion.id:
                        linea['entrada'] = m.product_qty
                        totales['entrada'] += m.product_qty
                    elif m.location_id.id == datos.ubicacion.id:
                        linea['salida'] = -m.product_qty
                        totales['salida'] -= m.product_qty

            else:
                linea['documento'] = m.name
                linea['tipo'] = 'Ajuste'
                if m.location_dest_id.id == datos.ubicacion.id:
                    linea['entrada'] = m.product_qty
                    totales['entrada'] += m.product_qty
                elif m.location_id.id == datos.ubicacion.id:
                    linea['salida'] = -m.product_qty
                    totales['salida'] -= m.product_qty

            saldo += linea['entrada']+linea['salida']
            linea['saldo'] = saldo

            costo = m.product_id.standard_price

            historic_obj = self.pool.get('product.historic.cost')
            if historic_obj:

                costo_ids = self.pool.get('product.historic.cost').search(cr, uid, [('product_id', '=', m.product_id.id),('name', '<=', m.date)],limit=1,order='name desc', context=context)

                for costo_id in costo_ids:
                    costo = self.pool.get('product.historic.cost').browse(cr, uid, costo_id, context=context)

            linea['costo'] = costo

            lineas.append(linea)

        return {'lineas': lineas, 'totales': totales}

    def reporte(self, cr, uid, ids, data, context=None):
        return {'type':'ir.actions.report.xml', 'report_name':'kardex'}

    def excel(self, cr, uid, ids, context=None):
        libro = xlwt.Workbook()
        hoja = libro.add_sheet('reporte')
        num_linea = 0

        for a in self.browse(cr, uid, ids):
            result = self.lineas(cr, uid, a, context=context)
            hoja.write(num_linea, 0, a.producto.default_code)
            hoja.write(num_linea, 1, a.producto.name)
            hoja.write(num_linea, 2, a.fecha_inicio)
            hoja.write(num_linea, 3, a.fecha_fin)
            hoja.write(num_linea, 4, a.ubicacion.name)
            num_linea += 1
            hoja.write(num_linea, 0, result['totales']['inicio'])
            hoja.write(num_linea, 1, result['totales']['entrada'])
            hoja.write(num_linea, 2, result['totales']['salida'])
            hoja.write(num_linea, 3, result['totales']['inicio']+result['totales']['entrada']+result['totales']['salida'])
            for l in result['lineas']:
                num_linea += 1
                hoja.write(num_linea, 0, l['fecha'])
                hoja.write(num_linea, 1, l['documento'])
                hoja.write(num_linea, 2, l['empresa'])
                hoja.write(num_linea, 3, l['tipo'])
                hoja.write(num_linea, 4, l['entrada'])
                hoja.write(num_linea, 5, l['salida'])
                hoja.write(num_linea, 6, l['saldo'])
                hoja.write(num_linea, 7, l['costo'])
                hoja.write(num_linea, 8, l['saldo']*l['costo'])

            num_linea += 2

        libro.save('/tmp/libro.xls')
        f = open('/tmp/libro.xls', 'rb')
        datos = base64.b64encode(f.read())
        self.write(cr, uid, ids, {'archivo':datos})

        return True

    def excel_resumen(self, cr, uid, ids, context=None):
        libro = xlwt.Workbook()
        hoja = libro.add_sheet('reporte')
        num_linea = 0

        context = context or {}

        for a in self.browse(cr, uid, ids):

            cr.execute("select sum(qty_in) as entrada, sum(qty_out) as salida, product_id, product_product.default_code, product_template.name as name \
                from ( \
                   select sum(product_qty) as qty_in, 0 as qty_out, product_id, product_uom \
                   from stock_move \
                   where state = 'done' and location_dest_id = %s and date between %s and %s \
                   group by product_id, product_uom \
                   union \
                   select 0 as qty_in, sum(product_qty) as qty_out, product_id, product_uom \
                   from stock_move \
                   where state = 'done' and location_id = %s and date between %s and %s \
                   group by product_id, product_uom \
                ) movimientos join product_product on (product_product.id = movimientos.product_id) \
                join product_template on (product_product.product_tmpl_id = product_template.id) \
                join product_uom on (movimientos.product_uom = product_uom.id) \
                group by product_id, product_product.default_code, product_template.name",
                (a.ubicacion.id, a.fecha_inicio, a.fecha_fin, a.ubicacion.id, a.fecha_inicio + ' 00:00:01', a.fecha_fin + ' 23:59:59'))
            lineas = cr.dictfetchall()

            hoja.write(num_linea, 0, a.fecha_inicio)
            hoja.write(num_linea, 1, a.fecha_fin)
            hoja.write(num_linea, 2, a.ubicacion.name)
            num_linea += 1
            hoja.write(num_linea, 0, 'Codigo')
            hoja.write(num_linea, 1, 'Nombre')
            hoja.write(num_linea, 2, 'Inicio')
            hoja.write(num_linea, 3, 'Entradas')
            hoja.write(num_linea, 4, 'Salidas')
            hoja.write(num_linea, 5, 'Existencias')

            for l in lineas:
                num_linea += 1
                context.update({ 'location': a.ubicacion.id, 'to_date': a.fecha_inicio })
                producto = self.pool.get('product.product').browse(cr, uid, datos.producto.id, context=context)
                inicio = producto.qty_available
                hoja.write(num_linea, 0, l['default_code'])
                hoja.write(num_linea, 1, l['name'])
                hoja.write(num_linea, 2, inicio)
                hoja.write(num_linea, 3, l['entrada'])
                hoja.write(num_linea, 4, l['salida'])
                hoja.write(num_linea, 5, inicio+l['entrada']-l['salida'])

        libro.save('/tmp/libro.xls')
        f = open('/tmp/libro.xls', 'rb')
        datos = base64.b64encode(f.read())
        self.write(cr, uid, ids, {'archivo':datos})

        return True

kardex_asistente()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
