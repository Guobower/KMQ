from odoo import fields,models,api
from odoo.exceptions import ValidationError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _get_sale_order(self):
        sale_obj = self.env['sale.order']
	invoice_obj = self.env['account.invoice']
	for data in self:
	    data.invoice_status_color = 'none'
	    if data.origin:
		if ':' in data.origin:
	            origin = data.origin.split(':')[0]
		else:
		    origin = data.origin
	    else:
		origin = False
	    if origin:
	        sale_order_id = sale_obj.search([('name','=',origin)])
		invoice_id = invoice_obj.search([('origin','=',origin)])
        	if sale_order_id:
			if sale_order_id.product_branding2_ids:
				data.has_branding = True
			else:
				data.has_branding = False
                	data.sale_order_id = sale_order_id.id
		if invoice_id:
			data.invoice_id = invoice_id.id
			data.invoice_status_g = invoice_id.state.capitalize()
			data.invoice_status_r = invoice_id.state.capitalize()
			data.customer_account_type = invoice_id.partner_id.account_type
			if invoice_id.state == 'draft':
			    data.invoice_status_color = 'red'
			elif invoice_id.state == 'paid':
			    data.invoice_status_color = 'green'
			elif invoice_id.state == 'open':
			    if invoice_id.partner_id.account_type == 'cod':
				data.invoice_status_color = 'red'
			    elif invoice_id.partner_id.account_type == 'account':
				data.invoice_status_color = 'green'
			    else: pass
			else: pass
			

    sale_order_id = fields.Many2one('sale.order',compute='_get_sale_order',string='Sale Order')
    invoice_id = fields.Many2one('account.invoice',compute='_get_sale_order',string='Invoice')
    invoice_status_g = fields.Char(compute='_get_sale_order',string='Invoice Status')
    invoice_status_r = fields.Char(compute='_get_sale_order',string='Invoice Status')
    invoice_status_color = fields.Char(compute='_get_sale_order',string="Invoice Status Color")
    customer_account_type = fields.Char(compute='_get_sale_order',string='Customer Account Type')
    description = fields.Text('Description')
    has_branding = fields.Boolean('Has Branding')
    is_printed = fields.Boolean('Invoice Printed ?')
    is_stock_available = fields.Boolean(compute='_check_stock_availability',string='Is Stock Available ?',default=False)


    @api.multi
    def _check_stock_availability(self):
	#print 'self===========',self
	for obj in self:
	    if any(state != 'assigned' for state in obj.move_lines.mapped('state') ):
	        obj.is_stock_available = False
	    else:
	        obj.is_stock_available = True


    @api.multi
    def write(self,vals):
        res = super(StockPicking,self).write(vals)
        '''if self.state == 'assigned' and self.picking_type_id.name == 'Delivery Orders':
            source_doc = self.origin
            if ':' in self.origin:
                source_doc = self.origin.split(':')[0]
            inv_obj = self.env['account.invoice'].search([('partner_shipping_id','=',self.partner_id.id),('origin','=',source_doc)])
            if inv_obj.partner_id.account_type == 'cod' and inv_obj.state != 'paid':
                self.state = 'waiting' '''

	if self.state == 'assigned' and self.picking_type_id.name in ['Pick','Pack,Delivery Orders']:
		source_doc = self.origin
		if self.origin:
		    if ':' in self.origin:
		        source_doc = self.origin.split(':')[0]
		    else:
		        source_doc = self.origin
		else:
		    source_doc = False
		if source_doc:
		    inv_obj = self.env['account.invoice'].search([('partner_shipping_id','=',self.partner_id.id),('origin','=',source_doc)])
		else:
		    inv_obj = False
		if inv_obj:		    
		    #if inv_obj.partner_id.account_type == 'cod' and inv_obj.state != 'paid':
		    #    self.state = 'waiting' 
		    if inv_obj.state == 'draft':
			self.state = 'waiting'
  		    elif inv_obj.state == 'open' and inv_obj.partner_id.account_type == 'cod':
			self.state = 'waiting'			 

        return res


    @api.multi
    def do_new_transfer(self):
        source_doc = self.origin
	if self.origin:
            if ':' in self.origin:
                source_doc = self.origin.split(':')[0]
	    else:
		source_doc = self.origin
	else:
	    source_doc = False
	if source_doc:
            inv_obj = self.env['account.invoice'].search([('partner_shipping_id','=',self.partner_id.id),('origin','=',source_doc)])
	else:
	    inv_obj = False
	if source_doc:
            if not inv_obj and self.picking_type_code == 'outgoing':
                raise ValidationError(('Invoice has not been created for this sale order %s')%(source_doc))
            elif self.picking_type_id.name == 'Delivery Orders':
	        for inv in inv_obj:
	            if inv.partner_id.account_type == 'cod' and inv.state != 'paid':
        	        raise ValidationError(('Invoice has not been paid for this sale order %s')%(source_doc))

	return super(StockPicking,self).do_new_transfer()

    @api.multi
    def do_print_pickinggggggg(self):
	res = super(StockPicking,self).do_print_picking()
	self.is_printed = True
	return res


    @api.multi
    def do_print_invoice(self):
        sale_obj = self.env['sale.order']
        invoice_obj = self.env['account.invoice']
	invoice_id = False
        for data in self:
            if data.origin:
                if ':' in data.origin:
                    origin = data.origin.split(':')[0]
                else:
                    origin = data.origin
            else:
                origin = False
            if origin:
                invoice_id = invoice_obj.search([('origin','=',origin)],limit=1)

	if invoice_id:
            self.write({'is_printed': True})
            return self.env["report"].get_action(invoice_id, 'account.report_invoice')
	else:
	    raise ValidationError('There is no invoice to print')


class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    location_id = fields.Many2one(
        'stock.location', 'Return Location',
        domain="[('usage', '=', 'internal')]")

