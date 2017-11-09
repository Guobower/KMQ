import json
from lxml import etree
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.tools import float_is_zero, float_compare
from odoo.tools.misc import formatLang

from odoo.exceptions import UserError, RedirectWarning, ValidationError

import odoo.addons.decimal_precision as dp
import logging

_logger = logging.getLogger(__name__)

class BrandingMethod(models.Model):
	_name = "branding.method"
	_description = "Branding Method"
	
	name = fields.Char('Branding Method')
	active = fields.Boolean('Active',default=True)
	product_id = fields.Many2one('product.template','Product')

class ProductTemplate(models.Model):
	_inherit = 'product.template'

	def open_quatation_form(self):
		data = {}
		data['default_product_id'] = self.id
                view_id = self.env['ir.model.data'].get_object_reference('kt_kmq', 'online_quote_form')
                return {
                         'name':_("Online Quotation"),#Name You want to display on wizard
                         'view_mode': 'form',
                         'view_id': view_id[1],
                         'view_type': 'form',
                         'res_model': 'online.order.wizard',# With . Example sale.order
                         'type': 'ir.actions.act_window',
                         'target': 'new',
                         'context':data,
                       }

	branding_methods = fields.Many2many('branding.method','product_branding_method_rel','product_id','method_id',string='Branding Method')
	branding_locations = fields.Many2many('branding.location','product_branding_location_rel','product_id','location_id',string='Branding Location')
	color_variants = fields.Many2many('color.variants','product_color_variant_rel','product_id','color_id',string='Colours')
	size_variants = fields.Many2many('size.variants','product_size_variant_rel','product_id','size_id',string='Sizes') 

class BrandingLocation(models.Model):
        _name = "branding.location"
        _description = "Branding Location"

        name = fields.Char('Position')
        active = fields.Boolean('Active',default=True)
	product_id = fields.Many2one('product.template','Product')

class ColorVariants(models.Model):
        _name = 'color.variants'
        name = fields.Char('Name')
	product_id = fields.Many2one('product.template','Product')

class Sizevariants(models.Model):
        _name = 'size.variants'
        name = fields.Char('Name')
	product_id = fields.Many2one('product.template','Product')

class BrandingPrice(models.Model):
	_name = 'branding.price'

	product_id = fields.Many2one('product.template','Product')
	branding_method = fields.Many2one('branding.method','Branding Method')
	branding_location = fields.Many2one('branding.location','Branding Location')
	color_variant = fields.Many2one('color.variants','Colours')
	size_variant = fields.Many2one('size.variants','Sizes')
	min_qty = fields.Integer('Min Quantity')
	max_qty = fields.Integer('Max Quantity')
	setup_cost = fields.Float('Setup Cost')
	item_cost = fields.Float('Item Cost')
