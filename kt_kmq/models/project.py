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
import MySQLdb
import html2text
import urllib

MAP_INVOICE_TYPE_PARTNER_TYPE = {
    'out_invoice': 'customer',
    'out_refund': 'customer',
    'in_invoice': 'supplier',
    'in_refund': 'supplier',
}


class ProjectStages(models.Model):
        _name = 'project.stages'

        name = fields.Char('Stage Name')
        sequence = fields.Integer('Sequence', default=1, help="Used to order stages. Lower is better.")
        send_customer_comm = fields.Boolean('Send Customer Communication')
        comm_template = fields.Many2one('mail.template','Communication Template')
	send_customer_sms = fields.Boolean('Send Customer SMS')
        sms_template = fields.Many2one('sms.template','SMS Template')


class Project(models.Model):
    _inherit = 'project.project'

    def _get_so_amount(self):
        total = 0.0
        for order in self.env['sale.order'].search([('associated_project','=',self.id)]):
            total+=order.amount_untaxed
        self.so_amount = total


    def _get_do_count(self):
        do_list = []
        for order in self.env['sale.order'].search([('associated_project','=',self.id)]):
            order.picking_ids = self.env['stock.picking'].search([('group_id', '=', order.procurement_group_id.id)]) if order.procurement_group_id else []
            self.do_count = len(order.picking_ids)
        """do_list.append(self.env['stock.picking'].search([('origin','=',order.name)]))
            self.do_count = len(do_list)"""

    def _get_inv_amount(self):
        total = 0.0
        for inv in self.env['account.invoice'].search([('associated_project','=',self.id)]):
                total+=inv.amount_untaxed
        self.inv_amount = total

    def _get_sign_count(self):
        sign_list = self.env['signature.request'].search([('project_id','=',self.id)])
        if sign_list:
            self.sign_count = len(sign_list)
			
    def _default_stage_id(self):
        default_stages = self.env['project.stages'].sudo().search([('name','=','New')]).id
        return default_stages

    project_number = fields.Char('Project Number')
    start_date = fields.Datetime('Start Date')
    end_date = fields.Datetime('End Date')
    space = fields.Char('')
    so_amount = fields.Float(compute='_get_so_amount',string="Sales")
    do_count = fields.Integer(compute='_get_do_count',string="Delivery")
    inv_amount = fields.Float(compute='_get_inv_amount',string="Invoiced")
    sign_count = fields.Integer(compute='_get_sign_count',string="Signatures")
    stage_id = fields.Many2one('project.stages','Stages',default=lambda self: self._default_stage_id(),track_visibility='onchange')
    job_type = fields.Selection([('Normal','Normal'),('Re-Run','Re-Run'),('Special','Special'),('Deadline','Deadline')],string="Job Type")
    artwork_format = fields.Selection([('Wording','Wording'),('Jpeg','Jpeg'),('PDF','PDF'),('Other','Other')],string="Artwork Format")
    pantone = fields.Char('Pantone')
    deadline_date = fields.Datetime('Deadline Date')
    artwork_upload_ids = fields.One2many('artwork.upload.details','project_id',string="Artwork Upload Details")
    logo = fields.Char(string="Logo")
    sale_person = fields.Many2one('res.users', 'Sales Person', compute="get_sale_detail")
    sale_number = fields.Many2one('sale.order', 'Sales Order', compute="get_sale_detail")
    invoice_numbers = fields.Char('Invoices', compute="get_invoice_numbers")

    @api.depends()
    @api.multi
    def get_invoice_numbers(self):
        account_obj = self.env['account.invoice']
        invoice_numbers = ''
        for project in self:
            invoices = account_obj.search([('associated_project', '=', project.id)])
            for invoice in invoices:
                invoice_numbers = invoice_numbers + ', ' + invoice.number
            project.invoice_numbers = invoice_numbers.lstrip(', ')

    @api.depends()
    @api.multi
    def get_sale_detail(self):
        order_obj = self.env['sale.order']
        for project in self:
            sales = order_obj.search([('associated_project', '=', project.id)])
            if sales:
                project.sale_number = sales[0].id
                project.sale_person = sales[0].user_id and sales[0].user_id.id

    def synch_data_daily(self):
	    journal = self.env['account.journal'].search([('name','=','Bank')])
	    invoice_id_list = []
	    count = 0
	    db = MySQLdb.connect("puladb.intdev.co.za","domain","Str@teg1c321","kmq" )
	    cr = db.cursor()
	    #qry = "UPDATE invoice_header set exists_in_odoo=True where reference='IN224818'"
	    data = cr.execute("SELECT * from invoice_header_invoice")
	    res = cr.fetchall()
	    for data in res:
		count+=1
		partner_id = data[2].split('_')
		user_id = data[3].split('_')
		journal_id = data[5].split('_')
		invoice_id = self.env['account.invoice'].search([('name','=',data[0])])
		if not invoice_id:
			res = self.env['account.invoice'].create({'name':data[0],'partner_id':int(partner_id[-1]),'date_invoice':data[1],'user_id':int(user_id[-1]),'journal_id':int(journal_id[-1]),'payment_term_id':1,'account_id':7,'state':'draft'})

	    #cr.execute("DELETE from invoice_header")
	    
	    data2 = cr.execute("SELECT * from invoice_lines")
            res2 = cr.fetchall()
	    counter = 0
            for data2 in res2:
		counter+=1
                product_id = data2[5]
                name = data2[7]
                account_id = data2[6] and data2[6] or 1
                quantity = float(data2[3])
                price_unit = float(data2[4])
                invoice_id = self.env['account.invoice'].search([('name','=',data2[0])])
		invoice_id = invoice_id and invoice_id[0]
		if data2[2]:
			tax_id = [int(data2[2])]
			tax_obj = self.env['account.tax'].browse(tax_id[0])
		else:
			tax_id = []
                if invoice_id :#and invoice_id.state in ['draft']:
			invoice_id_list.append(invoice_id)
                        line_id = self.env['account.invoice.line'].create({'name':name,'product_id':product_id,'account_id':account_id,'quantity':quantity,'price_unit':price_unit,'invoice_id':invoice_id.id,'invoice_line_tax_ids':[(6,0,tax_id)]})
			invoice_id.action_invoice_open()
			if tax_id:
				invoice_id._onchange_invoice_line_ids()
	    cr.close()

    def synch_refund_data_daily(self):
        invoice_id_list = []
        count = 0
        db = MySQLdb.connect("puladb.intdev.co.za","domain","Str@teg1c321","kmq" )
        cr = db.cursor()
        #qry = "UPDATE invoice_header set exists_in_odoo=True where reference='IN224818'"
        data = cr.execute("SELECT * from refund_header")
        res = cr.fetchall()
        for data in res:
            count+=1
            partner_id = data[2]
            user_id = data[3]
            journal_id = data[5]
            payment_id = data[4]
            account_id = data[6]
        refund_id = self.env['account.invoice'].search([('name','=',data[0])])
        if not refund_id:
            res = self.env['account.invoice'].create({'name':data[0],'origin':data[8],'partner_id':int(partner_id),'date_invoice':data[1],'user_id':int(user_id),'journal_id':int(journal_id),'payment_term_id':int(payment_id),'account_id':int(account_id),'type':'out_refund'})

	    
	    data2 = cr.execute("SELECT * from refund_lines")
            res2 = cr.fetchall()
	    counter = 0
            for data2 in res2:
		counter+=1
                product_id = data2[5]
                name = data2[7]
                account_id = data2[6] and data2[6] or 1
                quantity = float(data2[3])
                price_unit = float(data2[4])
                invoice_id = self.env['account.invoice'].search([('name','=',data2[0])])
		if invoice_id:
			invoice_id = invoice_id[0]
		if data2[2]:
			tax_id = [int(data2[2])]
			tax_obj = self.env['account.tax'].browse(tax_id[0])
		else:
			tax_id = []
                if invoice_id:# and invoice_id.state not in ['open','paid']:
			invoice_id_list.append(invoice_id)
                        line_id = self.env['account.invoice.line'].create({'name':name,'product_id':product_id,'account_id':account_id,'quantity':quantity,'price_unit':price_unit,'invoice_id':invoice_id.id,'invoice_line_tax_ids':[(6,0,tax_id)]})
			#invoice_id.action_invoice_open()
			if tax_id:
				invoice_id._onchange_invoice_line_ids()

        for inv in invoice_id_list:	
            inv.action_invoice_open()


    @api.model
    def create(self, values):
            values['project_number'] = '#'+self.env['ir.sequence'].next_by_code('project.project')
            new_id = super(Project,self).create(values)
            return new_id

    def write(self, values):
        approval_stage_id = self.env['project.stages'].search([('name','=','Artwork Design & Approval')])
        res = super(Project,self).write(values)
        mobile = self.partner_id.mobile
        if values.has_key('stage_id'):
            stage_name = self.env['project.stages'].browse(values['stage_id']).name
            email_to = self.user_id and self.user_id.partner_id.email or ''
            body_html = ("""Dear %s ,<br/><br/>This is an email to notify you that the Project %s has been moved to stage %s.<br/><br/>Kind Regards<br/>""")% (self.user_id.name,self.name,stage_name)
            #Jagadeesh edn
            mail_vals = {
                 'email_from':'info@kmqpromotions.com',
                 'email_to': email_to,
                 'email_cc':'raj@strategicdimensions.co.za,thabo@strategicdimensions.co.za',
                 'subject':'Project stage changes notification',
                 'body_html':body_html
                    }
            res2 = self.env['mail.mail'].sudo().create(mail_vals)

        if not mobile:
            raise UserError('Please capture mobile number for partner to send SMS.')
        if values.has_key('stage_id') and values['stage_id'] == approval_stage_id.id:
            template_obj = approval_stage_id.comm_template
            if approval_stage_id.send_customer_comm:
                template_obj.send_mail(self.id) 
            if approval_stage_id.send_customer_sms:
                sms_template_id = approval_stage_id.sms_template
                if sms_template_id:
                    gateway = self.env['sms.smsclient'].search([])
                    body = self.env['mail.template'].render_template(sms_template_id.body_html,'project.project',self.id)
                    url = gateway.url
                    name = url
                    ref = ''
                    if gateway.method == 'http':
                        prms = {}
                        for p in gateway.property_ids:
                            if p.type == 'user':
                                prms[p.name] = p.value
                            elif p.type == 'password':
                                prms[p.name] = p.value
                            elif p.type == 'to':
                                prms[p.name] = mobile
                            elif p.type == 'sender':
                                prms[p.name]= p.value
                            elif p.type == 'sms':
                                prms[p.name] = body
                            elif p.type == 'extra':
                                prms[p.name] = p.value
                                params = urllib.urlencode(prms)
                                name = url + "?" + params
                                queue_obj = self.env['sms.smsclient.queue']
                                values = {
                                    'name': name,
                                    'gateway_id':gateway.id,
                                    'state': 'draft',
                                    'mobile': mobile,
                                    'msg':html2text.html2text(sms_template_id.body_html) or '' #body #Raaj
                                    }
                                queue_obj.sudo().create(values)
                self.message_post(body=(str(html2text.html2text(sms_template_id.body_html))), context=None)
            return res

    def show_invoice(self):
        action = self.env.ref('account.action_invoice_refund_out_tree')
        result = action.read()[0]
        result['domain'] = [('associated_project', '=', self.id)]
        return result

    def show_deliveries(self):
        origins = []
        sale_orders = self.env['sale.order'].search([('associated_project','=',self.id)])
