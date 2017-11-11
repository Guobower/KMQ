from odoo import fields,models,api,_
import requests
import json
import xmltodict
from datetime import datetime,date
import MySQLdb
import base64
import StringIO
from odoo.exceptions import UserError, RedirectWarning, ValidationError, Warning

epoch = datetime.utcfromtimestamp(0)

def unix_time_millis(dt):
    return (dt - epoch).total_seconds() * 1000.0

class delete_invoice(models.Model):
    _name = "delete.invoice"
    file = fields.Binary("Upload lead File here")

    def do_leads_import(self):
        file_name=self.file
        val=base64.decodestring(file_name)
        fp = StringIO.StringIO()
        fp.write(val)
        #wb = xlrd.open_workbook(file_contents=fp.getvalue())
        wb.sheet_names()
        sheet_name=wb.sheet_names()
        sh = wb.sheet_by_index(0)
        sh = wb.sheet_by_name(sheet_name[0])
        n_rows=sh.nrows
        #lead = self.pool.get('crm.lead')
        count = 0
        ctr = 0
	journals = []
        for r in range(0,n_rows):
              ctr+=1
              record = sh.row_values(r)
	      self._cr.execute("SELECT id FROM account_move WHERE name=%s", (str(record[0]),))
	      res = self._cr.fetchall()
	      if res:
		      for data in res:
			journals.append(data[0])
			

class my_dict2(dict):
        def __str__(self):
            return json.dumps(self)

