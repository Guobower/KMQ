# -*- coding: utf-8 -*-
from odoo import models, api


class sale_order(models.Model):
    _inherit = "sale.order"

    @api.multi
    def check_credit_limit_ok(self):
	#print 'credit limit ok================='
        self.ensure_one()

        domain = [
            ('order_id.id', '!=', self.id),
            ('order_id.partner_id', '=', self.partner_id.id),
            ('order_id.state', 'in', ['sale', 'done'])]
        order_lines = self.env['sale.order.line'].search(domain)

        # We sum from all the sale orders that are aproved, the sale order
        # lines that are not yet invoiced
	#print 'order lines=============',order_lines
        to_invoice_amount = 0.0
        for line in order_lines:
            # not_invoiced is different from native qty_to_invoice because
            # the last one only consider to_invoice lines the ones
            # that has been delivered or are ready to invoice regarding
            # the invoicing policy. Not_invoiced consider all

            not_invoiced = line.product_uom_qty - line.qty_invoiced
	    #print 'not invoiced=================',not_invoiced
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(
                price, line.order_id.currency_id,
                not_invoiced,
                product=line.product_id, partner=line.order_id.partner_id)
	    #print 'taxes==============',taxes
            to_invoice_amount += taxes['total_included']
	    #print 'to inv amt==============',to_invoice_amount

        # We sum from all the invoices lines that are in draft and not linked
        # to a sale order
        domain = [
            ('invoice_id.partner_id', '=', self.partner_id.id),
            ('invoice_id.state', '=', 'draft'),
            ('sale_line_ids', '=', False)]
        draft_invoice_lines = self.env['account.invoice.line'].search(domain)
        draft_invoice_lines_amount = 0.0
	#print 'draft inv lines==================',draft_invoice_lines
        for line in draft_invoice_lines:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
	    #print 'price=============',price
            taxes = line.invoice_line_tax_ids.compute_all(
                price, line.invoice_id.currency_id,
                line.quantity,
                product=line.product_id, partner=line.invoice_id.partner_id)
	    #print 'taxes==============',taxes
            draft_invoice_lines_amount += taxes['total_included']
	    #print 'drfat inv lines amt=============',draft_invoice_lines_amount

        available_credit = self.partner_id.credit_limit - \
            self.partner_id.credit - \
            to_invoice_amount - draft_invoice_lines_amount
	#print 'values==============',self.partner_id.credit_limit,self.partner_id.credit,to_invoice_amount,draft_invoice_lines_amount
	#print 'val22222222===================',self.amount_total,available_credit
        if self.amount_total > available_credit:
            return False
        return True
