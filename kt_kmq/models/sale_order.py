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
import StringIO
import cStringIO
import base64
import requests
import xmltodict
from odoo.http import request

class ResUsers(models.Model):
        _inherit = 'res.users'
        user_pastel_id = fields.Integer('User Pastel ID')

        @api.model
        def create(self,vals):
                res = super(ResUsers,self).create(vals)
                auth_users = []
                andre_user = self.env['res.users'].search([('login','=','andre@kmq.co.za')])
                if andre_user:
                        andre_user_id = andre_user.id
                        auth_users.append(andre_user_id)

                if self._uid not in auth_users: 
                        raise UserError(_('Only Andre has been authorized to create users.'))
    
                return res


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def action_view_invoice(self):
        '''
        This function returns an action that display existing vendor bills of given purchase order ids.
        When only one found, show the vendor bill immediately.
        '''
        action = self.env.ref('account.action_invoice_tree2')
        result = action.read()[0]

        #override the context to get rid of the default filtering
        result['context'] = {'type': 'in_invoice', 'default_purchase_id': self.id}

        if not self.invoice_ids:
            # Choose a default account journal in the same currency in case a new invoice is created
            journal_domain = [
                ('type', '=', 'purchase'),
                ('company_id', '=', self.company_id.id),
                ('currency_id', '=', self.currency_id.id),
            ]
            default_journal_id = self.env['account.journal'].search(journal_domain, limit=1)
            if default_journal_id:
                result['context']['default_journal_id'] = default_journal_id.id
        else:
            # Use the same account journal than a previous invoice
            result['context']['default_journal_id'] = self.invoice_ids[0].journal_id.id

        #choose the view_mode accordingly
        if len(self.invoice_ids) != 1:
            result['domain'] = "[('id', 'in', " + str(self.invoice_ids.ids) + ")]"
        elif len(self.invoice_ids) == 1:
            res = self.env.ref('account.invoice_supplier_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = self.invoice_ids.id
	result['context']['default_reference'] = self.partner_ref
        return result


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'
    product_qty = fields.Integer(string='Quantity', required=True)

class SaleOrderLine(models.Model):
        _inherit = "sale.order.line"

        add_product_branding = fields.Boolean('Add Branding')
	product_branding_ids = fields.One2many('product.branding.lines','sale_order_line_id',string="Product Branding")
	#product_uom_qty = fields.Integer(string='Quantity', required=True, default=1)
	#branding_method_ids = fields.Many2many('branding.method','product_brand_method_rel','product_id','method_id') #Jagadeesh JUN09

	@api.onchange('product_id','add_product_branding')
        def onchange_add_product_binding(self):
                #branding_price_obj = self.env['branding.price'].search([('product_id','=',self.product_id.product_tmpl_id.id)])
                locations = []
		branding_locations = []
		branding_price_ids = self.env['branding.price'].search([('product_id','=',self.product_id.product_tmpl_id.id)])
		for data in branding_price_ids:
			branding_locations.append(data.branding_location)
		branding_locations.sort()
                for rec in list(set(branding_locations)):
			branding_price_obj = self.env['branding.price'].search([('branding_location','=',rec.id)])
                        line_data = {}
                        line_data['branding_location'] = rec.id
                        line_data['product_id'] = self.product_id.id
                        locations.append(line_data)
                self.product_branding_ids = sorted(locations)

	@api.multi
	def write22222(self,vals):
		"""auth_users = []
		auth_users.append(1)
		andre_user = self.env['res.users'].search([('login','=','andre@kmq.co.za')])
		if andre_user:
			andre_user_id = andre_user.id
			auth_users.append(andre_user_id)
		nancy_user = self.env['res.users'].search([('login','=','nancy@kmq.co.za')])
	        if nancy_user:
        	        nancy_user_id = nancy_user.id
                	auth_users.append(nancy_user_id)

		daniel_user = self.env['res.users'].search([('login','=','daniel@kmq.co.za')])
                if daniel_user:
                        daniel_user_id = daniel_user.id
                        auth_users.append(daniel_user_id)

	        if self._uid not in auth_users:
        	        raise UserError(_('You are not authorized to updated quote lines.'))

        	if request.session.has_key('from_quote') and request.session['from_quote']:
                	vals = {}"""
		res = super(SaleOrderLine,self).write22222222(vals)
		return res	
		

class SaleOrder(models.Model):
	_inherit = "sale.order"


        delivery_hub_id = fields.Many2one('delivery.hub',string="Delivery Hub")
        courier_company_id = fields.Many2one('courier.company',string="Client Courier Company")
        show_delivery_hub = fields.Boolean('Show Delivery Hub ?',default=False)
        show_courier_company = fields.Boolean('Show Courier Company ?',default=False)

        @api.onchange('carrier_id')
        def onchange_carrier_id(self):
            if self.carrier_id.name == 'KMQ Courier':
                self.show_delivery_hub = True
            else:
                self.show_delivery_hub = False

            if self.carrier_id.name == 'Client Courier':
                self.show_courier_company = True
            else:
                self.show_courier_company = False


	@api.multi
	def _get_branding(self):
		#Jagadeesh start 
		#self.product_branding2_ids = self.order_line.product_branding_ids
		brand_ids = []
		for order in self.order_line:
		    for brand in order.product_branding_ids:
			if order.add_product_branding:
			        brand_ids.append(brand.id)
		#brand_ids = [brand.id for order in self.order_line for brand in order.product_branding_ids if self.order_line.add_product_branding]
		self.product_branding2_ids = [(6,0,brand_ids)]

        @api.multi
        def _get_has_branding(self):
		if self.product_branding2_ids:
			self.has_branding = True
	        else:
			self.has_branding = False

        def _get_partner_code(self):
        	for data in self:
                	data.partner_code = data.partner_id and data.partner_id.ref or ''


        partner_code = fields.Char(compute='_get_partner_code',string='Partner Code')
	add_product_branding = fields.Boolean('Add Branding')
	product_branding2_ids = fields.One2many('product.branding.lines','sale_order_id',string="Product Branding",compute='_get_branding')
	partner_id = fields.Many2one('res.partner', string='Customer', readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, required=True, change_default=True, index=True, track_visibility='always',default=lambda self: self.env.user.partner_id)
	associated_project = fields.Many2one('project.project','Associated Project')
	job_type = fields.Selection([('Normal','Normal'),('Re-Run','Re-Run'),('Special','Special'),('Deadline','Deadline')],string="Job Type")
        artwork_format = fields.Selection([('Wording','Wording'),('Jpeg','Jpeg'),('PDF','PDF'),('Other','Other')],string="Artwork Format")
        pantone = fields.Char('Pantone')
        deadline_date = fields.Datetime('Deadline Date')
	payment_deposit = fields.Integer('Payment Deposit %') #Jagadeesh added
	#Jagadeesh JUN08 start
        lost_reason_id = fields.Many2one('crm.lost.reason','Cancel Reason')
        lost_reason = fields.Text('Additional comments for cancel reason')
        required_reason = fields.Boolean('Required Reason ?')
	payment_type = fields.Selection([('deposit','Deposit % Amount'),('full','Full Amount')],string="Payment Type")
	has_branding = fields.Boolean(compute='_get_has_branding',string="Has Branding")
	alternate_do = fields.Boolean('Has Alternate Address?')
	alt_street = fields.Char('Street')
	alt_street2 = fields.Char('Street2')
	alt_zip = fields.Char('Zip', change_default=True, size=24)
	alt_city = fields.Char('City')
	alt_state_id = fields.Many2one("res.country.state", 'State')
	alt_country_id = fields.Many2one('res.country', 'Country')
	partner_id = fields.Many2one('res.partner', string='Customer', readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, required=True, index=True, track_visibility='always')
	#Jagadeesj end
	#Jagadeesh JUN 06 commented to remove proforma functionality
        @api.multi
        def open_quotation2(self):
                self.ensure_one()
                self.write({'quote_viewed': True})
                request.session['from_quote'] = True
                return {
                    'type': 'ir.actions.act_url',
                    'target': 'self',
                    'url': '/quote/%s/%s' % (self.id, self.access_token)
                }



	@api.multi
	def write(self,vals):
		if vals.has_key('state') and vals['state'] == 'sale':
			email_to = self.user_id and self.user_id.partner_id.email or ''
			body_html = ("""Dear %s ,<br/><br/>This is an email to notify you that the sale order %s has been confirmed.<br/><br/>Kind Regards<br/>""")% (self.user_id.name,self.name)
                        #Jagadeesh edn
                        mail_vals = {
                             'email_from':'info@kmqpromotions.com',
                             'email_to': email_to,
                             #'email_cc':'raj@strategicdimensions.co.za,thabo@strategicdimensions.co.za',
                             'subject':'Sale order confirmation notification',
                             'body_html':body_html
                                }
                        res2 = self.env['mail.mail'].sudo().create(mail_vals)
        	if request.session.has_key('from_quote') and request.session['from_quote']:
                	vals = {}
	        res = super(SaleOrder,self).write(vals)
        	return res

	@api.multi
        def action_quotation_send(self):
		res = super(SaleOrder,self).action_quotation_send()
		data = {}
		product_images = []
		all_attachment = []
		if self.order_line:
			for line in self.order_line:
				data = {}
				if line.product_id.image_medium:		
					data.update({'name': str(line.product_id.name),'res_model':'sale.order','datas':line.product_id.image_medium,'datas_fname':str(line.product_id.name)+'.png','res_id':self.id})
		                        attachment = self.env['ir.attachment'].create(data)
					all_attachment.append(attachment)
		if all_attachment:
			for att in all_attachment:
				if res.has_key('context') and res['context'].has_key('default_template_id'):
					template_id = res['context']['default_template_id']
					template_data = self.env['mail.template'].browse(template_id)
					#template_data.write({'attachment_ids': [(4, [att.id])]})
					template_data.write({'attachment_ids':[(6, 0, [att.id])]})
		return res


        @api.multi
        @api.onchange('partner_id')
        def onchange_partner_id(self):
	    if self.partner_id.account_blocked:
		self.partner_id = False
		#raise ValidationError('Account has been blocked for this customer')	 
		#raise Warning(_('Account has been blocked for this customer'))
		#return False
		return {'warning': {'title': _('Warning'),'message': _('Account has been blocked for this customer.')}}



            super(SaleOrder,self).onchange_partner_id()
	    self.payment_deposit = self.partner_id.parent_id and self.partner_id.parent_id.payment_deposit or self.partner_id.payment_deposit

	'''to get paid amount and show on confirmation page for deposit paymenst'''
        @api.multi
        def get_invoice_paid_amount(self):
            inv_obj = self.env['account.invoice'].sudo().search([('origin','=',self.name)],limit=1)
            paid_amount = 0.0
            if inv_obj:
                paid_amount = inv_obj.amount_total - inv_obj.residual
            return paid_amount


	#Jagadeesh JUN 06 end
	#Raaj New
	@api.multi
	def action_confirm(self):
		#Jagadeesh JUN06 start
		if self.product_branding2_ids and not self.pantone:
		    raise ValidationError('Please complete the Pantone.')
		if self.product_branding2_ids and not self.job_type:
                    raise ValidationError('Please complete the Job Type.')
		if not self.client_order_ref:
		    raise ValidationError('Please complete the  customer reference')
		#Jagadeesj JUN06 end
		super(SaleOrder,self).action_confirm()
                for order in self:
                    stock_picks = self.env['stock.picking'].search([('group_id','=',order.procurement_group_id.id)])
                    for stock in stock_picks:
			stock.carrier_id = order.carrier_id.id #Jagadeesh oct 23
                        if stock.state in ['confirmed','assigned']:
                            stock.state = 'waiting'

        # Comment the code for create project from sale order
# 		if self.product_branding2_ids:
# 			project_id = self.env['project.project'].create({'name':'Proj'+self.name,'job_type':self.job_type,'artwork_format':self.artwork_format,'pantone':self.pantone,'deadline_date':self.deadline_date,'partner_id':self.partner_id and self.partner_id.id or False}) #Jagadeesh added partner id
# 			if project_id:
# 				self.write({'associated_project':project_id and project_id.id or False})

				#project_id.write({'partner_id':self.partner_id and self.partner_id.id or False}) #Jagadeesh commneted
		return super(SaleOrder,self).action_confirm()


        #Jagadeesh JUN08 start 
        @api.multi
        def action_cancel(self):
             view_id = self.env['ir.model.data'].get_object_reference('kt_kmq','quotation_cancel_form')[1]
             return {
                'name':'Quotation Cancel Reason',
                'nodestroy':True,
                'search_view_id':view_id,
                'view_mode':'form',
                'view_type':'form',
                'res_model':'quotation.cancel',
                'type':'ir.actions.act_window',
                'target':'new',
                }
        #Jagadeesh JUN08 end    

	@api.multi
        @api.onchange('alt_state_id')
        def onchange_alt_state_id(self):
            if self.alt_state_id:
                self.alt_country_id = self.alt_state_id.country_id


	#Jagadeesh start
	''' for report customizations'''
        @api.multi
        def get_product_branding_items(self,order):
            branding_lines = self.env['product.branding.lines'].search([('sale_order_line_id','=',order.id),('product_id','=',order.product_id.id)])
            return branding_lines
        #Jagadeesh end

        @api.depends('order_line.price_total')
        def _amount_all(self):
                """
                Compute the total amounts of the SO.
                """
                line_total = 0.0
                for order in self:
                    if order.product_branding2_ids:
                            for line in order.product_branding2_ids:
                                line_total+=line.total_cost
                    amount_untaxed = amount_tax = 0.0
                    for line in order.order_line:
                        amount_untaxed += line.price_subtotal
                        amount_tax += line.price_tax
                    line_brand_tot = line_total + amount_untaxed
		    if amount_tax > 0.0:
	                    line_brand_tot_tax = (line_brand_tot * 14) / 100
		    else:
			    line_brand_tot_tax = amount_tax
                    order.update({
                        'amount_untaxed': order.pricelist_id.currency_id.round(amount_untaxed) + line_total,
                        'amount_tax': order.pricelist_id.currency_id.round(line_brand_tot_tax),
                        'amount_total': amount_untaxed + line_brand_tot_tax + line_total,
                    })


        # From SO create invoice and update the project fields from SO to invoice
        @api.multi
        def _prepare_invoice(self):
            res = super(SaleOrder, self)._prepare_invoice()
            print "\n\n --res--",res
            res.update({'job_type':self.job_type,
                        'artwork_format':self.artwork_format,
                        'pantone':self.pantone,
                        'deadline_date':self.deadline_date,
                        })
            return res

#         @api.multi
#         def _prepare_invoice(self):
#                 print "\n\n --call----_prepare_invoice---",self
#                 """
#                 Prepare the dict of values to create the new invoice for a sales order. This method may be
#                 overridden to implement custom invoice generation (making sure to call super() to establish
#                 a clean extension chain).
#                 """
#                 self.ensure_one()
#                 journal_id = self.env['account.invoice'].default_get(['journal_id'])['journal_id']
#                 if not journal_id:
#                     raise UserError(_('Please define an accounting sale journal for this company.'))
#                 invoice_vals = {
#                     'name': self.client_order_ref or '',
#                     'origin': self.name,
#                     'type': 'out_invoice',
#                     'account_id': self.partner_invoice_id.property_account_receivable_id.id,
#                     'partner_id': self.partner_invoice_id.id,
#                     'partner_shipping_id': self.partner_shipping_id.id,
#                     'journal_id': journal_id,
#                     'currency_id': self.pricelist_id.currency_id.id,
#                     'comment': self.note,
#                     'payment_term_id': self.payment_term_id.id,
#                     'fiscal_position_id': self.fiscal_position_id.id or self.partner_invoice_id.property_account_position_id.id,
#                     'company_id': self.company_id.id,
#                     'user_id': self.user_id and self.user_id.id,
#                     'team_id': self.team_id.id,
#                     'date_invoice' : datetime.now().date(),
#                     'pricelist_id' : self.pricelist_id and self.pricelist_id.id or False,
#                     
#                 }
#                 return invoice_vals

        @api.multi
        def action_invoice_create_inh(self, grouped=False, final=False):
            """
            Create the invoice associated to the SO.
            :param grouped: if True, invoices are grouped by SO id. If False, invoices are grouped by
                        (partner_invoice_id, currency)
            :param final: if True, refunds will be generated if necessary
            :returns: list of created invoices
            """
            inv_obj = self.env['account.invoice']
            ir_property_obj = self.env['ir.property']
            precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            invoices = {}
            references = {}
            branding_vals_item = {}
            branding_vals_setup = {}
            lt = []
            location_code = False
            tax_ids = []
            att = ''
            for order in self:
                account_id = False
                if self.product_id.id:
                    account_id = self.product_id.property_account_income_id.id
                if not account_id:
                    inc_acc = ir_property_obj.get('property_account_income_categ_id', 'product.category')
                    account_id = order.fiscal_position_id.map_account(inc_acc).id if inc_acc else False
                branding_items_vals = [] 
                group_key = order.id if grouped else (order.partner_invoice_id.id, order.currency_id.id)
                for line in order.order_line.sorted(key=lambda l: l.qty_to_invoice < 0):
                    if line.tax_id:
                        if self.fiscal_position_id and self.product_id.taxes_id:
                            tax_ids = order.fiscal_position_id.map_tax(self.product_id.taxes_id).ids
                        else:
                            tax_ids = self.product_id.taxes_id.ids
                    #Jagadeesh added 
                    if line.qty_to_invoice == 0.0:
                        line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced
                    #Jagadeesh end
                    if float_is_zero(line.qty_to_invoice, precision_digits=precision):
                        continue
                    if group_key not in invoices:
                        inv_data = order._prepare_invoice()
                        invoice = inv_obj.create(inv_data)
                        invoice._onchange_payment_term_date_invoice()
                        references[invoice] = order
                        invoices[group_key] = invoice
                    elif group_key in invoices:
                        vals = {}
                        vals['user_id'] = order.user_id and order.user_id.id or False
                        if order.name not in invoices[group_key].origin.split(', '):
                            vals['origin'] = invoices[group_key].origin + ', ' + order.name
                        if order.client_order_ref and order.client_order_ref not in invoices[group_key].name.split(', '):
                            vals['name'] = invoices[group_key].name + ', ' + order.client_order_ref
                        invoices[group_key].write(vals)
                    if line.qty_to_invoice > 0:
                        line.invoice_line_create(invoices[group_key].id, line.qty_to_invoice)
                    elif line.qty_to_invoice < 0 and final:
                        line.invoice_line_create(invoices[group_key].id, line.qty_to_invoice)

                    #Jagadeesh added 
                    ''' to update branding items'''
                    if line.add_product_branding:
                        product_brand_items = self.env['product.branding.lines'].search([('sale_order_line_id','=',line.id)])
                        for brand in product_brand_items:
                            if brand.setup_cost >= 0.00:
                                location = brand.branding_location.name
                                if location:
                                    location_name = location.split(" ")[1]
                                    location_code = 'B0SP'+location_name
                            if brand.color_variant:
                                att = brand.color_variant.name
                            if brand.size_variant:
                                att = brand.size_variant.name
                            if location_code:
                                prod = self.env['product.product'].search([('default_code','=',str(location_code))])
                                prod2 = self.env['product.template'].search([('default_code','=','BOSPA')])
                                branding_vals_setup = {'product_id':prod.id,'name': "Setup for"+" "+brand.product_id.name+"-"+location_code+"-"+att,
                                                  'quantity':1,'price_unit':brand.setup_cost,
                                                  'invoice_line_tax_ids':[(6, 0, tax_ids)],'amount':(1 * brand.setup_cost),
                                                  'account_id':account_id}
                                lt.append(branding_vals_setup)
                            if brand.item_cost >= 0.00:
                                prod_code = prod_desc = ''
                                location = brand.branding_location.name
                                if location:
                                    location_name = location.split(" ")[1]
                                    location_code = 'B0SP'+location_name
                                if brand.color_variant:
                                        att = brand.color_variant.name
                                if brand.size_variant:
                                        att = brand.size_variant.name
                            prod_id = False
                            if location_code:
                                prod_id = self.env['product.product'].search([('default_code','=',location_code)])
                                if brand.branding_method.name == 'Heat Press':
                                    prod_code = 'B0FLEX'
                                    prod_desc = 'KMQ Heat Press for'+ ' '+brand.product_id.name+"-"+location_code+"-"+att

                                elif brand.branding_method.name == 'Pad Print':
                                    prod_code = 'B0PPA'
                                    prod_desc = 'KMQ Pad Print for'+ ' '+brand.product_id.name+"-"+location_code+"-"+att

                                elif brand.branding_method.name == 'Screen Print':
                                    prod_code = 'B0SPA'
                                    prod_desc = 'KMQ Screen Print for'+ ' '+brand.product_id.name+"-"+location_code+"-"+att

                                elif brand.branding_method.name == 'Embroidery':
                                    prod_code = 'BEMB'
                                    prod_desc = 'KMQ Embroidery for'+ ' '+brand.product_id.name+"-"+location_code+"-"+att

                                elif brand.branding_method.name == 'Doming':
                                    prod_code = 'DOME'
                                    prod_desc = 'KMQ Doming for'+ ' '+brand.product_id.name+"-"+location_code+"-"+att

                                elif brand.branding_method.name == 'Stickers':
                                    prod_code = 'STCKR'
                                    prod_desc = 'KMQ Stickers for'+ ' '+brand.product_id.name+"-"+location_code+"-"+att

                                branding_vals_item = {'product_id':prod_id.id,'name':prod_desc,
                                              'quantity':line.product_uom_qty,'price_unit':brand.item_cost,
                                              'invoice_line_tax_ids':[(6, 0, tax_ids)],'amount':(line.product_uom_qty * brand.item_cost),
                                              'account_id':account_id}
                                lt.append(branding_vals_item)

                #invoices[group_key].write({'account_product_branding_ids':branding_items_vals})
                for dic in lt:
                    invoices[group_key].write({'invoice_line_ids': [(0,0,dic)]})
                    #Jagadeesh end

                if references.get(invoices.get(group_key)):
                    if order not in references[invoices[group_key]]:
                        references[invoice] = references[invoice] | order

            if not invoices:
                raise UserError(_('There is no invoicable line.'))

            for invoice in invoices.values():
                if not invoice.invoice_line_ids:
                    raise UserError(_('There is no invoicable line.'))
                # If invoice is negative, do a refund invoice instead
                if invoice.amount_untaxed < 0:
                    invoice.type = 'out_refund'
                    for line in invoice.invoice_line_ids:
                        line.quantity = -line.quantity
                # Use additional field helper function (for account extensions)
                for line in invoice.invoice_line_ids:
                    line._set_additional_fields(invoice)
                # Necessary to force computation of taxes. In account_invoice, they are triggered
                # by onchanges, which are not triggered when doing a create.
                invoice.compute_taxes()
                invoice.message_post_with_view('mail.message_origin_link',
                    values={'self': invoice, 'origin': references[invoice]},
                    subtype_id=self.env.ref('mail.mt_note').id)

            return [inv.id for inv in invoices.values()]
	    #Jagadeesh end


class ProductBrandingLines(models.Model):
        _name = 'product.branding.lines'


        @api.model
        def _get_branding_method_domain(self):
	
            for obj in self:
                if obj.product_id:
                        branding_price_ids = self.env['branding.price'].search([('product_id','=',obj.product_id.product_tmpl_id.id)])
                        methods = []
                        for data in branding_price_ids:
                                methods.append(data.branding_method.id)
                        return [('id', 'in', methods)]
                else:
                    return []


        branding_location = fields.Many2one('branding.location','Branding Location')
        #branding_method = fields.Many2one('branding.method',string='Branding Method',domain=_get_branding_method_domain)
	#branding_method = fields.Many2one('branding.method',string='Branding Method',domain=lambda self: self._get_branding_method_domain())
	#branding_method = fields.Many2one('branding.method',string='Branding Method',domain=_get_branding_method_domain)
	branding_method = fields.Many2one('branding.method',string='Branding Method')
	branding_method_name = fields.Char('Branding Method Name')
        #product_id = fields.Many2one('product.template','Product')
	product_id = fields.Many2one('product.product','Product') #Jagadeesh
        color_variant = fields.Many2one('color.variants','Colours')
	size_variant = fields.Many2one('size.variants','Sizes')
        setup_cost = fields.Float('Setup Cost')
        item_cost = fields.Float('Cost/Item')
        total_cost = fields.Float('Total Cost')
	sale_order_id = fields.Many2one('sale.order','Online Order')
	sale_order_line_id = fields.Many2one('sale.order.line','Online Order')
	invoice_id = fields.Many2one('account.invoice','Invoice/Bill')

	#Jagadeesh 
	@api.multi
	@api.onchange('branding_location')
	def onchange_branding_location(self):
	     self.product_id = self.sale_order_line_id.product_id.id
	     self.sale_order_id = self.sale_order_line_id.order_id.id
	#Jagadeesh end


	@api.multi
        @api.onchange('setup_cost','item_cost')
        def onchange_costs(self):
             self.total_cost = (self.sale_order_line_id.product_uom_qty * self.item_cost) + self.setup_cost
             #self.sale_order_id = self.sale_order_line_id.order_id.id



	#Jagadeesh JUN08 start
	@api.multi
	def _get_method_ids(self,product):
            for obj in self:
                if obj.product_id:
                        branding_price_ids = self.env['branding.price'].search([('product_id','=',obj.product_id.product_tmpl_id.id)])
                        methods = []
                        for data in branding_price_ids:
                                methods.append(data.branding_method.id)
                        return methods
                else:
                    return []

	
	
	@api.multi
	@api.onchange('product_id')
	def onchnge_product_branding_method(self):
		if self.product_id:
			branding_price_ids = self.env['branding.price'].search([('product_id','=',self.product_id.product_tmpl_id.id)])
			methods = []
			for data in branding_price_ids:
				methods.append(data.branding_method.id)
			return {'domain':{'branding_method': [('id', 'in', methods)]}}

	#Jagadeesh JUN08 end

	@api.multi
        @api.onchange('branding_method')
        def onchange_branding_location(self):
             self.branding_method_name = self.branding_method.name or ''
	     if self.branding_method:
                     branding_obj = self.env['branding.price'].search([('product_id','=',self.product_id.product_tmpl_id.id),('branding_method','=',self.branding_method.id)])
		     colors = []
		     sizes = []
		     for data in branding_obj:
			colors.append(data.color_variant.id)
			sizes.append(data.size_variant.id)
		     return {'domain':{'color_variant': [('id', 'in', colors)],'size_variant':[('id', 'in', sizes)]}}



	@api.onchange('branding_method','color_variant','size_variant')
	def onchange_branding_items(self):	
		if (self.branding_method and self.color_variant) or (self.branding_method and self.size_variant):
			branding_price_ids = self.env['branding.price'].search([('branding_method','=',self.branding_method.id),('product_id','=',self.product_id.product_tmpl_id.id),('branding_location','=',self.branding_location.id)])
			product_id = self.env['product.product'].search([('product_tmpl_id','=',self.sale_order_line_id.product_id.id)])
			branding_price_ids_lst = []
			branding_price_ids_on_colors_lst = []
			branding_price_ids_on_size_lst = []
			if branding_price_ids:
				for rec in branding_price_ids:
					branding_price_ids_lst.append(rec.id)
				branding_price_ids_on_colors = self.env['branding.price'].search([('id','in',branding_price_ids_lst),('color_variant','=',self.color_variant.id)])
				if branding_price_ids_on_colors and self.color_variant:
					for rec in branding_price_ids_on_colors:
	                	                branding_price_ids_on_colors_lst.append(rec.id)
					if branding_price_ids_on_colors_lst:
						branding_price_ids_on_limits = self.env['branding.price'].search([('id','in',branding_price_ids_on_colors_lst),('min_qty','<=',self.sale_order_line_id.product_uom_qty),('max_qty','>=',self.sale_order_line_id.product_uom_qty)])
                                                if branding_price_ids_on_limits:
                                                        #for rec in branding_price_ids_on_limits:
                                                        self.setup_cost = branding_price_ids_on_limits.setup_cost or 0.0
                                                        self.item_cost = branding_price_ids_on_limits.item_cost or 0.0
                                                        self.total_cost = (self.sale_order_line_id.product_uom_qty * self.item_cost) + self.setup_cost or 0.0
				branding_price_ids_on_size = self.env['branding.price'].search([('id','in',branding_price_ids_lst),('size_variant','=',self.size_variant.id)])
				if branding_price_ids_on_size and self.size_variant:
					for rec in branding_price_ids_on_size:
		                        	branding_price_ids_on_size_lst.append(rec.id)
					if branding_price_ids_on_size_lst:
						branding_price_ids_on_limits = self.env['branding.price'].search([('id','in',branding_price_ids_on_size_lst),('min_qty','<=',self.sale_order_line_id.product_uom_qty),('max_qty','>=',self.sale_order_line_id.product_uom_qty)])
						if branding_price_ids_on_limits:
							for rec in branding_price_ids_on_limits:
								self.setup_cost = rec.setup_cost or 0.0
								self.item_cost = rec.item_cost or 0.0
								self.total_cost = (self.sale_order_line_id.product_uom_qty * self.item_cost) + self.setup_cost or 0.0

class QuotaionCancel(models.Model):
    _name = 'quotation.cancel'

    lost_reason_id = fields.Many2one('crm.lost.reason','Cancel Reason')
    lost_reason = fields.Text('Additional comments for cancel reason ')
    required_reason = fields.Boolean('Required Reason ?')


    @api.onchange('lost_reason_id')
    def onchange_lost_reason(self):
        if self.lost_reason_id:
            if self.lost_reason_id.name in ['other','Other']:
                self.required_reason = True
            else:
                self.required_reason = False
        else:
            self.required_reason = False

    @api.multi
    def submit_reason(self):
        project_stages_obj = self.env['project.stages']
        if self.lost_reason_id:
            sale_order_id = self.env.context.get('active_id')
            sale_order_obj = self.env['sale.order'].browse(sale_order_id)
            sale_order_obj.lost_reason_id = self.lost_reason_id.id
            sale_order_obj.lost_reason = self.lost_reason
            sale_order_obj.required_reason = self.required_reason

            sale_order_obj.state = 'cancel'
            #Jagadeesh oct 23
            ''' to cancel the delivery orders '''
            ref = self.env['ir.sequence'].search([('name','=','Primary WarehouseSequence picking')],limit=1)
            warehouse = self.env['stock.warehouse'].search([('name','=','Main Warehouse Cosmic Street')],limit=1)
            pick_type = self.env['stock.picking.type'].search([('name','=','Pick'),('sequence_id','=',ref.id),('warehouse_id','=',warehouse.id)],limit=1)

            stock_picks = self.env['stock.picking'].search([('group_id','=',sale_order_obj.procurement_group_id.id),('picking_type_id','=',pick_type.id)])
            for stock in stock_picks:
                stock.action_cancel()
            #Jagadeesh oct 23 end
            if self._context and self._context.get('active_model') and self._context.get('active_id'):
                order_id = self.env[self._context.get('active_model')].browse(self._context.get('active_id'))
                if order_id:
                    if order_id.associated_project:
                        stage_id = project_stages_obj.search([('name', '=', 'Cancelled')], order='id desc', limit=1)
                        if not stage_id:
                            stage_id = project_stages_obj.create({'name':'Cancelled'})
                        order_id.associated_project.write({'stage_id':stage_id.id})
                        order_id.associated_project.toggle_active()
                    order_id.order_line.mapped('procurement_ids').cancel()
        return True

#Jagadeesh start
class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    @api.multi
    def create_invoices(self):
        res = super(SaleAdvancePaymentInv,self).create_invoices()
        sale_orders = self.env['sale.order'].browse(self._context.get('active_ids', []))
        for order in sale_orders:
            stock_picks = self.env['stock.picking'].search([('group_id','=',order.procurement_group_id.id)])
            for stock in stock_picks:
                if stock.picking_type_id.name == 'Pick':
                    stock.state = 'assigned'
        return res
#Jagadeesh end

class DeliveryHub(models.Model):
    _name = 'delivery.hub'

    name = fields.Char('Name')

class CourierCompany(models.Model):
    _name = 'courier.company'

    name = fields.Char('Name')