class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'
    #quantity = fields.Integer(string="Quanitty",default=1)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        domain = {}
        if not self.invoice_id:
            return

        part = self.invoice_id.partner_id
        fpos = self.invoice_id.fiscal_position_id
        company = self.invoice_id.company_id
        currency = self.invoice_id.currency_id
        pricelist = self.invoice_id.pricelist_id
        type = self.invoice_id.type

        if not part:
            warning = {
                    'title': _('Warning!'),
                    'message': _('You must first select a partner!'),
                }
            return {'warning': warning}

        if not self.product_id:
            if type not in ('in_invoice', 'in_refund'):
                self.price_unit = 0.0
            domain['uom_id'] = []
        else:
            if part.lang:
                product = self.product_id.with_context(lang=part.lang)
            else:
                product = self.product_id

            self.name = product.partner_ref
            account = self.get_invoice_line_account(type, product, fpos, company)
            if account:
                self.account_id = account.id
            self._set_taxes()

            if type in ('in_invoice', 'in_refund'):
		if product.description_purchase:
                    self.name += '\n' + product.description_purchase
            else:
                if product.description_sale:
                    self.name += '\n' + product.description_sale

            if not self.uom_id or product.uom_id.category_id.id != self.uom_id.category_id.id:
                self.uom_id = product.uom_id.id
            domain['uom_id'] = [('category_id', '=', product.uom_id.category_id.id)]



            if pricelist:
                self.price_unit = self.product_id.with_context(pricelist=pricelist.id).price
                if self.uom_id and self.uom_id.id != product.uom_id.id:
                    self.price_unit = product.uom_id._compute_price(self.price_unit, self.uom_id)
        return {'domain': domain}

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def write(self, vals):
        res = super(AccountInvoice,self).write(vals)
        if vals.get('description') and 'SO' in self.origin:
            picking_objs = self.env['stock.picking'].search([('group_id.name','=',self.origin)])
            for obj in picking_objs:
                obj.description = self.description
        return res



    def _get_sale_order(self):
	sale_obj = self.env['sale.order']
	for data in self:
		sale_order_id = sale_obj.search([('name','=',data.origin)]).id
		if sale_order_id:
			data.sale_order_id = sale_order_id

    def _get_partner_code(self):
        for data in self:
                data.partner_code = data.partner_id and data.partner_id.ref or ''

    @api.multi
    def copy(self, default=None):
	auth_users = []
	andre_user = self.env['res.users'].search([('login','=','andre@kmq.co.za')])
        if andre_user:
        	andre_user_id = andre_user.id
		auth_users.append(andre_user_id)
	nancy_user = self.env['res.users'].search([('login','=','nancy@kmq.co.za')])
        if nancy_user:
                nancy_user_id = nancy_user.id
		auth_users.append(nancy_user_id)
	if self._uid not in auth_users:
                raise UserError(_('You are not authorized to updated quote lines.'))

        self.ensure_one()
        default['date_invoice'] = datetime.now().date()
        default = dict(default)
        return super(AccountInvoice, self).copy(default)


	
    account_product_branding_ids = fields.One2many('account.product.branding.lines','invoice_id','Branding Lines')
    associated_project = fields.Many2one('project.project','Associated Project')
    sale_order_id = fields.Many2one('sale.order',compute='_get_sale_order',string='Sale Order')
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', states={'draft': [('readonly', False)]}, help="Pricelist for current sales order.")
    partner_code = fields.Char(compute='_get_partner_code',string='Partner Code')
    description = fields.Text('Description')
    created_at_pastel = fields.Boolean('Created at Pastel')

    def unix_time_millis(dt):
	return (dt - epoch).total_seconds() * 1000.0


    def post_to_pastel(self):

	if not self.name and self.type == 'out_refund':
                raise UserError(_('Please add a reference for this Invoice.'))

        # lots of duplicate calls to action_invoice_open, so we remove those already open
	#res = super(AccountInvoice,self).action_invoice_open()
	headers = {"Content-type": "application/json"}
	client_data = {"username" : "Daniel"}
        client_data_resp = requests.post(url='http://letsap.dedicated.co.za/portmapping/CompanyList.asmx/GetCompanyList', headers=headers,  json=client_data)
        client_data_res = json.loads(client_data_resp.content)
	for data in client_data_res['d']:
		if data['Alias'] == 'PASTELCONNECT':
		        client_handle = data['ClientHandle'] 
			continue

	data = {"clientHandle" : client_handle, "customerID" : str(self.partner_id.parent_id and self.partner_id.parent_id.ref or self.partner_id.ref)}
	resp = requests.post(url='http://letsap.dedicated.co.za/Letsap.Framework.WebHost/KMQAPIService.svc/GetCustomer', headers=headers,  json=data)
        jd = json.loads(resp.content)
	resp_data = jd['GetCustomerResult']
	order_ref= ''
	if self.type == 'in_invoice':
		doctype = 8
		part_doc_type = "108"
		order_ref = self.reference
		#next_seq = self.env['ir.sequence'].next_by_code('Vendor Bills')
	elif self.type == 'out_invoice':
		doctype = 3
		part_doc_type = "103"
		order_ref=self.name
		#next_seq = self.env['ir.sequence'].next_by_code('Customer Invoices')
	elif self.type == 'out_refund':
                doctype = 4
                part_doc_type = "104"
		order_ref=self.origin
		#next_seq = self.env['ir.sequence'].next_by_code('Customer Refunds')
	elif self.type == 'in_refund':
                doctype = 9
                part_doc_type = "109"
		order_ref = self.origin
		#next_seq = self.env['ir.sequence'].next_by_code('Vendor Refunds')

	resp_inv_num = requests.post(url='http://letsap.dedicated.co.za/Letsap.Framework.WebHost/KMQAPIService.svc/GetNextDocumentNumber', headers=headers,json={'clientHandle':client_handle,'globalNumbers':True,'userid':1,'docType':doctype})
	jd_inv_num = json.loads(resp_inv_num.content)
	## Date Changes
	#self.date_invoice = datetime.now().date()
	a = datetime.strptime(str(self.date_invoice), '%Y-%m-%d')
	a = int(unix_time_millis(a))
	self._onchange_payment_term_date_invoice()
	b = datetime.strptime(str(self.date_due), '%Y-%m-%d')
        b = int(unix_time_millis(b))

	lt = []
	delivery_street = delivery_street2 = delivery_city = delivery_zip1 = delivery_state = delivery_country = state_name = country_name = ''
	if self.partner_shipping_id:
                if self.partner_shipping_id.state_id:
                        state_name = self.env['res.country.state'].search([('id','=',self.partner_shipping_id.state_id.id)]).name
                if self.partner_shipping_id.country_id:
                        country_name = self.env['res.country'].search([('id','=',self.partner_shipping_id.country_id.id)]).name
                delivery_street = self.partner_shipping_id.street
                delivery_street2 = self.partner_shipping_id.street2
                delivery_city = self.partner_shipping_id.city
                delivery_state = state_name
                delivery_country = country_name
                delivery_zip1 = self.partner_shipping_id.zip
	## ENd
	part_period_dic = {'Mar':101,'Apr':102,'May':103,'Jun':104,'Jul':105,'Aug':106,'Sep':107,'Oct':108,'Nov':109,'Dec':110,'Jan':111,'Feb':112}
	invoice_month = datetime.strptime(str(self.date_invoice),'%Y-%m-%d').strftime('%b')
	part_period_code = part_period_dic[invoice_month]
	if jd_inv_num:
		inv_number = jd_inv_num['GetNextDocumentNumberResult']
		documentfullmodel = { "_documentID": "00000000-0000-0000-0000-000000000000",    "_userID": "00000000-0000-0000-0000-000000000000",    "_documentType": part_doc_type,    "_documentNumber": str(self.number),    "_updated":False,    "_documentDate": "/Date("+str(a)+"+0200"+")/",    "_paymentDueDate": "/Date("+str(b)+"+0200"+")/",    "_orderNumber": str(order_ref),    "_salesmanCode": str(self.user_id and self.user_id.partner_id.ref),    "_inclusiveInput": False,    "_forceTax": 0,    "_forceTaxType": 0,    "_message": "|||",    "_postalAddress": "||||",    "_deliveryAddress": "||||",    "_telephone": "",    "_fax": "",    "_email": "",    "_contact": "", "_project": "", " _currencyCode":0,    "_exchangeRate": 1,    "_discountPercent": 0,    "_settlementTerms": "0",    "_dayBased": False,    "_paymentTerms": 0,   "_localExc": 0,    "_foreignExc": 0,    "_localDiscount": 0,   "_foreignDiscount": 0,    "_localTax": 0,    "_foreignTax": 0,    "_localInc": 0,    "_foreignInc": 0,    "_costPrice": 0,    "_deleted": False,    "_printed": False,    "_onHold": False,    "_cOD": False,    "_packed": False,   "_emailed": False,    "_packingMethod": "",    "_deliveryMethod": "",    "_note": "",    "_needsAuthorisation": False,    "_uploadedToServer": False,    "_downloadedToTerminal": False,    "_terminalID": 0,   "_creditNoteReason": "",    "_freight": "",    "_ship": "",    "_updatedOn": "/Date("+str(a)+"+0200"+")/",    "_createDate": "/Date("+str(a)+"+0200"+")/",    "_documentLines": None,    "_users": None,   "_documentPayment": None,    "_partnerCusomerCode": str(self.partner_id.parent_id and self.partner_id.parent_id.ref or self.partner_id.ref),    "_partnerAccountCode": str(self.name),    "_partnerPeriod": part_period_code , "_currencyCode": 0}
		arrayofdocumentlinefullmodel = []
		inv_created = False
		for line in self.invoice_line_ids:
			#if self.type not in ['out_invoice','in_invoice','in_refund']:
			#	line.price_unit = -(line.price_unit)
			val = {}
			resp_getitem_code = requests.post(url='http://letsap.dedicated.co.za/Letsap.Framework.WebHost/KMQAPIService.svc/GetItem', headers=headers,json={'clientHandle':client_handle,'itemID':str(line.product_id.default_code)})
			product_id = json.loads(resp_getitem_code.content)
			val["_documentLineID"] =  "00000000-0000-0000-0000-000000000000"
			val["_documentID"] = "00000000-0000-0000-0000-000000000000"
			val["_lineNumber"] = 0
			val["_storeID"] = "00000000-0000-0000-0000-000000000000"
			val["_itemID"] = product_id['GetItemResult']['_itemID']
			val["_description"] = str(line.name)
			val["_unit"] = ""
			val["_salesmanID"] = "00000000-0000-0000-0000-000000000000"
			val["_forceTax"]= False
                        val["_taxType"]= 1
                        val["_taxPercent"]= "14"
			val["_discountType"] = 0
			val["_costPrice"] = line.price_unit
			val["_quantity"] = int(line.quantity)
			val["_packSizeCode"] = ""
			val["_packSizeQty"] = 0
			val["_partnerStorecode"] = "001"
			val["_discountType"]= 0 
			val["_quantityLeft"]= int(line.quantity)
			val["_packSizeCode"]= ""
			val["_packSizeQty"]= 0
			val["_packSizeRatio"]= 0
			val["_batchSerialItem"]= False
			val["_length"]= 0
			val["_width"]= 0
			val["_height"]= 0
			val["_weight"]= 0
			val["_squareMeterPrice"]= 0
			val["_localExclusivePrice"]= 0
			val["_localInclusivePrice"]= 0
			val["_foreignExclusivePrice"]= line.price_unit or 0.0
			val["_foreignInclusivePrice"]= 0
			val["_localTaxAmount"]= 0
			val["_foreignTaxAmount"]= 0
			val["_discountPercent"]= 0
			val["_localDiscountAmount"]= 0
			val["_foreignDiscountAmount"]= 0
			val["_localExcNetAmount"]= 0
			val["_localIncNetAmount"]= 0
			val["_foreignExcNetAmount"]= 0
			val["_foreignIncNetAmount"]= 0
			val["_linkLineNumber"]= 0
			val["_linkDocumentType"]= 0
			val["_linkDocumentNumber"]= ""
			val["_changeUnitAndQty"]= False
			val["_changeDescription"]= False
			val["_uploadedToServer"]= False
			val["_downloadedToTerminal"]= False
			val["_terminalID"]= 0
			val["_picture"] = []
			val["_partnerProductCode"] = str(line.product_id.default_code)
			val["_partnerCustomerCode"] = str(self.partner_id.ref)
			val["_partnerSalesmanCode"] = ""
			val["_partnerPeriod"] = part_period_code
			val["_partnerDocumentDate"] =  "/Date(1490172598000+0200)/"
			val["_partnerVersion"] = 10
			val["_partnerItemCategory"] = ""
			val["_partnerDocumentType"] = part_doc_type
			val["_partnerDocumentNumber"] = str(self.number)
			val["_partnerFixedDescription"] = False
			val["_partnerServiceItem"] = False
			val["_partnerShowUnitQty"] = True
			val["_partnerRowType"] = 0
			val["_partnerRowSelected"] = False
			val["_partnerOldQty"] = 0
			val["_lineType"] = 1
			val["_project"] = None
			arrayofdocumentlinefullmodel.append(val)

		inv_dict = {
				"clientHandle" : client_handle, 
				"documentFM" : documentfullmodel, 
				"documentLinesFM" : arrayofdocumentlinefullmodel, 
				"globalNumbers" : True, 
				"userId" : 0, 
				"emailPDFDoc" : True, 
				"emailAddress" : ""
		}
		
		try:
			url = "http://letsap.dedicated.co.za/Letsap.Framework.WebHost/KMQAPIService.svc/GetTestConnection/"+str(client_handle)
			conn = requests.get(url)
			if conn.status_code == 200:
				resp_inv_create = requests.post(url='http://letsap.dedicated.co.za/Letsap.Framework.WebHost/KMQAPIService.svc/SaveDocument', headers=headers,json=my_dict2(inv_dict))
				inv_created = True
				self.created_at_pastel = True
		
		except Exception,e:
			print "Exception is:",e


    @api.multi
    def action_invoice_open(self):
        if not self.name and self.type == 'out_refund':
            raise UserError(_('Please add a reference for this Invoice.'))

        # lots of duplicate calls to action_invoice_open, so we remove those already open
        res = super(AccountInvoice,self).action_invoice_open()
        headers = {"Content-type": "application/json"}
        client_data = {"username" : "Daniel"}
        client_data_resp = requests.post(url='http://letsap.dedicated.co.za/portmapping/CompanyList.asmx/GetCompanyList', headers=headers,  json=client_data)
        client_data_res = json.loads(client_data_resp.content)
        for data in client_data_res['d']:
            if data['Alias'] == 'PASTELTEST-PC':
                client_handle = data['ClientHandle'] 
                continue
#     	for data in client_data_res['d']:
#     		if data['Alias'] == 'PASTELCONNECT':
# 		        client_handle = data['ClientHandle'] 
#     			continue

        data = {"clientHandle" : client_handle, "customerID" : str(self.partner_id.parent_id and self.partner_id.parent_id.ref or self.partner_id.ref)}
        resp = requests.post(url='http://letsap.dedicated.co.za/Letsap.Framework.WebHost/KMQAPIService.svc/GetCustomer', headers=headers,  json=data)
        jd = json.loads(resp.content)
        resp_data = jd['GetCustomerResult']
        order_ref= ''
        if self.type == 'in_invoice':
            doctype = 8
            part_doc_type = "108"
            order_ref = self.reference
            #next_seq = self.env['ir.sequence'].next_by_code('Vendor Bills')
        elif self.type == 'out_invoice':
            doctype = 3
            part_doc_type = "103"
            order_ref=self.name
            #next_seq = self.env['ir.sequence'].next_by_code('Customer Invoices')
        elif self.type == 'out_refund':
            doctype = 4
            part_doc_type = "104"
            order_ref=self.origin
            #next_seq = self.env['ir.sequence'].next_by_code('Customer Refunds')
        elif self.type == 'in_refund':
            doctype = 9
            part_doc_type = "109"
            der_ref = self.origin
        #next_seq = self.env['ir.sequence'].next_by_code('Vendor Refunds')

        ## Date Changes
        #self.date_invoice = datetime.now().date()
        a = datetime.strptime(str(self.date_invoice), '%Y-%m-%d')
        a = int(unix_time_millis(a))
        self._onchange_payment_term_date_invoice()
        b = datetime.strptime(str(self.date_due), '%Y-%m-%d')
        b = int(unix_time_millis(b))

        lt = []
        delivery_street = delivery_street2 = delivery_city = delivery_zip1 = delivery_state = delivery_country = state_name = country_name = ''
        if self.partner_shipping_id:
            if self.partner_shipping_id.state_id:
                    state_name = self.env['res.country.state'].search([('id','=',self.partner_shipping_id.state_id.id)]).name
            if self.partner_shipping_id.country_id:
                    country_name = self.env['res.country'].search([('id','=',self.partner_shipping_id.country_id.id)]).name
            delivery_street = self.partner_shipping_id.street
            delivery_street2 = self.partner_shipping_id.street2
            delivery_city = self.partner_shipping_id.city
            delivery_state = state_name
            delivery_country = country_name
            delivery_zip1 = self.partner_shipping_id.zip
    ## ENd
        part_period_dic = {'Mar':101,'Apr':102,'May':103,'Jun':104,'Jul':105,'Aug':106,'Sep':107,'Oct':108,'Nov':109,'Dec':110,'Jan':111,'Feb':112}
        invoice_month = datetime.strptime(str(self.date_invoice),'%Y-%m-%d').strftime('%b')
        part_period_code = part_period_dic[invoice_month]
        if self.number:
            inv_number = self.number #jd_inv_num['GetNextDocumentNumberResult']
            documentfullmodel = { "_documentID": "00000000-0000-0000-0000-000000000000",    "_userID": "00000000-0000-0000-0000-000000000000",    "_documentType": part_doc_type,    "_documentNumber": str(self.number),    "_updated":False,    "_documentDate": "/Date("+str(a)+"+0200"+")/",    "_paymentDueDate": "/Date("+str(b)+"+0200"+")/",    "_orderNumber": str(order_ref),    "_salesmanCode": str(self.user_id and self.user_id.partner_id.ref),    "_inclusiveInput": False,    "_forceTax": 0,    "_forceTaxType": 0,    "_message": "|||",    "_postalAddress": "||||",    "_deliveryAddress": "||||",    "_telephone": "",    "_fax": "",    "_email": "",    "_contact": "", "_project": "", " _currencyCode":0,    "_exchangeRate": 1,    "_discountPercent": 0,    "_settlementTerms": "0",    "_dayBased": False,    "_paymentTerms": 0,   "_localExc": 0,    "_foreignExc": 0,    "_localDiscount": 0,   "_foreignDiscount": 0,    "_localTax": 0,    "_foreignTax": 0,    "_localInc": 0,    "_foreignInc": 0,    "_costPrice": 0,    "_deleted": False,    "_printed": False,    "_onHold": False,    "_cOD": False,    "_packed": False,   "_emailed": False,    "_packingMethod": "",    "_deliveryMethod": "",    "_note": "",    "_needsAuthorisation": False,    "_uploadedToServer": False,    "_downloadedToTerminal": False,    "_terminalID": 0,   "_creditNoteReason": "",    "_freight": "",    "_ship": "",    "_updatedOn": "/Date("+str(a)+"+0200"+")/",    "_createDate": "/Date("+str(a)+"+0200"+")/",    "_documentLines": None,    "_users": None,   "_documentPayment": None,    "_partnerCusomerCode": str(self.partner_id.parent_id and self.partner_id.parent_id.ref or self.partner_id.ref),    "_partnerAccountCode": str(self.name),    "_partnerPeriod":  part_period_code, "_currencyCode": 0}
            arrayofdocumentlinefullmodel = []
            inv_created = False
            for line in self.invoice_line_ids:
                #if self.type not in ['out_invoice','in_invoice','in_refund']:
                #	line.price_unit = -(line.price_unit)
                val = {}
                resp_getitem_code = requests.post(url='http://letsap.dedicated.co.za/Letsap.Framework.WebHost/KMQAPIService.svc/GetItem', headers=headers,json={'clientHandle':client_handle,'itemID':str(line.product_id.default_code)})
                product_id = json.loads(resp_getitem_code.content)
                val["_documentLineID"] =  "00000000-0000-0000-0000-000000000000"
                val["_documentID"] = "00000000-0000-0000-0000-000000000000"
                val["_lineNumber"] = 0
                val["_storeID"] = "00000000-0000-0000-0000-000000000000"
                val["_itemID"] = product_id['GetItemResult']['_itemID']
                val["_description"] = str(line.name)
                val["_unit"] = ""
                val["_salesmanID"] = "00000000-0000-0000-0000-000000000000"
                val["_forceTax"]= False
                val["_taxType"]= 1
                val["_taxPercent"]= "14"
                val["_discountType"] = 0
                val["_costPrice"] = line.price_unit
                val["_quantity"] = int(line.quantity)
                val["_packSizeCode"] = ""
                val["_packSizeQty"] = 0
                val["_partnerStorecode"] = "001"
                val["_discountType"]= 0 
                val["_quantityLeft"]= int(line.quantity)
                val["_packSizeCode"]= ""
                val["_packSizeQty"]= 0
                val["_packSizeRatio"]= 0
                val["_batchSerialItem"]= False
                val["_length"]= 0
                val["_width"]= 0
                val["_height"]= 0
                val["_weight"]= 0
                val["_squareMeterPrice"]= 0
                val["_localExclusivePrice"]= 0
                val["_localInclusivePrice"]= 0
                val["_foreignExclusivePrice"]= line.price_unit or 0.0
                val["_foreignInclusivePrice"]= 0
                val["_localTaxAmount"]= 0
                val["_foreignTaxAmount"]= 0
                val["_discountPercent"]= 0
                val["_localDiscountAmount"]= 0
                val["_foreignDiscountAmount"]= 0
                val["_localExcNetAmount"]= 0
                val["_localIncNetAmount"]= 0
                val["_foreignExcNetAmount"]= 0
                val["_foreignIncNetAmount"]= 0
                val["_linkLineNumber"]= 0
                val["_linkDocumentType"]= 0
                val["_linkDocumentNumber"]= ""
                val["_changeUnitAndQty"]= False
                val["_changeDescription"]= False
                val["_uploadedToServer"]= False
                val["_downloadedToTerminal"]= False
                val["_terminalID"]= 0
                val["_picture"] = []
                val["_partnerProductCode"] = str(line.product_id.default_code)
                val["_partnerCustomerCode"] = str(self.partner_id.ref)
                val["_partnerSalesmanCode"] = ""
                val["_partnerPeriod"] = part_period_code
                val["_partnerDocumentDate"] =  "/Date(1490172598000+0200)/"
                val["_partnerVersion"] = 10
                val["_partnerItemCategory"] = ""
                val["_partnerDocumentType"] = part_doc_type
                val["_partnerDocumentNumber"] = str(self.number)
                val["_partnerFixedDescription"] = False
                val["_partnerServiceItem"] = False
                val["_partnerShowUnitQty"] = True
                val["_partnerRowType"] = 0
                val["_partnerRowSelected"] = False
                val["_partnerOldQty"] = 0
                val["_lineType"] = 1
                val["_project"] = None
                arrayofdocumentlinefullmodel.append(val)

        inv_dict = {
            "clientHandle" : client_handle, 
            "documentFM" : documentfullmodel, 
            "documentLinesFM" : arrayofdocumentlinefullmodel, 
            "globalNumbers" : True, 
            "userId" : 0, 
            "emailPDFDoc" : True, 
            "emailAddress" : ""
        }

        try:
            url = "http://letsap.dedicated.co.za/Letsap.Framework.WebHost/KMQAPIService.svc/GetTestConnection/"+str(client_handle)
            conn = requests.get(url)
            if conn.status_code == 200:
                resp_inv_create = requests.post(url='http://letsap.dedicated.co.za/Letsap.Framework.WebHost/KMQAPIService.svc/SaveDocument', headers=headers,json=my_dict2(inv_dict))
                inv_created = True
                resp_inv_create_content = json.loads(resp_inv_create.content)
                if resp_inv_create_content.get('SaveDocumentResult') and resp_inv_create_content.get('SaveDocumentResult') == inv_number:
                    self.created_at_pastel = True

                self.message_post(body=resp_inv_create_content)
                if not self.created_at_pastel:
                    raise Warning(
                                  _("Cannot Validate Invoice: %s")% (resp_inv_create_content.get('SaveDocumentResult')))

        except Exception,e:
            print "Exception is:",e
            self.message_post(body=e)
            raise Warning(
                          _("Cannot Validate Invoice: %s")% (resp_inv_create_content.get('SaveDocumentResult')))

        return res 


    #Jagadeesh start
    ''' for report customizations'''
    @api.multi
    def get_product_branding_items(self,line):
        branding_lines = self.env['account.product.branding.lines'].search([('invoice_id','=',line.invoice_id.id),('product_id','=',line.product_id.id)])
        return branding_lines
    #Jagadeesh end



    @api.one
    @api.depends('invoice_line_ids.price_subtotal','account_product_branding_ids.total_cost','tax_line_ids.amount', 'currency_id', 'company_id', 'date_invoice')
    def _compute_amount(self):

	#total_brands_amount = sum(rec.total_cost for rec in self.account_product_branding_ids) #Jagadeesh
        self.amount_untaxed = sum(line.price_subtotal for line in self.invoice_line_ids)#+total_brands_amount #Jagadeesh
        self.amount_tax = sum(line.amount for line in self.tax_line_ids)
        self.amount_total = self.amount_untaxed + self.amount_tax
        amount_total_company_signed = self.amount_total
        amount_untaxed_signed = self.amount_untaxed
        if self.currency_id and self.currency_id != self.company_id.currency_id:
            currency_id = self.currency_id.with_context(date=self.date_invoice)
            amount_total_company_signed = currency_id.compute(self.amount_total, self.company_id.currency_id)
            amount_untaxed_signed = currency_id.compute(self.amount_untaxed, self.company_id.currency_id)
        sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
        self.amount_total_company_signed = amount_total_company_signed * sign
        self.amount_total_signed = self.amount_total * sign
        self.amount_untaxed_signed = amount_untaxed_signed * sign


    @api.multi
    def get_taxes_values(self):
        ''' overrided base method '''
        tax_grouped = {}
        for line in self.invoice_line_ids:
            price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.invoice_line_tax_ids.compute_all(price_unit, self.currency_id, line.quantity, line.product_id, self.partner_id)['taxes']

            for tax in taxes:
                #Jagadeesh oct 27
                if tax['name'] == 'Tax 14.00%':
                    tax['amount'] = (tax['base'] * 14) / 100
                #Jagadeesh oct 27
                val = self._prepare_tax_line_vals(line, tax)
                key = self.env['account.tax'].browse(tax['id']).get_grouping_key(val)

                if key not in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base'] += val['base']
        return tax_grouped



class AccountProductBrandingLines(models.Model):
        _name = 'account.product.branding.lines'

        branding_location = fields.Many2one('branding.location','Branding Location')
        branding_method = fields.Many2one('branding.method','Branding Method')
        #product_id = fields.Many2one('product.template','Product')
        product_id = fields.Many2one('product.product','Product') #Jagadeesh
        color_variant = fields.Many2one('color.variants','Colours')
        size_variant = fields.Many2one('size.variants','Sizes')
        setup_cost = fields.Float('Setup Cost')
        item_cost = fields.Float('Cost/Item')
        total_cost = fields.Float('Total Cost')
        invoice_id = fields.Many2one('account.invoice','Invoice/Bill')
        invoice_line_id = fields.Many2one('account.invoice.line','Invoice/Bill')

#Jagadeesh start
class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.multi
    def post(self):
	user = self.env['res.users'].browse(self._context['uid'])
        group = self.env['res.groups'].search([('name', '=', 'Payment Registration Group')])
        if user not in group.users:
                raise UserError(_('Only users from Payment Registration Group are allowed to process payment.'))

        res = super(AccountPayment,self).post()
        inv_obj = self.env['account.invoice'].browse(self._context.get('active_id'))
        sale_obj = self.env['sale.order'].search([('name','=',inv_obj.origin)])
        if sale_obj.partner_id.account_type == 'cod' and inv_obj.state == 'paid':
            stock_picks = self.env['stock.picking'].search([('group_id','=',sale_obj.procurement_group_id.id)])
            for stock in stock_picks:
                if stock.picking_type_id.name == 'Delivery Orders' and stock.state == 'waiting':
                    stock.state = 'assigned'

	a = datetime.strptime(str(self.payment_date), '%Y-%m-%d')
        a = int(unix_time_millis(a))

	headers = {"Content-type": "application/json"}
        client_data = {"username" : "Daniel"}
        client_data_resp = requests.post(url='http://letsap.dedicated.co.za/portmapping/CompanyList.asmx/GetCompanyList', headers=headers,  json=client_data)
        client_data_res = json.loads(client_data_resp.content)
	if inv_obj.type in ['out_invoice']:
        	ref_amount = float(-(self.amount))
	else:
		ref_amount = float(self.amount)

        for data in client_data_res['d']:
                if data['Alias'] == 'PASTELCONNECT':
                        client_handle = data['ClientHandle']
                        continue
	if self.journal_id.name == 'Credit Card Clearing':
		journal = 2
		journal_v = 1

	elif self.journal_id.name == 'Petty Cash Andre':
		journal = 10
		journal_v = 9

	elif self.journal_id.name == 'Nedbank Current Account':
                journal = 15
		journal_v = 16

	elif self.journal_id.name == 'Standard Bank Current Acc':
                journal = 19
		journal_v = 20

	elif self.journal_id.name == 'ABSA Curr Acc':
                journal = 21
		journal_v = 22

	elif self.journal_id.name == 'FNB Curr Acc':
                journal = 23
		journal_v = 24
	elif self.journal_id.name == 'Nedbank Payment Acc':
                journal = 25
		journal_v = 26

	if inv_obj.type == 'out_refund':
		entry_type_num = journal

        data_send = {
		"clientHandle" : client_handle,
                "EntryTypeNumber" : journal_v if inv_obj.type == 'in_invoice' else journal,
                "UserID" : user.user_pastel_id,
                "Period" : 7,
                "Date" : str(date.today().strftime("%Y-%m-%d")),#"/Date("+str(a)+"+0200"+")/",
                "GDC" : "C",
                "AccNumber" : str(inv_obj.partner_id.parent_id and inv_obj.partner_id.parent_id.ref or inv_obj.partner_id.ref),
                "Ref" : "", #str(self.communication),
                "Description" : str(inv_obj.partner_id.parent_id and inv_obj.partner_id.parent_id.name or inv_obj.partner_id.name), #str(self.name),
                "Amount" : float(ref_amount),
                "TaxType" : 0,
                "TaxAmount" : 0,
                "OIType" : "",
                "JobCode" : "",
                "MatchRef" : "",
                "DiscAmount" : 0,
                "DiscTType" : 0,
                "ContraAcc" : "",
                "ExchangeRate" : 1,
                "BExchangeRate" : 1,

                }
	data_receive = {
                "clientHandle" : str(client_handle),
                "EntryTypeNumber" : journal if inv_obj.type in ['out_refund','out_invoice'] else journal_v, # journal,
                "UserID" : user.user_pastel_id,
                "Period" : 7,
                "Date" : str(date.today().strftime("%Y-%m-%d")), #"/Date("+str(a)+"+0200"+")/",
                "GDC" : "D",
                "AccNumber" : str(inv_obj.partner_id.parent_id and inv_obj.partner_id.parent_id.ref or inv_obj.partner_id.ref),
                "Ref" : "", #str(self.communication),
                "Description" : str(inv_obj.partner_id.parent_id and inv_obj.partner_id.parent_id.name or inv_obj.partner_id.name), #str(self.name),
                "Amount" : float(ref_amount),
                "TaxType" : 0,
                "TaxAmount" : 0,
                "OIType" : "",
                "JobCode" : "",
                "MatchRef" : "",
                "DiscAmount" : 0,
                "DiscTType" : 0,
                "ContraAcc" : "",
                "ExchangeRate" : 1,
                "BExchangeRate" :1,
                }
        try:
            if inv_obj.type in ['in_invoice']:
                resp = requests.post(url='http://letsap.dedicated.co.za/Letsap.Framework.WebHost/KMQAPIService.svc/ImportGLBatch', headers=headers,json=my_dict2(data_send))

            elif inv_obj.type in ['out_invoice','out_refund']:
            	resp = requests.post(url='http://letsap.dedicated.co.za/Letsap.Framework.WebHost/KMQAPIService.svc/ImportGLBatch', headers=headers,json=my_dict2(data_receive))

        except Exception,e:
                print "Exception is:",e

        return res

class AccountPaymentTerm(models.Model):
	_inherit = 'account.payment.term'
	_order = 'term_value asc'
	@api.multi
	def _get_term_value(self):
		if self.name:
			if self.name == '30':
				self.term_value = 30
			if self.name == '60':
                                self.term_value = 60
			if self.name == '90':
                                self.term_value = 90
			if self.name == '120':
                                self.term_value = 120
			if self.name == 'Immediate Payment':
                                self.term_value = 0
	term_value = fields.Integer(compute ='_get_term_value',string='Term Value')



