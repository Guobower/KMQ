# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2009-Today OpenERP SA (<http://www.openerp.com>).
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

{
    'name' : 'payu.com payment Acquirer',
    'version' : '1.0',
    'depends' : ['payment','website_sale'],
    'author' : 'KTree',
    'category': 'Hidden',
    'summary':"Payment Acquirer: payu Implementation",
    'description': """
    payu Payment Acquirer
    """,
    'website': 'http://www.strategicdimensions.co.za',
    'data': [
	'views/payu_template.xml',
	'data/payu_data.xml',
	'views/payu.xml',
	'views/payment_acquirer.xml',
        'views/emailtemplate_view.xml'
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'images': [],
}
