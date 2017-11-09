# View Report
import werkzeug

from openerp import SUPERUSER_ID
from openerp import http,fields
from openerp.http import request
from openerp.tools.translate import _
from openerp.addons.website.models.website import slug
#upload cfo rules
from datetime import datetime
#upload cfo rules
import re
import json
import hashlib
# import pyDes
import urllib2
import urllib
import base64
import logging
from urlparse import urlparse

# View Report
from openerp.http import request, serialize_exception as _serialize_exception
from openerp.addons.web.controllers.main import serialize_exception,content_disposition
from odoo.addons.website_portal.controllers.main import website_account
from odoo.addons.website_quote.controllers.main import sale_quote
from odoo.addons.website_mail.controllers.main import _message_post_helper
import requests

import re

_logger = logging.getLogger(__name__)

#Jagadeesh start
class SaleQuote(sale_quote):

    @http.route("/quote/<int:order_id>/<token>", type='http', auth="public", website=True)
    def view(self, order_id, pdf=None, token=None, message=False, **post):
        # use sudo to allow accessing/viewing orders for public user
        # only if he knows the private token

        #Jagadeesh added
        no_pantone = False
        no_customer_ref = False
	#print 'before===============',no_pantone,no_customer_ref
        sale_order_obj = request.env['sale.order'].sudo().browse(order_id)
        if sale_order_obj.product_branding2_ids and not sale_order_obj.pantone:
           no_pantone = True

	if not sale_order_obj.client_order_ref:
	   no_customer_ref = True
        #Jagadeesh end
	#print 'after===============',no_pantone,no_customer_ref

        now = fields.Date.today()
        if token:
            Order = request.env['sale.order'].sudo().search([('id', '=', order_id), ('access_token', '=', token)])
            # Log only once a day
            if Order and request.session.get('view_quote') != now:
                request.session['view_quote'] = now
                body = _('Quotation viewed by customer')
                _message_post_helper(res_model='sale.order', res_id=Order.id, message=body, token=token, token_field="access_token", message_type='notification', subtype="mail.mt_note", partner_ids=Order.user_id.partner_id.ids)
        else:
            Order = request.env['sale.order'].search([('id', '=', order_id)])

        if not Order:
            return request.render('website.404')
        request.session['sale_order_id'] = Order.id

        days = 0
        if Order.validity_date:
            days = (fields.Date.from_string(Order.validity_date) - fields.Date.from_string(fields.Date.today())).days + 1
        if pdf:
            pdf = request.env['report'].sudo().with_context(set_viewport_size=True).get_pdf([Order.id], 'website_quote.report_quote')
            pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf))]
            return request.make_response(pdf, headers=pdfhttpheaders)
        transaction_id = request.session.get('quote_%s_transaction_id' % Order.id)
        if not transaction_id:
            Transaction = request.env['payment.transaction'].sudo().search([('reference', '=', Order.name)])
        else:
            Transaction = request.env['payment.transaction'].sudo().browse(transaction_id)
        values = {
            'quotation': Order,
            'message': message and int(message) or False,
            'option': bool(filter(lambda x: not x.line_id, Order.options)),
            'order_valid': (not Order.validity_date) or (now <= Order.validity_date),
            'days_valid': days,
            'action': request.env.ref('sale.action_quotations').id,
            'breadcrumb': request.env.user.partner_id == Order.partner_id,
            'tx_id': Transaction.id if Transaction else False,
            'tx_state': Transaction.state if Transaction else False,
            'tx_post_msg': Transaction.acquirer_id.post_msg if Transaction else False,
            'need_payment': Order.invoice_status == 'to invoice' and Transaction.state in ['draft', 'cancel', 'error'],
            'token': token,
        }

        if Order.require_payment or values['need_payment']:
            values['acquirers'] = list(request.env['payment.acquirer'].sudo().search([('website_published', '=', True), ('company_id', '=', Order.company_id.id)]))
            extra_context = {
                'submit_class': 'btn btn-primary',
                'submit_txt': _('Pay & Confirm')
            }
            values['buttons'] = {}
            for acquirer in values['acquirers']:
                values['buttons'][acquirer.id] = acquirer.with_context(**extra_context).render(
                    '/',
                    Order.amount_total,
                    Order.pricelist_id.currency_id.id,
                    values={
                        'return_url': '/quote/%s/%s' % (order_id, token) if token else '/quote/%s' % order_id,
                        'type': 'form',
                        'alias_usage': _('If we store your payment information on our server, subscription payments will be made automatically.'),
                        'partner_id': Order.partner_id.id,
                    })
        #Jagadeesh added
	return_url = '/quote/%s/%s' % (order_id, token) if token else '/quote/%s' % order_id
	#print 'vals===========',no_pantone,no_customer_ref
	values.update({'no_pantone':no_pantone,'no_customer_ref':no_customer_ref,'quote_id':order_id,'return_url':return_url })
	#Jagadeesh end
        return request.render('website_quote.so_quotation', values)

    @http.route(['/quote/accept'], type='json', auth="public", website=True)
    def accept(self, order_id, token=None, pantone=None,order_ref=None,signer=None, sign=None, **post):	
        Order = request.env['sale.order'].sudo().browse(order_id)
	#Jagadeesh new
	values = {}
	if pantone:
	    values.update({'pantone':pantone})
	if order_ref:
	    values.update({'client_order_ref':order_ref})
	if values:
	    Order.sudo().write(values)
	#Jagadeesh end
        if token != Order.access_token or Order.require_payment:
            return request.render('website.404')
        if Order.state != 'sent':
            return False
        attachments = [('signature.png', sign.decode('base64'))] if sign else []
        Order.action_confirm()
        message = _('Order signed by %s') % (signer,)
        _message_post_helper(message=message, res_id=order_id, res_model='sale.order', attachments=attachments, **({'token': token, 'token_field': 'access_token'} if token else {}))
        return True


    # note dbo: website_sale code
    @http.route(['/quote/<int:order_id>/transaction/<int:acquirer_id>'], type='json', auth="public", website=True)
    def payment_transaction(self, acquirer_id, order_id,pantone,order_ref,payment_type):
        return self.payment_transaction_token(acquirer_id, order_id, None,pantone,order_ref,payment_type)

    @http.route(['/quote/<int:order_id>/transaction/<int:acquirer_id>/<token>'], type='json', auth="public", website=True)
    def payment_transaction_token(self, acquirer_id, order_id,token,pantone,order_ref,payment_type):
        """ Json method that creates a payment.transaction, used to create a
        transaction when the user clicks on 'pay now' button. After having
        created the transaction, the event continues and the user is redirected
        to the acquirer website.

        :param int acquirer_id: id of a payment.acquirer record. If not set the
                                user is redirected to the checkout page
        """
        PaymentTransaction = request.env['payment.transaction'].sudo()

        Order = request.env['sale.order'].sudo().browse(order_id)
        values = {}
        if pantone:
            values.update({'pantone':pantone})
        if order_ref:
            values.update({'client_order_ref':order_ref})
        if payment_type:
            values.update({'payment_type':payment_type})
        Order.sudo().write(values)
        #Jagadeesh start JUN16
        #Order.payment_type = payment_type
        order_amount_total = False
        if Order.payment_type == 'deposit':
            order_amount_total = (Order.payment_deposit * Order.amount_total)/100
        else:
            order_amount_total = Order.amount_total

        #Jagadeesh end
        if not Order or not Order.order_line or acquirer_id is None:
            return request.redirect("/quote/%s" % order_id)

        # find an already existing transaction
        Transaction = PaymentTransaction.search([('reference', '=', Order.name)])
        if Transaction:
            if Transaction.sale_order_id != Order or Transaction.state in ['error', 'cancel'] or Transaction.acquirer_id.id != acquirer_id:
                Transaction = False
            elif Transaction.state == 'draft':
                Transaction.write({
                    'amount': order_amount_total, #Order.amount_total,
                })
        if not Transaction:
            Transaction = PaymentTransaction.create({
                'acquirer_id': acquirer_id,
                'type': Order._get_payment_type(),
                'amount': order_amount_total, #Order.amount_total,
                'currency_id': Order.pricelist_id.currency_id.id,
                'partner_id': Order.partner_id.id,
                'reference': PaymentTransaction.get_next_reference(Order.name),
                'sale_order_id': Order.id,
                'callback_eval': "self.sale_order_id._confirm_online_quote(self)"
            })
            request.session['quote_%s_transaction_id' % Order.id] = Transaction.id

            # update quotation
            Order.write({
                'payment_acquirer_id': acquirer_id,
                'payment_tx_id': Transaction.id
            })

        return Transaction.acquirer_id.with_context(
            submit_class='btn btn-primary',
            submit_txt=_('Pay & Confirm')).render(
            Transaction.reference,
            Order.amount_total,
            Order.pricelist_id.currency_id.id,
            values={
                'return_url': '/quote/%s/%s' % (order_id, token) if token else '/quote/%s' % order_id,
                'type': Order._get_payment_type(),
                'alias_usage': _('If we store your payment information on our server, subscription payments will be made automatically.'),
                'partner_id': Order.partner_shipping_id.id or Order.partner_invoice_id.id,
                'billing_partner_id': Order.partner_invoice_id.id,
            })



class QuoteInfo(http.Controller):

    @http.route("/submit_sale_order", type='http', auth="public", website=True)
    def quote_info(self,**post):
	#print 'post=============',post
	values = {}
	if 'pantone' in post.keys():
	    values.update({'pantone':post['pantone']})
	if 'customer_ref'  in post.keys():
	    values.update({'client_order_ref':post['customer_ref']})
        sale_order = request.env['sale.order'].sudo().browse(int(post['quotation_id']))
        sale_order.sudo().write(values)
        #return request.render('kt_kmq.so_quotation_inherit',{'quotation':sale_order})
	return request.redirect(post['return_url'])

#Jagadeesh end

class UploadArtwork(http.Controller):

    @http.route(['/upload/artwork/','/upload/artwork/<rec>'], type='http', auth="public", website=True)
    def upload_artwork_fun(self,**post):
	if post:
		project_id = int(post.get('rec'))
		session = request.session
		session['project_id'] = project_id
	return request.render("kt_kmq.artwork_upload_page")

    @http.route(['/submit/doc/'], type='http', auth="public", methods=['GET', 'POST'],website=True,csrf=False)
    def submit_doc_fun(self,**post):
	#print kk
	if post.get('attachment'):
		fname = str(post.get('attachment')),'chkkkkkkkkkkk'
	        gname = fname[0].split(' ')[1]
                fp = post.get('attachment')
                data= post.get('attachment').read()
		datas = data.encode('base64')
		attachment_id = request.env['ir.attachment'].create({
                    'name': gname[2:-1],
                    'res_name': 'Artwork',
                    'res_model': 'project.project',
                    'res_id': request.session['project_id'],
                    'datas': datas,
                    'datas_fname': gname[2:-1],
	        })
	if attachment_id:
	        return request.redirect('http://kmquat.odoo.co.za/page/thank-you?')
	else:
		return request.redirect('http://kmquat.odoo.co.za/page/upload-error')


    @http.route(['/upload/artwork2'], type='http', auth='public', website=True,csrf=False)
    def upload_artwork2(self,**post):

	artwork_details_obj = []
	artwork_details = request.env['artwork.upload.details'].search([('project_id','=',int(request.session.get('project_id')))])
	#request.env['artwork.upload.details'].create({'project_id':int(request.session.get('project_id')),'pantone':post['pantone'],'filename':a[1],'comments':post['comments']})
        #print artwork_details,'artwork_details_obj==========='
	sale_order_id = request.env['sale.order'].search([('associated_project','=',int(request.session.get('project_id')))])
	if sale_order_id:
		email_to = sale_order_id.user_id and sale_order_id.user_id.partner_id.email or ''
	#print kk
	for data in artwork_details:
		artwork_details_obj.append(data)
        if post:
	    l = []
	    fname = str(post['artwork_file']).split(' ')[1].encode("ascii")
	    l.append(fname)
	    a = l[0].encode('ascii').split('\'')
            cr = request.cr
            #project_id = int(request.session['rec'])
	    if post.get('artwork_file'):
                #fp = post.get('artwork_file')
                #data = post.get('artwork_file').split('\\')[2].read() 
		data = post.get('artwork_file').read()
                datas = data.encode('base64')
                attachment_id = request.env['ir.attachment'].create({
                    'name': a[1],
                    'res_name': 'Artwork',
                    'res_model': 'project.project',
                    'res_id': request.session['project_id'],
                    'datas': datas,
                    'datas_fname': a[1],
                })
	        if attachment_id:
			request.env['artwork.upload.details'].create({'project_id':int(request.session.get('project_id')),'pantone':post['pantone'],'filename':a[1],'comments':post['comments']})
			artwork_details_obj = []
		        artwork_details = request.env['artwork.upload.details'].search([('project_id','=',int(request.session.get('project_id')))])
		        #request.env['artwork.upload.details'].create({'project_id':int(request.session.get('project_id')),'pantone':post['pantone'],'filename':a[1],'comments':post['comments']})
		        #print artwork_details,'artwork_details_obj==========='
			sn_list = "<tbody><tr><td>Filename</td><td></td><td>Pantone</td><td></td><td>Comments</td></tr>"
		        for data in artwork_details:
                		artwork_details_obj.append(data)
				sn_list += "<tr><td>%s</td><td></td><td>%s</td><td></td><td>%s</td></tr>"%(data.filename,data.pantone,data.comments)
	                        sn_list += "</tbody>"

			body_html = ("""Dear %s ,<br/><br/>This is and alert email to notify you regarding the artwork upload.<br/><br/><table>%s</table><br/><br/>Kind Regards<br/>""")% (sale_order_id.user_id.name,sn_list)
	                #Jagadeesh edn
	                mail_vals = {
	          	     'email_from':'info@kmqpromotions.com',
                	     'email_to': email_to,
	                     'email_cc':'raj@strategicdimensions.co.za,thabo@strategicdimensions.co.za',
        	             'subject':'Artwork Upload Alert',
	                     'body_html':body_html
                                }
        		res = request.env['mail.mail'].sudo().create(mail_vals)


        		return request.render('kt_kmq.artwork_upload_page',{'artwork_details_obj':artwork_details_obj}) #json.dumps({'message':1})

	return request.render('kt_kmq.artwork_upload_page',{'artwork_details_obj':artwork_details_obj})

