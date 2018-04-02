from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
# from docutils.parsers import null
# from decorator import append


class ProductBrandingLines(models.Model):
    _name = 'product.branding.lines'

    @api.model
    def _get_branding_method_domain(self):
        for obj in self:
            if obj.product_id:
                branding_price_ids = self.env['branding.price'].search([('product_id', '=', obj.product_id.product_tmpl_id.id)])
                methods = []
                for data in branding_price_ids:
                    methods.append(data.branding_method.id)
                return [('id', 'in', methods)]
            else:
                return []


    branding_location = fields.Many2one('branding.location', 'Branding Location')
        # branding_method = fields.Many2one('branding.method',string='Branding Method',domain=_get_branding_method_domain)
    # branding_method = fields.Many2one('branding.method',string='Branding Method',domain=lambda self: self._get_branding_method_domain())
    # branding_method = fields.Many2one('branding.method',string='Branding Method',domain=_get_branding_method_domain)
    branding_method = fields.Many2one('branding.method', string='Branding Method')
    branding_method_name = fields.Char('Branding Method Name')
        # product_id = fields.Many2one('product.template','Product')
    product_id = fields.Many2one('product.product', 'Product')  # Jagadeesh
    color_variant = fields.Many2one('color.variants', 'Colours')
    size_variant = fields.Many2one('size.variants', 'Sizes')
    setup_cost = fields.Float('Setup Cost', digits=dp.get_precision('Branding Price'))
    item_cost = fields.Float('Cost/Item', digits=dp.get_precision('Branding Price'))
    total_cost = fields.Float('Total Cost', compute="get_brand_total", digits=dp.get_precision('Branding Price'))
#     total_cost = fields.Float('Total Cost')
    sale_order_id = fields.Many2one('sale.order', 'Online Order')
    sale_order_line_id = fields.Many2one('sale.order.line', 'Online Order')
    invoice_id = fields.Many2one('account.invoice', 'Invoice/Bill')
    colour_cost = fields.Float('Colour Change Cost')
    artwork_cost = fields.Float('Artwork Charge Cost')
    job_type = fields.Selection([('Normal', 'Normal'), ('Re-Run', 'Re-Run'), ('Special', 'Special'), ('Deadline', 'Deadline')], string="Job Type")
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')
# 

    @api.multi
    @api.depends('item_cost', 'setup_cost', 'colour_cost', 'artwork_cost')
    def get_brand_total(self):
        for branding in self:
            uom_qty = branding.sale_order_line_id and branding.sale_order_line_id.product_uom_qty or 0.0
            branding.total_cost = branding.setup_cost + branding.colour_cost + branding.artwork_cost + (branding.item_cost * uom_qty)

#     # Jagadeesh 
#     @api.multi
#     @api.onchange('branding_location')
#     def onchange_branding_location(self):
#          self.product_id = self.sale_order_line_id.product_id.id
#          self.sale_order_id = self.sale_order_line_id.order_id.id
    # Jagadeesh end


    @api.multi
    @api.onchange('setup_cost', 'item_cost', 'colour_cost', 'artwork_cost')
    def onchange_costs(self):
        for branding in self:
            uom_qty = branding.sale_order_line_id and branding.sale_order_line_id.product_uom_qty or 0.0
            branding.total_cost = branding.setup_cost + branding.colour_cost + branding.artwork_cost + (branding.item_cost * uom_qty)

#          self.total_cost = (self.sale_order_line_id.product_uom_qty * self.item_cost) + self.setup_cost
             # self.sale_order_id = self.sale_order_line_id.order_id.id


    # Jagadeesh JUN08 start
    @api.multi
    def _get_method_ids(self, product):
        for obj in self:
            if obj.product_id:
                branding_price_ids = self.env['branding.price'].search([('product_id', '=', obj.product_id.product_tmpl_id.id)])
                methods = []
                for data in branding_price_ids:
                    methods.append(data.branding_method.id)
                return methods
            else:
                return []

#     @api.multi
#     @api.onchange('product_id')
#     def onchnge_product_branding_method(self):
#         if self.product_id:
#             branding_price_ids = self.env['branding.price'].search([('product_id', '=', self.product_id.product_tmpl_id.id)])
#             methods = []
#             for data in branding_price_ids:
#                 methods.append(data.branding_method.id)
#             return {'domain':{'branding_method': [('id', 'in', methods)]}}

    @api.multi
    @api.onchange('branding_method')
    def onchange_branding_location(self):
        self.branding_method_name = self.branding_method.name or ''
        colors = []
        sizes = []
        if self.branding_method:
            branding_obj = self.env['branding.price'].search([('product_id', '=', self.product_id.product_tmpl_id.id), ('branding_method', '=', self.branding_method.id)])
            for data in branding_obj:
                colors.append(data.color_variant.id)
                sizes.append(data.size_variant.id)
        return {'domain':{'color_variant': [('id', 'in', list(set(colors)))], 'size_variant':[('id', 'in', list(set(sizes)))]}}

#     @api.onchange('branding_method', 'color_variant', 'size_variant', 'sale_order_line_id.product_uom_qty', 'sale_order_line_id.order_id.pricelist_id')
    @api.onchange('branding_method', 'color_variant', 'size_variant', 'sale_order_line_id')
    def onchange_branding_items(self):
        print"onchange_branding_items=========",self.sale_order_line_id
        if (self.branding_method and self.color_variant) or (self.branding_method and self.size_variant):
            pricelist = self.env['product.pricelist'].browse(self._context.get('pricelist'))
            job_type = self._context.get('job_type') or ''
            branding_price_ids = self.env['branding.price'].search([('branding_method', '=', self.branding_method.id), ('product_id', '=', self.product_id.product_tmpl_id.id), ('branding_location', '=', self.branding_location.id)])
            product_id = self.env['product.product'].search([('product_tmpl_id', '=', self.sale_order_line_id.product_id.id)])
            branding_price_ids_lst = []
            branding_price_ids_on_colors_lst = []
            branding_price_ids_on_size_lst = []
            if branding_price_ids:
                for rec in branding_price_ids:
                    branding_price_ids_lst.append(rec.id)
                branding_price_ids_on_colors = self.env['branding.price'].search([('id', 'in', branding_price_ids_lst), ('color_variant', '=', self.color_variant.id)])
                if branding_price_ids_on_colors and self.color_variant:
                    for rec in branding_price_ids_on_colors:
                        branding_price_ids_on_colors_lst.append(rec.id)
                    if branding_price_ids_on_colors_lst:
                        branding_price_ids_on_limits = self.env['branding.price'].search([('id', 'in', branding_price_ids_on_colors_lst), ('min_qty', '<=', self.sale_order_line_id.product_uom_qty), ('max_qty', '>=', self.sale_order_line_id.product_uom_qty)], limit=1)
                        if branding_price_ids_on_limits:
                                # for rec in branding_price_ids_on_limits:
                                if job_type == 'Re-Run':
                                    setup_cost = round(branding_price_ids_on_limits.rerun_setup_cost,2)
                                else:
                                    setup_cost = round(branding_price_ids_on_limits.setup_cost,2)
                                self.setup_cost = round((setup_cost * (1- (pricelist.percentage/100))),2) or 0.0
                                self.item_cost = round(branding_price_ids_on_limits.item_cost,2) or 0.0
#                                 self.total_cost = (self.sale_order_line_id.product_uom_qty * self.item_cost) + self.setup_cost + self.colour_cost + self.artwork_cost or 0.0
                branding_price_ids_on_size = self.env['branding.price'].search([('id', 'in', branding_price_ids_lst), ('size_variant', '=', self.size_variant.id)])
                if branding_price_ids_on_size and self.size_variant:
                    for rec in branding_price_ids_on_size:
                        branding_price_ids_on_size_lst.append(rec.id)
                    if branding_price_ids_on_size_lst:
                        branding_price_ids_on_limits = self.env['branding.price'].search([('id', 'in', branding_price_ids_on_size_lst), ('min_qty', '<=', self.sale_order_line_id.product_uom_qty), ('max_qty', '>=', self.sale_order_line_id.product_uom_qty)], limit=1)
                        if branding_price_ids_on_limits:
                            for rec in branding_price_ids_on_limits:
                                if job_type == 'Re-Run':
                                    setup_cost = round(rec.rerun_setup_cost,2)
                                else:
                                    setup_cost = rec.setup_cost
                                self.setup_cost = round((setup_cost * (1- (pricelist.percentage/100))),2) or 0.0
                                self.item_cost = round(rec.item_cost,2) or 0.0
#                 if self._context.get('sale'):
#                     return (setup_cost * (1- (pricelist.percentage/100))) or 0.0
#                                 self.total_cost = (self.sale_order_line_id.product_uom_qty * self.item_cost) + self.setup_cost + self.colour_cost + self.artwork_cost or 0.0

    @api.multi
    def write(self,vals):
        for brandingprice in self:
            if vals.get('product_id'):
                product = self.env['product.product'].browse(vals.get('product_id'))
            else:
                product = brandingprice.product_id

            if vals.get('sale_order_line_id'):
                order_line = brandingprice.env['sale.order.line'].browse(vals.get('sale_order_line_id'))
            else:
                order_line = brandingprice.sale_order_line_id

            if order_line.order_id:
#                 if vals.get('setup_cost') and order_line.order_id.pricelist_id and order_line.order_id.pricelist_id.percentage:
#                     setup_cost = vals.get('setup_cost') * (1 - (order_line.order_id.pricelist_id.percentage/100))
#                     vals.update({'setup_cost': setup_cost})
                domain = [('sale_order_line_id.order_id', '=', order_line.order_id.id)]
                price_domain = []
                if vals.get('color_variant'):
                    domain.append(('color_variant', '=', vals.get('color_variant')))
                    price_domain.append(('color_variant', '=', vals.get('color_variant')))
                elif brandingprice.color_variant:
                    domain.append(('color_variant', '=', brandingprice.color_variant.id))
                    price_domain.append(('color_variant', '=', brandingprice.color_variant.id))
                else:
                    domain.append(('color_variant', '=', False))
                    price_domain.append(('color_variant', '=', False))
                if vals.get('size_variant'):
                    domain.append(('size_variant', '=', vals.get('size_variant')))
                    price_domain.append(('size_variant', '=', vals.get('size_variant')))
                elif brandingprice.size_variant:
                    domain.append(('size_variant', '=', brandingprice.size_variant.id))
                    price_domain.append(('size_variant', '=', brandingprice.size_variant.id))
                else:
                    domain.append(('size_variant', '=', False))
                    price_domain.append(('size_variant', '=', False))
                if vals.get('branding_location'):
                    domain.append(('branding_location', '=', vals.get('branding_location')))
                    price_domain.append(('branding_location', '=', vals.get('branding_location')))
                elif brandingprice.branding_location:
                    domain.append(('branding_location', '=', brandingprice.branding_location.id))
                    price_domain.append(('branding_location', '=', brandingprice.branding_location.id))
                if vals.get('branding_method'):
                    domain.append(('branding_method', '=', vals.get('branding_method')))
                    price_domain.append(('branding_method', '=', vals.get('branding_method')))
                elif brandingprice.branding_method:
                    domain.append(('branding_method', '=', brandingprice.branding_method.id))
                    price_domain.append(('branding_method', '=', brandingprice.branding_method.id))
                if vals.get('product_id'):
                    product = self.env['product.product'].browse(vals.get('product_id'))
                elif brandingprice.product_id:
                    product = brandingprice.product_id
                repeat_lines = self.search(domain)
                make_this_setup_zero = False
                for line in repeat_lines:
                    if line.setup_cost and line.id != brandingprice.id and product.product_tmpl_id.id == line.product_id.product_tmpl_id.id:
                        make_this_setup_zero = True
                if len(repeat_lines.ids) > 1 and make_this_setup_zero:
                    uom_qty = vals.get('product_uom_qty') or order_line.product_uom_qty
                    colour_cost = vals.get('colour_cost') or brandingprice.colour_cost
                    artwork_cost = vals.get('artwork_cost') or brandingprice.artwork_cost
                    item_cost = vals.get('item_cost') or brandingprice.item_cost
                    vals.update({'setup_cost': 0.0})