#         for order in sale_orders:
#                 origins.append(order.name)
#         action = self.env.ref('stock.action_picking_tree_all')
#         result = action.read()[0]
#         result['domain'] = [('origin','in',origins)]
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        pickings = sale_orders.mapped('picking_ids')
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = pickings.id
        return action


class SignatureRequestTemplate(models.Model):
    _inherit = "signature.request.template"

    project_id = fields.Many2one('project.project','Project')

class SignatureRequest(models.Model):
    _inherit = "signature.request"

    project_id = fields.Many2one('project.project','Project')

class MultiAttachment(models.Model):
	_name= 'multi.attachment'
	model_id = fields.Many2one('ir.model','Model')
	att_ids = fields.Many2many('ir.attachment', 'class_ir_attachments_rel', 'model_id_id', 'attachment_id', 'Click to add a new Everytime..')

class ArtWorkUploadDetails(models.Model):
	_name = 'artwork.upload.details' 
	filename = fields.Char('Filename')
	pantone = fields.Char('Pantone')
	comments = fields.Char('Comments')
	project_id = fields.Many2one('Project')

class sms_template(models.Model):
    "Templates for sending SMS"
    _name = "sms.template"
    name = fields.Char("Name",size=256)
    body_html = fields.Text('Body', translate=True, help="Rich-text/HTML version of the message (placeholders may be used here)")

