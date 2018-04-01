# -*- coding: utf-8 -*-
import werkzeug

from odoo import SUPERUSER_ID
from odoo import http
from odoo.http import request
from odoo.tools.translate import _
from odoo.addons.website.models.website import slug
#from odoo.addons.web.controllers.main import login_redirect
import odoo.addons.website_sale.controllers.main as website_sale
from datetime import datetime


PPG = 20 # Products Per Page
PPR = 4  # Products Per Row


class WebsiteSale(website_sale.WebsiteSale):
 
    def checkout_form_save(self, checkout):
        
        cr, uid, context, registry = request.cr, request.uid, request.context, request.registry

        order = request.website.sale_get_order(force_create=1, context=context)

        orm_partner = registry.get('res.partner')
        orm_user = registry.get('res.users')
        order_obj = request.registry.get('sale.order')

        partner_lang = request.lang if request.lang in [lang.code for lang in request.website.language_ids] else None

        billing_info = {}
        if partner_lang:
            billing_info['lang'] = partner_lang
        billing_info.update(self.checkout_parse('billing', checkout, True))

        # set partner_id
        partner_id = None
        if request.uid != request.website.user_id.id:
            partner_id = orm_user.sudo().browse(uid).partner_id.id
        elif order.partner_id:
            user_ids = request.registry['res.users'].sudo().search([("partner_id", "=", order.partner_id.id)])
            if not user_ids or request.website.user_id.id not in user_ids:
                partner_id = order.partner_id.id

        # save partner informations
        if partner_id and request.website.partner_id.id != partner_id:
            #orm_partner.write(cr, SUPERUSER_ID, [partner_id], billing_info, context=context)
	    partner_obj = orm_partner.sudo().browse(partner_id)
	    partner_obj.sudo().write(billing_info)
        else:
            # create partner
            email = billing_info['email'].strip()
            partner_id = orm_partner.sudo().search([('email','=ilike',billing_info['email'])])
            if partner_id:
                partner_id = partner_id.id
                #orm_partner.write(cr, SUPERUSER_ID, partner_id, billing_info, context=context)
		partner_obj = orm_partner.sudo().browse(partner_id)
                partner_obj.sudo().write(billing_info)
            else:
                partner_id = orm_partner.sudo().create(billing_info)

        # create a new shipping partner
        if checkout.get('shipping_id') == -1:
            shipping_info = {}
            if partner_lang:
                shipping_info['lang'] = partner_lang
            shipping_info.update(self.checkout_parse('shipping', checkout, True))
            shipping_info['type'] = 'delivery'
            shipping_info['parent_id'] = partner_id
            checkout['shipping_id'] = orm_partner.sudo().create(shipping_info)

        order_info = {
            'partner_id': partner_id,
            'message_follower_ids': [(4, partner_id), (3, request.website.partner_id.id)],
            'partner_invoice_id': partner_id,
        }
        order_info.update(order_obj.onchange_partner_id(partner_id)['value'])
        address_change = order_obj.onchange_delivery_id(order.company_id.id, partner_id,
                                                        checkout.get('shipping_id'))['value']
        order_info.update(address_change)
        if address_change.get('fiscal_position'):
            fiscal_update = order_obj.onchange_fiscal_position(address_change['fiscal_position'],
                                                               [(4, l.id) for l in order.order_line])['value']
            order_info.update(fiscal_update)
        order_info.pop('user_id')
        order_info.update(partner_shipping_id=checkout.get('shipping_id') or partner_id)

        #order_obj.write(cr, SUPERUSER_ID, [order.id], order_info, context=context)
	order.sudo().write(order_info)
    
    @http.route('/shop/payment/validate', type='http', auth="public", website=True)
    def payment_validate(self, transaction_id=None, sale_order_id=None, **post):
        """ Method that should be called by the server when receiving an update
        for a transaction. State at this point :

         - UDPATE ME
        """
        cr, uid, context = request.cr, request.uid, request.context
        email_act = None
        sale_order_obj = request.env['sale.order']
        email_obj = request.env['mail.template']
        if transaction_id is None:
            tx = request.website.sale_get_transaction()
        else:
            tx = request.env['payment.transaction'].sudo().browse(transaction_id)

        if sale_order_id is None:
            order = request.website.sale_get_order()
        else:
            order = request.env['sale.order'].sudo().browse(sale_order_id)
            assert order.id == request.session.get('sale_last_order_id')

        if not order or (order.amount_total and not tx):
            return request.redirect('/shop')

        if (not order.amount_total and not tx) or tx.state in ['pending', 'done']:
            if (not order.amount_total and not tx):
                # Orders are confirmed by payment transactions, but there is none for free orders,
                # (e.g. free events), so confirm immediately
                order.action_button_confirm()
            # send by email
         #   email_act = sale_order_obj.action_quotation_send(cr, SUPERUSER_ID, [order.id], context=request.context)
            template_id = email_obj.sudo().search([('name','=',"CharterBooks Saleorder Email")])
            if template_id:
                mail_message = template_id.send_mail(order.id) #email_obj.sudo().send_mail(template_id[0],order.id)
        elif tx and tx.state == 'cancel':
            # cancel the quotation
            sale_order_obj.sudo().action_cancel([order.id])

        # send the email
        #if email_act and email_act.get('context'):
        #    composer_values = {}
        #    email_ctx = email_act['context']
        #    public_id = request.website.user_id.id
        #    if uid == public_id:
        #        composer_values['email_from'] = request.website.user_id.company_id.email
        #    composer_id = request.registry['mail.compose.message'].create(cr, SUPERUSER_ID, composer_values, context=email_ctx)
        #    request.registry['mail.compose.message'].send_mail(cr, SUPERUSER_ID, [composer_id], context=email_ctx)

        # clean context and session, then redirect to the confirmation page
        request.website.sale_reset()

        return request.redirect('/shop/confirmation')