#                     vals.update({'setup_cost': 0.0, 'total_cost': (uom_qty * item_cost) + colour_cost + artwork_cost})
            res = super(ProductBrandingLines,self).write(vals)

            if order_line.order_id:
                if not order_line.order_id.override_branding_pricing:
                    location = brandingprice.branding_location and '= ' + str(brandingprice.branding_location.id) or 'IS Null'
                    method = brandingprice.branding_method and '= ' + str(brandingprice.branding_method.id) or 'IS Null'
                    color_variant = brandingprice.color_variant and '= ' + str(brandingprice.color_variant.id) or 'IS Null'
                    size_variant = brandingprice.size_variant and '= ' + str(brandingprice.size_variant.id) or 'IS Null'
                    order_id = order_line.order_id and '= ' + str(order_line.order_id.id) or 'IS Null'
                    tmpl_id = product.product_tmpl_id and '= ' + str(product.product_tmpl_id.id) or 'IS Null'
    
                    query = """SELECT b.id,SUM(sl.product_uom_qty) 
                                FROM product_branding_lines b,sale_order_line sl 
                                WHERE b.branding_location %s AND 
                                b.branding_method %s AND 
                                b.color_variant %s AND 
                                b.size_variant %s AND 
                                b.sale_order_line_id in (SELECT id FROM sale_order_line WHERE order_id %s) AND 
                                sl.id in (SELECT id FROM sale_order_line WHERE order_id %s) AND 
                                b.product_id in (SELECT id FROM product_product WHERE product_tmpl_id %s) GROUP BY b.id"""% (location,method,color_variant, size_variant, order_id, order_id, tmpl_id,)
                    self.env.cr.execute(query)
                    quary_res = self.env.cr.fetchall()
                    if quary_res:
                        price_domain.append(('product_id', '=', product.product_tmpl_id.id))
                        price_domain.append(('min_qty', '<=', quary_res[0][1]))
                        price_domain.append(('max_qty', '>=', quary_res[0][1]))
                        branding_price_ids_on_limits = self.env['branding.price'].search(price_domain)
    
                        branding_line_ids = []
                        for query_vals in quary_res:
                            product_branding_line = brandingprice.browse(query_vals[0])
                            if branding_price_ids_on_limits:
                                if order_line.order_id.pricelist_id and order_line.order_id.pricelist_id.percentage:
                                    item_cost = round(branding_price_ids_on_limits.item_cost * (1 - (order_line.order_id.pricelist_id.percentage/100)),2)
    #                                 total_cost = (product_branding_line.sale_order_line_id.product_uom_qty * item_cost) + setup_cost + product_branding_line.colour_cost + product_branding_line.artwork_cost or 0.0
                                else:
                                    item_cost = round(branding_price_ids_on_limits.item_cost,2) or 0.0
    #                                 total_cost = (product_branding_line.sale_order_line_id.product_uom_qty * product_branding_line.item_cost) + setup_cost + product_branding_line.colour_cost + product_branding_line.artwork_cost or 0.0
                                self.env.cr.execute("""UPDATE product_branding_lines set item_cost=%s where id=%s"""% (item_cost,round(query_vals[0],2),))
                                uom_qty = order_line.product_uom_qty or 0.0
                                total_cost = round((product_branding_line.setup_cost + product_branding_line.colour_cost + product_branding_line.artwork_cost + (item_cost * uom_qty)),)
                                self.env.cr.execute("""UPDATE product_branding_lines set total_cost=%s where id=%s"""% (total_cost,round(query_vals[0],2),))
            return res

    @api.model
    def create(self,vals):
        if vals.get('item_cost'):
            vals.update({'item_cost': round(vals.get('item_cost'),2)})
        if vals.get('setup_cost'):
            vals.update({'setup_cost': round(vals.get('setup_cost'),2)})
        if vals.get('artwork_cost'):
            vals.update({'artwork_cost': round(vals.get('artwork_cost'),2)})
        if vals.get('colour_cost'):
            vals.update({'colour_cost': round(vals.get('colour_cost'),2)})
        product = self.env['product.product'].browse(vals.get('product_id'))
        order_line = self.env['sale.order.line'].browse(vals.get('sale_order_line_id'))
        if order_line.order_id:
#             if vals.get('setup_cost') and order_line.order_id.pricelist_id and order_line.order_id.pricelist_id.percentage:
#                 setup_cost = vals.get('setup_cost') * (1 - (order_line.order_id.pricelist_id.percentage/100))
#                 vals.update({'setup_cost': setup_cost})
            domain = [('sale_order_line_id.order_id', '=', order_line.order_id.id)]
            price_domain = []
            if vals.get('color_variant'):
                domain.append(('color_variant', '=', vals.get('color_variant')))
                price_domain.append(('color_variant', '=', vals.get('color_variant')))
            else:
                domain.append(('color_variant', '=', False))
                price_domain.append(('color_variant', '=', False))
            if vals.get('size_variant'):
                domain.append(('size_variant', '=', vals.get('size_variant')))
                price_domain.append(('size_variant', '=', vals.get('size_variant')))
            else:
                domain.append(('size_variant', '=', False))
                price_domain.append(('size_variant', '=', False))
            if vals.get('branding_location'):
                domain.append(('branding_location', '=', vals.get('branding_location')))
                price_domain.append(('branding_location', '=', vals.get('branding_location')))
            if vals.get('branding_method'):
                domain.append(('branding_method', '=', vals.get('branding_method')))
                price_domain.append(('branding_method', '=', vals.get('branding_method')))
            repeat_lines = self.search(domain)
            for repeat_line in repeat_lines:
                if repeat_line.product_id.product_tmpl_id.id == product.product_tmpl_id.id and repeat_line.setup_cost != 0.0:
                    vals.update({'setup_cost': 0.0, 'total_cost': (order_line.product_uom_qty * vals.get('item_cost'))  + vals.get('artwork_cost') + vals.get('colour_cost')})

            res = super(ProductBrandingLines,self).create(vals)

            if not order_line.order_id.override_branding_pricing:
                location = res.branding_location and '= ' + str(res.branding_location.id) or 'IS Null'
                method = res.branding_method and '= ' + str(res.branding_method.id) or 'IS Null'
                color_variant = res.color_variant and '= ' + str(res.color_variant.id) or 'IS Null'
                size_variant = res.size_variant and '= ' + str(res.size_variant.id) or 'IS Null'
                order_id = order_line.order_id and '= ' + str(order_line.order_id.id) or 'IS Null'
                tmpl_id = product.product_tmpl_id and '= ' + str(product.product_tmpl_id.id) or 'IS Null'

                query = """SELECT b.id,SUM(sl.product_uom_qty) 
                            FROM product_branding_lines b,sale_order_line sl 
                            WHERE b.branding_location %s AND 
                            b.branding_method %s AND 
                            b.color_variant %s AND 
                            b.size_variant %s AND 
                            b.sale_order_line_id in (SELECT id FROM sale_order_line WHERE order_id %s) AND 
                            sl.id in (SELECT id FROM sale_order_line WHERE order_id %s) AND 
                            b.product_id in (SELECT id FROM product_product WHERE product_tmpl_id %s) GROUP BY b.id"""% (location,method,color_variant, size_variant, order_id, order_id, tmpl_id,)
                self.env.cr.execute(query)
                quary_res = self.env.cr.fetchall()
                if quary_res:
                    price_domain.append(('product_id', '=', product.product_tmpl_id.id))
                    price_domain.append(('min_qty', '<=', quary_res[0][1]))
                    price_domain.append(('max_qty', '>=', quary_res[0][1]))
                    branding_price_ids_on_limits = self.env['branding.price'].search(price_domain)

                    for vals in quary_res:
                        product_branding_line = self.browse(vals[0])
                        if branding_price_ids_on_limits:
                            if order_line.order_id.pricelist_id and order_line.order_id.pricelist_id.percentage:
                                product_branding_line.item_cost = round((branding_price_ids_on_limits.item_cost * (1 - (order_line.order_id.pricelist_id.percentage/100))),2)
#                                 product_branding_line.total_cost = (product_branding_line.sale_order_line_id.product_uom_qty * product_branding_line.item_cost) + product_branding_line.setup_cost + product_branding_line.artwork_cost + product_branding_line.colour_cost or 0.0
                            else:
                                product_branding_line.item_cost = round(branding_price_ids_on_limits.item_cost,2) or 0.0
#                                 product_branding_line.total_cost = (product_branding_line.sale_order_line_id.product_uom_qty * product_branding_line.item_cost) + product_branding_line.setup_cost + product_branding_line.artwork_cost + product_branding_line.colour_cost or 0.0
        return res

    @api.multi
    def unlink(self):
        removed_branding_line_ids = str(self._ids).replace(',)', ')')
        setup_cost = False
        for branding_line in self:
            product = branding_line.product_id
            order_line = branding_line.sale_order_line_id
            if order_line.order_id and not order_line.order_id.override_branding_pricing:
                price_domain = []
                if branding_line.color_variant:
                    price_domain.append(('color_variant', '=', branding_line.color_variant.id))
                else:
                    price_domain.append(('color_variant', '=', False))
                if branding_line.size_variant:
                    price_domain.append(('size_variant', '=', branding_line.size_variant.id))
                else:
                    price_domain.append(('size_variant', '=', False))
                if branding_line.branding_location:
                    price_domain.append(('branding_location', '=', branding_line.branding_location.id))
                if branding_line.branding_method:
                    price_domain.append(('branding_method', '=', branding_line.branding_method.id))

                location = branding_line.branding_location and '= ' + str(branding_line.branding_location.id) or 'IS Null'
                method = branding_line.branding_method and '= ' + str(branding_line.branding_method.id) or 'IS Null'
                color_variant = branding_line.color_variant and '= ' + str(branding_line.color_variant.id) or 'IS Null'
                size_variant = branding_line.size_variant and '= ' + str(branding_line.size_variant.id) or 'IS Null'
                order_id = order_line.order_id and '= ' + str(order_line.order_id.id) or 'IS Null'
                tmpl_id = product.product_tmpl_id and '= ' + str(product.product_tmpl_id.id) or 'IS Null'

                self.env.cr.execute("""SELECT id FROM sale_order_line WHERE order_id %s AND id != %s """% (order_id, order_line.id,))
                order_line_ids = self.env.cr.fetchall()

                query = """SELECT b.id, SUM(sl.product_uom_qty) 
                            FROM product_branding_lines b,sale_order_line sl 
                            WHERE b.id NOT IN %s AND
                            b.branding_location %s AND 
                            b.branding_method %s AND 
                            b.color_variant %s AND 
                            b.size_variant %s AND 
                            b.sale_order_line_id in (SELECT id FROM sale_order_line WHERE order_id %s AND id != %s) AND 
                            sl.id in (SELECT id FROM sale_order_line WHERE order_id %s AND id != %s) AND 
                            b.product_id in (SELECT id FROM product_product WHERE product_tmpl_id %s) GROUP BY b.id"""% (removed_branding_line_ids,location,method,color_variant, size_variant, order_id, order_line.id, order_id, order_line.id, tmpl_id,)
                self.env.cr.execute(query)
                quary_res = self.env.cr.fetchall()

                if quary_res:
                    price_domain.append(('product_id', '=', product.product_tmpl_id.id))
                    price_domain.append(('min_qty', '<=', quary_res[0][1]))
                    price_domain.append(('max_qty', '>=', quary_res[0][1]))
                    branding_price_ids_on_limits = self.env['branding.price'].search(price_domain)

                    branding_rec = self.browse(quary_res[0][0])
                    if branding_rec.setup_cost or setup_cost == True:
                        setup_cost = True
                    if branding_line.setup_cost and setup_cost == False:
                        self.env.cr.execute("""UPDATE product_branding_lines set setup_cost=%s where id=%s"""% (branding_line.setup_cost,quary_res[0][0],))
                        setup_cost = True
                    for vals in quary_res:
                        product_branding_line = self.browse(vals[0])
                        if branding_price_ids_on_limits:
                            total_cost = (product_branding_line.sale_order_line_id.product_uom_qty * product_branding_line.item_cost) + product_branding_line.setup_cost or 0.0
                            item_cost = branding_price_ids_on_limits.item_cost or 0.0
                            self.env.cr.execute("""UPDATE product_branding_lines set item_cost=%s,total_cost=%s where id=%s"""% (item_cost,total_cost,vals[0],))
        res = super(ProductBrandingLines, self).unlink()
        return res


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    percentage = fields.Float('Percentage')


