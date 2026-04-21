import logging
from odoo.upgrade import util

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    util.records.remove_view(cr, xml_id="kardex.kardex_asistente_kardex")
    util.records.remove_record(cr, "kardex.window_reporte_kardex")
    util.records.remove_record(cr, "kardex.action_reporte_kardex")
    util.records.remove_record(cr, "kardex.menu_asistente_kardex")

    _logger.info("Vistas viejas borradas")
