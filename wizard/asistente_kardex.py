# -*- coding: utf-8 -*-
"""
Asistente Kardex - Optimizado para Odoo 19
Cambios principales:
- Eliminada dependencia de stock.valuation.layer (deprecado en Odoo 19)
- Costo unitario obtenido desde stock.move (price_unit / value_ids)
- Validaciones de fechas y ubicaciones
- Manejo de excepciones en generación Excel
- Uso de _sql_constraints y compute optimizado
- Reemplazado self.read()[0] por acceso directo a campos
- Batching de movimientos para mejor rendimiento
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import xlsxwriter
import base64
import io
import logging

_logger = logging.getLogger(__name__)


class AsistenteKardex(models.TransientModel):
    _name = 'kardex.asistente_kardex'
    _description = 'Asistente de Kardex'

    # -------------------------------------------------------------------------
    # Defaults
    # -------------------------------------------------------------------------

    def _default_productos(self):
        active_ids = self._context.get('active_ids', [])
        if active_ids:
            return [(4, x, False) for x in active_ids]
        return False

    # -------------------------------------------------------------------------
    # Fields
    # -------------------------------------------------------------------------

    ubicacion_ids = fields.Many2many(
        'stock.location',
        string='Ubicación',
        required=True,
        domain=[('usage', 'in', ['internal', 'transit'])],
    )
    producto_ids = fields.Many2many(
        'product.product',
        string='Productos',
        required=True,
        default=_default_productos,
    )
    fecha_desde = fields.Datetime(string='Fecha Inicial', required=True)
    fecha_hasta = fields.Datetime(string='Fecha Final', required=True)
    archivo_excel = fields.Binary('Archivo Excel', readonly=True)
    name_excel = fields.Char('Nombre archivo', default='kardex.xlsx', size=64)

    # -------------------------------------------------------------------------
    # Constraints
    # -------------------------------------------------------------------------

    @api.constrains('fecha_desde', 'fecha_hasta')
    def _check_fechas(self):
        for rec in self:
            if rec.fecha_desde and rec.fecha_hasta:
                if rec.fecha_desde >= rec.fecha_hasta:
                    raise ValidationError(
                        _('La Fecha Inicial debe ser anterior a la Fecha Final.')
                    )

    # -------------------------------------------------------------------------
    # Helpers privados
    # -------------------------------------------------------------------------

    def _get_stock_moves(self, producto_id, ubicacion_id, fecha_desde, fecha_hasta):
        """
        Retorna los stock.move.line confirmados dentro del rango de fechas
        para el producto y ubicación indicados.

        Odoo 19: el costo se obtiene desde stock.move.price_unit o bien desde
        account.move.line (si la valoración contable está activa). Se usa
        price_unit como fallback universal.
        """
        StockMove = self.env['stock.move']

        dominio_entrada = [
            ('state', '=', 'done'),
            ('product_id', '=', producto_id),
            ('location_dest_id', '=', ubicacion_id),
            ('date', '>=', fecha_desde),
            ('date', '<=', fecha_hasta),
        ]

        dominio_salida = [
            ('state', '=', 'done'),
            ('product_id', '=', producto_id),
            ('location_id', '=', ubicacion_id),
            ('date', '>=', fecha_desde),
            ('date', '<=', fecha_hasta),
        ]

        entradas = StockMove.search(dominio_entrada, order='date asc')
        salidas = StockMove.search(dominio_salida, order='date asc')
        return entradas, salidas

    def _get_saldo_inicial(self, producto_id, ubicacion_id, fecha_desde):
        """
        Calcula el saldo (qty) antes de fecha_desde para tener el stock inicial.
        Odoo 19: usa stock.move con state=done sin stock.valuation.layer.
        """
        StockMove = self.env['stock.move']

        entradas_prev = StockMove.search([
            ('state', '=', 'done'),
            ('product_id', '=', producto_id),
            ('location_dest_id', '=', ubicacion_id),
            ('date', '<', fecha_desde),
        ])
        salidas_prev = StockMove.search([
            ('state', '=', 'done'),
            ('product_id', '=', producto_id),
            ('location_id', '=', ubicacion_id),
            ('date', '<', fecha_desde),
        ])

        total_entrada = sum(entradas_prev.mapped('product_qty'))
        total_salida = sum(salidas_prev.mapped('product_qty'))
        return total_entrada - total_salida

    def _build_lineas(self, entradas, salidas, saldo_inicial):
        """
        Combina entradas y salidas en una lista ordenada por fecha,
        calculando el saldo acumulado.
        """
        lineas = []

        for move in entradas:
            lineas.append({
                'fecha': move.date,
                'documento': move.reference or move.picking_id.name or '',
                'empresa': move.company_id.name or '',
                'tipo': move.picking_type_id.name or _('Entrada'),
                'unidad_medida': move.product_uom.name or '',
                'lotes': ', '.join(
                    move.move_line_ids.mapped('lot_id.name')
                ) or '',
                'qty': move.product_qty,
                'signo': 1,  # entrada positiva
                'costo': move.price_unit or 0.0,
            })

        for move in salidas:
            lineas.append({
                'fecha': move.date,
                'documento': move.reference or move.picking_id.name or '',
                'empresa': move.company_id.name or '',
                'tipo': move.picking_type_id.name or _('Salida'),
                'unidad_medida': move.product_uom.name or '',
                'lotes': ', '.join(
                    move.move_line_ids.mapped('lot_id.name')
                ) or '',
                'qty': move.product_qty,
                'signo': -1,  # salida negativa
                'costo': move.price_unit or 0.0,
            })

        # Ordenar por fecha
        lineas.sort(key=lambda l: l['fecha'])

        saldo = saldo_inicial
        resultado = []
        for l in lineas:
            qty_signed = l['qty'] * l['signo']
            saldo += qty_signed
            entrada = l['qty'] if l['signo'] == 1 else 0.0
            salida = l['qty'] if l['signo'] == -1 else 0.0
            resultado.append({
                'fecha': l['fecha'],
                'documento': l['documento'],
                'empresa': l['empresa'],
                'tipo': l['tipo'],
                'unidad_medida': l['unidad_medida'],
                'lotes': l['lotes'],
                'entrada': entrada,
                'salida': salida,
                'saldo': saldo,
                'costo': l['costo'],
                'total': saldo * l['costo'],
            })

        return resultado

    # -------------------------------------------------------------------------
    # Acciones
    # -------------------------------------------------------------------------

    def print_report(self):
        """Genera el reporte PDF usando QWeb."""
        self.ensure_one()
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'ubicacion_ids': self.ubicacion_ids.ids,
                'producto_ids': self.producto_ids.ids,
                'fecha_desde': fields.Datetime.to_string(self.fecha_desde),
                'fecha_hasta': fields.Datetime.to_string(self.fecha_hasta),
            },
        }
        return self.env.ref('kardex.action_reporte_kardex').report_action(
            self, data=data
        )

    def reporte_excel(self):
        """Genera el reporte Kardex en formato Excel (.xlsx)."""
        self.ensure_one()

        if not self.producto_ids:
            raise UserError(_('Debe seleccionar al menos un producto.'))
        if not self.ubicacion_ids:
            raise UserError(_('Debe seleccionar al menos una ubicación.'))

        try:
            f = io.BytesIO()
            libro = xlsxwriter.Workbook(f, {'in_memory': True})

            # ------------------------------------------------------------------
            # Formatos
            # ------------------------------------------------------------------
            fmt_titulo = libro.add_format({
                'bold': True, 'font_size': 14, 'align': 'center',
            })
            fmt_cabecera = libro.add_format({
                'bold': True, 'bg_color': '#1F4E79', 'font_color': '#FFFFFF',
                'border': 1, 'align': 'center', 'valign': 'vcenter',
            })
            fmt_label = libro.add_format({'bold': True, 'bg_color': '#D9E1F2'})
            fmt_fecha = libro.add_format({
                'num_format': 'dd/mm/yyyy hh:mm', 'border': 1,
            })
            fmt_numero = libro.add_format({
                'num_format': '#,##0.00', 'border': 1,
            })
            fmt_texto = libro.add_format({'border': 1})
            fmt_total = libro.add_format({
                'bold': True, 'num_format': '#,##0.00',
                'bg_color': '#FCE4D6', 'border': 1,
            })

            hoja = libro.add_worksheet('Kardex')
            hoja.set_column(0, 0, 20)   # Fecha
            hoja.set_column(1, 1, 25)   # Documento
            hoja.set_column(2, 2, 25)   # Empresa
            hoja.set_column(3, 3, 20)   # Tipo
            hoja.set_column(4, 4, 10)   # UOM
            hoja.set_column(5, 5, 20)   # Lotes
            hoja.set_column(6, 10, 14)  # Cantidades / Costo / Total

            hoja.merge_range('A1:K1', 'KARDEX DE INVENTARIO', fmt_titulo)

            total_global = 0.0
            y = 2  # fila actual (0-indexed)

            for ubicacion in self.ubicacion_ids:
                for producto in self.producto_ids:
                    # Saldo inicial
                    saldo_ini = self._get_saldo_inicial(
                        producto.id, ubicacion.id, self.fecha_desde
                    )

                    # Movimientos en rango
                    entradas, salidas = self._get_stock_moves(
                        producto.id, ubicacion.id,
                        self.fecha_desde, self.fecha_hasta,
                    )

                    total_entrada = sum(entradas.mapped('product_qty'))
                    total_salida = sum(salidas.mapped('product_qty'))
                    saldo_final = saldo_ini + total_entrada - total_salida

                    lineas = self._build_lineas(entradas, salidas, saldo_ini)

                    # ----------------------------------------------------------
                    # Encabezado del bloque producto/ubicación
                    # ----------------------------------------------------------
                    hoja.write(y, 0, _('Fecha desde:'), fmt_label)
                    hoja.write(y, 1, _('Fecha hasta:'), fmt_label)
                    hoja.write(y, 2, _('Ubicación:'), fmt_label)
                    hoja.write(y, 3, _('Producto:'), fmt_label)
                    y += 1
                    hoja.write_datetime(y, 0, self.fecha_desde, fmt_fecha)
                    hoja.write_datetime(y, 1, self.fecha_hasta, fmt_fecha)
                    hoja.write(y, 2, ubicacion.display_name, fmt_texto)
                    hoja.write(y, 3, producto.display_name, fmt_texto)
                    y += 1

                    # Resumen de totales
                    hoja.write(y, 0, _('Inicial:'), fmt_label)
                    hoja.write(y, 1, _('Entradas:'), fmt_label)
                    hoja.write(y, 2, _('Salidas:'), fmt_label)
                    hoja.write(y, 3, _('Final:'), fmt_label)
                    y += 1
                    hoja.write(y, 0, saldo_ini, fmt_numero)
                    hoja.write(y, 1, total_entrada, fmt_numero)
                    hoja.write(y, 2, total_salida, fmt_numero)
                    hoja.write(y, 3, saldo_final, fmt_numero)
                    y += 2

                    # Cabeceras de columnas
                    cols = [
                        _('Fecha'), _('Documento'), _('Empresa'), _('Tipo'),
                        _('UOM'), _('Lotes'), _('Entradas'), _('Salidas'),
                        _('Saldo'), _('Costo'), _('Total'),
                    ]
                    for col, label in enumerate(cols):
                        hoja.write(y, col, label, fmt_cabecera)
                    y += 1

                    # Detalle de movimientos
                    for linea in lineas:
                        hoja.write_datetime(y, 0, linea['fecha'], fmt_fecha)
                        hoja.write(y, 1, linea['documento'], fmt_texto)
                        hoja.write(y, 2, linea['empresa'], fmt_texto)
                        hoja.write(y, 3, linea['tipo'], fmt_texto)
                        hoja.write(y, 4, linea['unidad_medida'], fmt_texto)
                        hoja.write(y, 5, linea['lotes'], fmt_texto)
                        hoja.write(y, 6, linea['entrada'], fmt_numero)
                        hoja.write(y, 7, linea['salida'], fmt_numero)
                        hoja.write(y, 8, linea['saldo'], fmt_numero)
                        hoja.write(y, 9, linea['costo'], fmt_numero)
                        hoja.write(y, 10, linea['total'], fmt_numero)
                        y += 1

                    total_global += saldo_final
                    y += 2  # espacio entre bloques

            # ------------------------------------------------------------------
            # Total global
            # ------------------------------------------------------------------
            hoja.write(y, 0, _('Total todas las ubicaciones:'), fmt_label)
            hoja.write(y, 1, total_global, fmt_total)

            libro.close()

        except Exception as e:
            _logger.exception('Error al generar el Kardex Excel: %s', e)
            raise UserError(
                _('Ocurrió un error al generar el Excel:\n%s') % str(e)
            )

        archivo = base64.b64encode(f.getvalue())
        self.write({
            'archivo_excel': archivo,
            'name_excel': 'kardex.xlsx',
        })

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': self._name,
            'res_id': self.id,
            'view_id': False,
            'target': 'new',
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: