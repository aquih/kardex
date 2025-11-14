# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import xlsxwriter
import base64
import io
import logging

class AsistenteKardex(models.TransientModel):
    _name = 'kardex.asistente_kardex'
    _description = 'Kardex'

    def _default_productos(self):
        active_ids = self._context.get('active_ids', [])
        if len(active_ids) > 0:
            products = self.env['product.product'].browse(active_ids)
            return [(4, x, False) for x in active_ids]
        else:
            return None

    ubicacion_ids = fields.Many2many("stock.location", string="Ubicacion", required=True)
    producto_ids = fields.Many2many("product.product", string="Productos", required=True, default=_default_productos)
    fecha_desde = fields.Datetime(string="Fecha Inicial", required=True)
    fecha_hasta = fields.Datetime(string="Fecha Final", required=True)
    archivo_excel = fields.Binary('Archivo excel')
    name_excel = fields.Char('Nombre archivo', default='kardex.xlsx', size=32)

    def print_report(self):
        data = {
             'ids': [],
             'model': 'kardex.asistente_kardex',
             'form': self.read()[0]
        }
        return self.env.ref('kardex.action_reporte_kardex').report_action(self, data=data)

    def reporte_excel(self):
        f = io.BytesIO()
        libro = xlsxwriter.Workbook(f)
        formato_fecha = libro.add_format({'num_format': 'dd/mm/yy'})
        formato_numero = libro.add_format({'num_format': '#,##0.00'})
        hoja = libro.add_worksheet('reporte')

        hoja.write(0, 0, 'KARDEX')

        total_final = 0
        y = 2
        for ubicacion in self.ubicacion_ids:
            for producto in self.producto_ids:
                resultado = self.env['report.kardex.reporte_kardex'].lineas(self.fecha_desde, self.fecha_hasta, producto.id, ubicacion.id)
                hoja.write(y, 0, 'Fecha desde:')
                hoja.write(y, 1, 'Fecha hasta:')
                hoja.write(y, 2, 'Ubicación:')
                hoja.write(y, 3, 'Producto:')
                y += 1
                hoja.write(y, 0, self.fecha_desde, formato_fecha)
                hoja.write(y, 1, self.fecha_hasta, formato_fecha)
                hoja.write(y, 2, ubicacion.display_name)
                hoja.write(y, 3, producto.display_name)
                y += 1
                hoja.write(y, 0, 'Inicial:')
                hoja.write(y, 1, 'Entradas:')
                hoja.write(y, 2, 'Salidas:')
                hoja.write(y, 3, 'Final:')
                y += 1
                hoja.write(y, 0, resultado['totales']['inicio'], formato_numero)
                hoja.write(y, 1, resultado['totales']['entrada'], formato_numero)
                hoja.write(y, 2, resultado['totales']['salida'], formato_numero)
                hoja.write(y, 3, resultado['totales']['inicio']+resultado['totales']['entrada']+resultado['totales']['salida'], formato_numero)
                y += 2
                hoja.write(y, 0, 'Fecha')
                hoja.write(y, 1, 'Documento')
                hoja.write(y, 2, 'Empresa')
                hoja.write(y, 3, 'Tipo')
                hoja.write(y, 4, 'UOM')
                hoja.write(y, 5, 'Lotes')
                hoja.write(y, 6, 'Entradas')
                hoja.write(y, 7, 'Salidas')
                hoja.write(y, 8, 'Final')
                hoja.write(y, 9, 'Costo')
                hoja.write(y, 10, 'Total')
                total_final += resultado['totales']['inicio']+resultado['totales']['entrada']+resultado['totales']['salida']
                y += 1
                for linea in resultado['lineas']:
                    hoja.write(y, 0, linea['fecha'], formato_fecha)
                    hoja.write(y, 1, linea['documento'])
                    hoja.write(y, 2, linea['empresa'])
                    hoja.write(y, 3, linea['tipo'])
                    hoja.write(y, 4, linea['unidad_medida'])
                    hoja.write(y, 5, linea['lotes'])
                    hoja.write(y, 6, linea['entrada'], formato_numero)
                    hoja.write(y, 7, linea['salida'], formato_numero)
                    hoja.write(y, 8, linea['saldo'], formato_numero)
                    hoja.write(y, 9, linea['costo'], formato_numero)
                    hoja.write(y, 10, linea['total'], formato_numero)
                    y += 1
                y += 1

        hoja.write(y, 0, 'Total de todas las ubicaciones')
        hoja.write(y, 1, total_final, formato_numero)

        libro.close()
        archivo = base64.b64encode(f.getvalue())
        self.write({'archivo_excel':archivo, 'name_excel':'kardex.xlsx'})

        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'kardex.asistente_kardex',
            'res_id': self.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
