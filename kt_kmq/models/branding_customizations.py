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
    _name = 'branding.method'
    _description = "Branding Method"

    name = fields.Char('Branding Method')
    active = fields.Boolean('Active',default=True)
    product_id = fields.Many2one('product.template','Product Template')
    product_product_id = fields.Many2one('product.product','Product', required=True)

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        ''' Adds domain upon branding method according to selected Product's Branding prices in Sale order line form '''
        args = args or []
        recs = self.browse()

        if self.env.context.get('product'):
            product = self.env['product.product'].browse(self.env.context.get('product'))
            branding_price_ids = self.env['branding.price'].search([('product_id', '=', product.product_tmpl_id.id)])
            methods = []
            for data in branding_price_ids:
                methods.append(data.branding_method.id)

            recs = self.search([('id', 'in', methods)] + args, limit=limit)
        if not recs:
            recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()


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
    branding_pricing = fields.One2many('branding.price','product_id',string='Branding Pricing')
#     branding_methods = fields.Many2many('branding.method','product_branding_method_rel','product_id','method_id',string='Branding Method')
# 	branding_locations = fields.Many2many('branding.location','product_branding_location_rel','product_id','location_id',string='Branding Location')
# 	color_variants = fields.Many2many('color.variants','product_color_variant_rel','product_id','color_id',string='Colours')
# 	size_variants = fields.Many2many('size.variants','product_size_variant_rel','product_id','size_id',string='Sizes') 

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
    branding_method_name = fields.Char('Branding Method Name')
    branding_location = fields.Many2one('branding.location','Branding Location')
    color_variant = fields.Many2one('color.variants','Colours')
    size_variant = fields.Many2one('size.variants','Sizes')
    min_qty = fields.Integer('Min Quantity')
    max_qty = fields.Integer('Max Quantity')
    setup_cost = fields.Float('Setup Cost')
    item_cost = fields.Float('Item Cost')
    rerun_setup_cost = fields.Float('Rerun Setup Cost')

    @api.onchange('branding_method')
    def onchange_method(self):
        for line in self:
            if self.branding_method:
                line.branding_method_name = self.branding_method.name
        
