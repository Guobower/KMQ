# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2013 Julius Network Solutions SARL <contact@julius.fr>
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

#from openerp.osv import orm, fields
from odoo import models, fields
import time
import logging

_logger = logging.getLogger('smsclient')

class ServerAction(models.Model):
    """
    Possibility to specify the SMS Gateway when configure this server action
    """
    _inherit = 'ir.actions.server'

    sms_server = fields.Many2one('sms.smsclient', 'SMS Server',
            help='Select the SMS Gateway configuration to use with this action')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
