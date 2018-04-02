from odoo import api, fields, models, _
import time
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import Warning
import datetime

#import xlrd
import tempfile
import binascii

from odoo.exceptions import AccessError

import base64

import logging
_logger = logging.getLogger(__name__)

class InventoryCheckWizard(models.TransientModel):
    _name = "inventory.check.wizard"

    msg = fields.Text('Message')
    sale_id = fields.Many2one('sale.order', string='Order')



    @api.multi
    def check_and_confirm(self):
        """
        Confirm Sale order
        """
        if self.sale_id:
            self.sale_id.action_confirm()
        return {'type': 'ir.actions.act_window_close'}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: