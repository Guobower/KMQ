import json
from lxml import etree
from datetime import datetime,date
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
# import xmltodict
epoch = datetime.utcfromtimestamp(0)

def unix_time_millis(dt):
    return (dt - epoch).total_seconds() * 1000.0

class mydict(dict):
        def __str__(self):
            return json.dumps(self) 
			
class ResPartner(models.Model):
    _inherit = 'res.partner'

    payment_deposit = fields.Integer('Payment Deposit %')
    created_at_pastel = fields.Boolean('Created at Pastel?')
    ref = fields.Char(string='Internal Reference', index=True,required=True,size=6)
    fax = fields.Char('Fax')
    is_company = fields.Boolean(string='Is a Company', default=True,
        help="Check if the contact is a company, otherwise it is a person")

    

    _sql_constraints = [
        ('customer_ref_uniq', 'unique (ref)', 'The reference of the customer must be unique!')
    ]

    @api.multi
    def action_partner_unblock(self,ids):
	print "inside action_partner_unblock",ids
	for part_id in ids:
		self._cr.execute("""UPDATE res_partner set account_blocked=False where id = %s""",(part_id,))
	#return True


    @api.multi
    def block_account(self):
	
	print 'block=========='
	group_ids = self.env['res.groups'].search([('name', '=', 'Allow Blocking Accounts')]).users.ids
	if self.env.uid not in group_ids:
	    raise ValidationError("You are not allowed to Block/Unblock accounts")

	
	self.account_blocked = True
	#self.update_account_blocking(block=True)
	return True

    @api.multi
    def update_account_blocking(self,block):
    
	headers = {"Content-type": "application/json"}
        client_data = {"username" : "Daniel"}
        client_data_resp = requests.post(url='http://letsap.dedicated.co.za/portmapping/CompanyList.asmx/GetCompanyList', headers=headers,  json=client_data)
        client_data_res = json.loads(client_data_resp.content)
        client_handle = client_data_res['d'][0]['ClientHandle']

        requestData = {"clientHandle":str(client_handle),"customerID":str(self.ref)}
        partner_data_resp = requests.post(url='http://letsap.dedicated.co.za/Letsap.Framework.WebHost/KMQAPIService.svc/GetCustomer', headers=headers,  json=requestData)
        final_data = json.loads(partner_data_resp.content)
        #if final_data['GetCustomerResult']['_partnerAddress'] and final_data['GetCustomerResult']['_partnerAddress']:
        #        create_date = final_data['GetCustomerResult']['_partnerAddress']['_createDate']
		
        #else:
        #        create_date = final_data['GetCustomerResult']['_createDate']
	if final_data.has_key('GetCustomerResult'):
            final_data['GetCustomerResult']['_blocked'] = block
            test = block
        elif final_data.has_key('GetSupplierResult'):
            final_data['GetSupplierResult']['_blocked'] = block
            test = block

        if self.company_type == 'company' and self.customer:
            data = {"clientHandle": str(client_handle),"Customer":final_data['GetCustomerResult']}
        elif self.company_type == 'company' and self.supplier:
            data = {"clientHandle": str(client_handle),"supplier":final_data['GetSupplierResult']}


	try:
                url = "http://letsap.dedicated.co.za/Letsap.Framework.WebHost/KMQAPIService.svc/GetTestConnection/"+str(client_handle)
                conn = requests.get(url)
                if conn.status_code == 200:
		     save_customer = requests.post(url='http://letsap.dedicated.co.za/Letsap.Framework.WebHost/KMQAPIService.svc/SaveCustomer', headers=headers,json=mydict(data))
	except Exception,e:
                print "Exception is:",e


	return True

    @api.multi
    def unblock_account(self):
        print 'unblock=========='
	group_ids = self.env['res.groups'].search([('name', '=', 'Allow Blocking Accounts')]).users.ids
        if self.env.uid not in group_ids:
            raise ValidationError("You are not allowed to Block/Unblock accounts")
	self.account_blocked = False
	#self.update_account_blocking(block=False)
        return True


    @api.multi
    def copy(self, default=None):
        self.ensure_one()
        default['ref'] = ''
        default = dict(default or {}, name=_('%s (copy)') % self.name)
        return super(ResPartner, self).copy(default)


    @api.onchange('ref')
    def onchange_ref(self):
	if self.ref:
		existing_ref = self.search([('ref','=',self.ref)])
		if existing_ref:
			raise UserError(_('Entered reference number already exist.'))
    @api.model
    def create(self,vals):
	if self._context.has_key('default_customer') or self._context.has_key('default_supplier') or self._context.has_key('search_default_customer') or self._context.has_key('search_default_supplier'):
		group = self.env['res.groups'].search([('name', '=', 'Accounts(Customers) Creation group')])
		user = self.env['res.users'].browse(self._uid)
        	if user not in group.users:
	        	raise UserError(_('Only users from Accounts(Customers) Creation group are allowed to create customer.'))

	res = super(ResPartner,self).create(vals)
	return res
		

    """@api.model
    def create(self,vals):
        #if vals.has_key('parent_id') and vals['parent_id'] == False:
       	salesman_code = False
	if not vals.has_key('child_ids') and not vals['parent_id']:
		raise UserError(_('Please add a contact for the customer.'))
	if vals.has_key('user_id') and vals['user_id']:
		salesman_code = self.env['res.users'].browse(vals['user_id']).partner_id.ref 
	headers = {"Content-type": "application/json"}
	conn = requests.post(url='http://letsap.dedicated.co.za/Letsap.Framework.WebHost/KMQAPIService.svc/GetTestConnection', headers=headers)
        client_data = {"username" : "Daniel"}
        client_data_resp = requests.post(url='http://letsap.dedicated.co.za/portmapping/CompanyList.asmx/GetCompanyList', headers=headers,  json=client_data)
        client_data_res = json.loads(client_data_resp.content)
        client_handle = client_data_res['d'][0]['ClientHandle'] 

	a = datetime.strptime(str(datetime.now().date()), '%Y-%m-%d')
        a = int(unix_time_millis(a))
        
	postal_add = delev_add = cell = contact = email = fax = telephone = duv2 = sup2 = ' '
        if vals.has_key('zip') and vals['zip']:
                zip1 = str(vals['zip']) or ''
	if vals.has_key('child_ids') and vals['child_ids']:
	    for val in vals['child_ids']:
	        if val[2]['type']=='invoice':
		    if val[2].has_key('state_id'):
			state_name = self.env['res.country.state'].search([('id','=',val[2]['state_id'])]).name
		    if val[2].has_key('country_id'):
			country_name = self.env['res.country'].search([('id','=',val[2]['country_id'])]).name
	            postal_street = val[2]['street']
        	    postal_street2 = val[2]['street2']
                    postal_city = val[2]['city']
	            postal_state = state_name
        	    postal_country = country_name
                    postal_zip1 = val[2]['zip']
		    postal_add = postal_street+","+ postal_street2+","+ postal_city+","+ postal_state+","+ postal_country+","+ postal_zip1
		    
                if val[2]['type']=='delivery':
                    if val[2].has_key('state_id'):
                        state_name = self.env['res.country.state'].search([('id','=',val[2]['state_id'])]).name
                    if val[2].has_key('country_id'):
                        country_name = self.env['res.country'].search([('id','=',val[2]['country_id'])]).name
                    delivery_street = val[2]['street']
                    delivery_street2 = val[2]['street2']
                    delivery_city = val[2]['city']
                    delivery_state = state_name
                    delivery_country = country_name
                    delivery_zip1 = val[2]['zip']
                    delev_add = delivery_street+","+ delivery_street2+","+ delivery_city+","+ delivery_state+","+ delivery_country+","+ delivery_zip1
		if val[2]['type']=='contact':
		    cell = val[2]['mobile']
		    contact = val[2]['name']
		    email = val[2]['email']
		    fax = val[2]['fax']
		    telephone = val[2]['phone']
                    
	######
		if type(postal_add) is unicode:
			sup2=str(postal_add)
		if type(postal_add) is tuple:
	        	sup = list(postal_add)
		        sup2 = str(sup[0])
		if type(delev_add) is unicode:
			duv2 = str(delev_add)
		if type(delev_add) is tuple:
        		duv = list(delev_add)
		        duv2 = str(duv[0])
	data = {
	  "clientHandle": str(client_handle),
	  "Customer": {
	    "_blocked": vals.has_key('account_blocked') and vals['account_blocked'] or False,
	    "_countryCode": None,
	    "_createDate": "/Date("+str(a)+"+0200"+")/",
	    "_creditLimit": vals['credit_limit'] if vals.has_key('credit_limit') else 0,
	    "_currencyCode": 0,
	    "_currentBalance": 0.00,
	    "_customerBranches": [
	      {
	        "_branchID": "00000000-0000-0000-0000-000000000000",
	        "_branchName": "1",
	        "_createDate": "/Date("+str(a)+"+0200"+")/",
	        "_customerContacts": [
	          {
	            "_branchID": "00000000-0000-0000-0000-000000000000",
		    "_cell": cell,#vals.has_key('child_ids') and vals['child_ids'] and vals['child_ids'][0][2].has_key('mobile') and vals['child_ids'][0][2]['mobile'],
                    "_contact": contact,#vals.has_key('child_ids') and vals['child_ids'] and vals['child_ids'][0][2].has_key('name') and vals['child_ids'][0][2]['name'],
                    "_contactID": "00000000-0000-0000-0000-000000000000",
                    "_createDate": "/Date("+str(a)+"+0200"+")/",
                    "_email": email,#vals.has_key('child_ids') and vals['child_ids'] and vals['child_ids'][0][2].has_key('email') and vals['child_ids'][0][2]['email'],
                    "_fax": fax,#vals.has_key('child_ids') and vals['child_ids'] and vals['child_ids'][0][2].has_key('fax') and vals['child_ids'][0][2]['fax'],
                    "_telephone":telephone,# vals.has_key('child_ids') and vals['child_ids'] and vals['child_ids'][0][2].has_key('phone') and vals['child_ids'][0][2]['phone'],
	            "_updatedOn": "/Date("+str(a)+"+0200"+")/"
	          }
	        ],
	        "_customerDescription": str(vals['name']),
	        "_customerID": "00000000-0000-0000-0000-000000000000",
	        "_emailAddress": None,
	        "_partnerContact": None,
	        "_partnerCustomerCode": vals.has_key('ref') and str(vals['ref']),
	        "_partnerMobile": None,
	        "_partnerSalesmanCode": str(salesman_code),
	        "_partnerTelephone": None,
	        "_physicalAddress": "1,1,1,1,1",
	        "_postalAddress": "2,2,2,2,",
	        "_salesmanID": None,
	        "_updatedOn": "/Date("+str(a)+"+0200"+")/"
	      }
	    ],
	    "_customerCategory": None,
	    "_customerCategoryID": "00000000-0000-0000-0000-000000000000",
	    "_customerDescription": str(vals['name']),
	    "_customerID": "00000000-0000-0000-0000-000000000000",
	    "_dayBased": False,
	    "_defaultTax": 0,
	    "_discountPercent": 0,
	    "_docPrintorEmail": 1,
	    "_freight": None,
	    "_incExc": False,
	    "_interestAfter": -1,
	    "_lCardNumber": None,
	    "_loyaltyProg": None,
	    "_openItem": True,
	    "_openingBalance": 3470,
	    "_partnerAddress": {
	      "_branchID": "00000000-0000-0000-0000-000000000000",
	      "_branchName": None,
	      "_createDate": "/Date("+str(a)+"+0200"+")/",
	      "_customerContacts": [
	        {
	          "_branchID": "00000000-0000-0000-0000-000000000000",
	          "_cell": cell,#vals.has_key('child_ids') and vals['child_ids'] and vals['child_ids'][0][2].has_key('mobile') and vals['child_ids'][0][2]['mobile'],
	          "_contact": contact,#vals.has_key('child_ids') and vals['child_ids'] and vals['child_ids'][0][2].has_key('name') and vals['child_ids'][0][2]['name'],
	          "_contactID": "00000000-0000-0000-0000-000000000000",
	          "_createDate": "/Date("+str(a)+"+0200"+")/",
	          "_email": email,#vals.has_key('child_ids') and vals['child_ids'] and vals['child_ids'][0][2].has_key('email') and vals['child_ids'][0][2]['email'],
	          "_fax":fax,# vals.has_key('child_ids') and vals['child_ids'] and vals['child_ids'][0][2].has_key('fax') and vals['child_ids'][0][2]['fax'],
	          "_telephone": telephone,#vals.has_key('child_ids') and vals['child_ids'] and vals['child_ids'][0][2].has_key('phone') and vals['child_ids'][0][2]['phone'],
	          "_updatedOn": "/Date("+str(a)+"+0200"+")/"
	        }
	      ],
	      "_customerDescription": None,
	      "_customerID": "00000000-0000-0000-0000-000000000000",
	      "_emailAddress": None,
	      "_partnerContact": None,
	      "_partnerCustomerCode": vals.has_key('ref') and str(vals['ref']),
	      "_partnerMobile": None,
	      "_partnerSalesmanCode": str(salesman_code),
	      "_partnerTelephone": None,
	      "_physicalAddress": duv2 and duv2 or '',
	      "_postalAddress": sup2 and sup2 or '',
	      "_salesmanID": None,
	      "_updatedOn": "/Date("+str(a)+"+0200"+")/"
	    },
	    "_partnerAgeing": [
	      0,
	      "0",
	      "0",
	      "0",
	      "0"
	    ],
	    "_partnerBranches": None,
	    "_partnerCustomerCategory": 0,
	    "_partnerCustomerCode": vals.has_key('ref') and str(vals['ref']) or '',
	    "_partnerOverrideTax": 0,
	    "_partnerVatCode": None,
	    "_paymentTerms": 0,
	    "_priceListID": "00000000-0000-0000-0000-000000000000",
	    "_settlementTerms": False,
	    "_ship": None,
	    "_statPrintorEmail": 1,
	    "_taxReference": vals.has_key('vat_no') and str(vals['vat_no']),
	    "_taxTypeID": "00000000-0000-0000-0000-000000000000",
	    "_updatedOn": "/Date("+str(a)+"+0200"+")/",
	    "partnerPriceListId": 1,
	    "partnerTaxTypeId": 0
	  }
	}

        supp_data = {
	  "clientHandle": str(client_handle),
	  "supplier": {
	    "_blocked": vals.has_key('account_blocked') and vals['account_blocked'] or False,
	    "_countryCode": None,
	    "_createDate": "/Date("+str(a)+"+0200"+")/",
	    "_creditLimit": vals.has_key('credit_limit') and vals['credit_limit'] or 0.0,
	    "_currencyCode": 0,
	    "_currentBalance": 0.00,
	    "_dayBased": True,
	    "_defaultTax": 0,
	    "_discountPercent": 0,
	    "_docPrintorEmail": 1,
	    "_freight": "",
	    "_incExc": True,
	    "_openItem": True,
	    "_openingBalance": 0,
	    "_partnerAddress": 
	      {
	        "_branchID": "00000000-0000-0000-0000-000000000000",
	        "_branchName": "1",
	        "_createDate": "/Date("+str(a)+"+0200"+")/",
		"_physicalAddress": str(delev_add),
                "_postalAddress": str(postal_add),#
	        "_supplierContact": 
	          {
	            "_branchID": "00000000-0000-0000-0000-000000000000",
		    "_cell": cell,#vals.has_key('child_ids') and vals['child_ids'] and vals['child_ids'][0][2].has_key('mobile') and vals['child_ids'][0][2]['mobile'],
                    "_contact": contact,#vals.has_key('child_ids') and vals['child_ids'] and vals['child_ids'][0][2].has_key('name') and vals['child_ids'][0][2]['name'],
                    "_contactID": "00000000-0000-0000-0000-000000000000",
                    "_createDate": "/Date("+str(a)+"+0200"+")/",
                    "_email": email,#vals.has_key('child_ids') and vals['child_ids'] and vals['child_ids'][0][2].has_key('email') and vals['child_ids'][0][2]['email'],
                    "_fax": fax,#vals.has_key('child_ids') and vals['child_ids'] and vals['child_ids'][0][2].has_key('fax') and vals['child_ids'][0][2]['fax'],
                    "_telephone":telephone,# vals.has_key('child_ids') and vals['child_ids'] and vals['child_ids'][0][2].has_key('phone') and vals['child_ids'][0][2]['phone'],
	            "_updatedOn": "/Date("+str(a)+"+0200"+")/"
	          }
	        ,
	        "_supplierDescription": str(vals['name']),
	        "_supplierID": "00000000-0000-0000-0000-000000000000",
	        "_emailAddress": None,
	        "_partnerContact": None,
	        "_partnerSupplierCode": vals.has_key('ref') and str(vals['ref']),
	        "_partnerMobile": None,
	        "_partnerSalesmanCode": str(salesman_code),
	        "_partnerTelephone": None,
	        "_physicalAddress": str(delev_add),
	        "_postalAddress": str(postal_add),
	        "_salesmanID": None,
	        "_updatedOn": "/Date("+str(a)+"+0200"+")/"
	      }
	    ,
            "_supplierCategoryID": "00000000-0000-0000-0000-000000000000",
            "_supplierCode":vals.has_key('ref') and str(vals['ref']),
	    "_supplierDescription": str(vals['name']),
            "_supplierID": "00000000-0000-0000-0000-000000000000",
	    "_paymentTerms": 1,
	    "_settlementTerms": False,
	    "_ship": None,
	    "_statPrintorEmail": 1,
	    "_taxReference": vals.has_key('vat_no') and str(vals['vat_no']),
	    "_taxTypeID": "00000000-0000-0000-0000-000000000000",
	    "_updatedOn": "/Date("+str(a)+"+0200"+")/",
	  }
	}

	######
	try:
		url = "http://letsap.dedicated.co.za/Letsap.Framework.WebHost/KMQAPIService.svc/GetTestConnection/"+str(client_handle)
		conn = requests.get(url)
                if conn.status_code == 200:

		    if (vals.has_key('ref') and vals['ref']) and (vals.has_key('company_type') and vals['company_type'] == 'company') and vals['customer'] == True:
			resp = requests.post(url='http://letsap.dedicated.co.za/Letsap.Framework.WebHost/KMQAPIService.svc/SaveCustomer', headers=headers,json=mydict(data))
			#if resp.status_code == "200":
			if resp.status_code == 200:
		                vals['created_at_pastel'] = True
		        else:
        		        vals['created_at_pastel'] = False

		    elif (vals.has_key('ref') and vals['ref']) and (vals.has_key('company_type') and vals['company_type'] == 'company') and vals['supplier'] == True:
        	        resp = requests.post(url='http://letsap.dedicated.co.za/Letsap.Framework.WebHost/KMQAPIService.svc/SaveSupplier', headers=headers,json=mydict(supp_data))
                	#if resp.status_code == "200":
	                if resp.status_code == 200:
        	                vals['created_at_pastel'] = True
	                else:
        	                vals['created_at_pastel'] = False


	except Exception,e:
		print "Exception is in createeeeeeeee:",e
	return super(ResPartner,self).create(vals)

    def write(self,vals):
	if vals.has_key('ref') and self.ref:
		raise UserError(_('You cannot change the Internal Reference for a customer.'))
	#res = super(ResPartner,self).write(vals)
	salesman_code = ''
	headers = {"Content-type": "application/json"}
        client_data = {"username" : "Daniel"}
       	client_data_resp = requests.post(url='http://letsap.dedicated.co.za/portmapping/CompanyList.asmx/GetCompanyList', headers=headers,  json=client_data)
        client_data_res = json.loads(client_data_resp.content)
       	client_handle = client_data_res['d'][0]['ClientHandle'] 
	a = datetime.strptime(str(datetime.now().date()), '%Y-%m-%d')
        a = int(unix_time_millis(a))
	if vals.has_key('user_id') and vals['user_id']:
		user = self.env['res.users'].browse(vals['user_id'])
		salesman_code = user.partner_id.ref
	else:
		salesman_code = self.user_id and self.user_id.partner_id.ref or ' '

	postal_add = delev_add = cell = contact = email = fax = telephone = ' '

	if vals.has_key('child_ids') and vals['child_ids']:
            for val in vals['child_ids']:
                if val[2] and val[2].has_key('type') and val[2]['type']=='invoice':
                    if val[2].has_key('state_id'):
                        state_name = self.env['res.country.state'].search([('id','=',val[2]['state_id'])]).name
                    if val[2].has_key('country_id'):
                        country_name = self.env['res.country'].search([('id','=',val[2]['country_id'])]).name
                    postal_street = val[2]['street']
                    postal_street2 = val[2]['street2']
                    postal_city = val[2]['city']
                    postal_state = state_name
                    postal_country = country_name
                    postal_zip1 = val[2]['zip']
                    postal_add = postal_street+","+ postal_street2+","+ postal_city+","+ postal_state+","+ postal_country+","+ postal_zip1,

                if val[2] and val[2].has_key('type') and val[2]['type']=='delivery':
                    if val[2].has_key('state_id'):
                        state_name = self.env['res.country.state'].search([('id','=',val[2]['state_id'])]).name
                    if val[2].has_key('country_id'):
                        country_name = self.env['res.country'].search([('id','=',val[2]['country_id'])]).name
                    delivery_street = val[2]['street']
                    delivery_street2 = val[2]['street2']
                    delivery_city = val[2]['city']
                    delivery_state = state_name
                    delivery_country = country_name
                    delivery_zip1 = val[2]['zip']
                    delev_add = delivery_street+","+ delivery_street2+","+ delivery_city+","+ delivery_state+","+ delivery_country+","+ delivery_zip1,
                if val[2] and val[2].has_key('type') and val[2]['type']=='contact':
                    cell = val[2]['mobile']
                    contact = val[2]['name']
                    email = val[2]['email']
                    fax = val[2]['fax']
                    telephone = val[2]['phone']


	if self.child_ids:
	    for val in self.child_ids:
	      if val.type=='invoice':
                if val.state_id:
                        state_name = self.env['res.country.state'].search([('id','=',val.state_id.id)]).name
                if val.country_id:
                        country_name = self.env['res.country'].search([('id','=',val.country_id.id)]).name
                postal_street = val.street
                postal_street2 = val.street2
                postal_city = val.city
                postal_state = state_name
                postal_country = country_name
                postal_zip1 = val.zip
                postal_add = postal_street+","+ postal_street2+","+ postal_city+","+ postal_state+","+ postal_country+","+ postal_zip1,
                
              if val.type=='delivery':
                if val.state_id:
                        state_name = self.env['res.country.state'].search([('id','=',val.state_id.id)]).name
                if val.country_id:
                        country_name = self.env['res.country'].search([('id','=',val.country_id.id)]).name
                delivery_street = val.street
                delivery_street2 = val.street2
                delivery_city = val.city
                delivery_state = state_name
                delivery_country = country_name
                delivery_zip1 = val.zip
                delev_add = delivery_street+","+ delivery_street2+","+ delivery_city+","+ delivery_state+","+ delivery_country+","+ delivery_zip1,
                
              if val.type == 'contact':
                cell = val.mobile
                contact = val.name
		email = val.email
		fax = val.fax
		telephone = val.phone

	      if vals.has_key('child_ids') and vals['child_ids']:
	      	for val in vals['child_ids']:
		    if val[2] and val[2].has_key('email'):
	                email = val[2]['email']
		    if val[2] and val[2].has_key('mobile'):
                        cell = val[2]['mobile']
		    if val[2] and val[2].has_key('name'):
                        contact = val[2]['name']
		    if val[2] and val[2].has_key('fax'):
                        fax = val[2]['fax']
		    if val[2] and val[2].has_key('phone'):
                        telephone = val[2]['phone']

		    if val[2]:
	                con_id = val[1]
			con_data = self.env['res.partner'].browse(con_id)
			if con_data.type == 'delivery':
				delivery_street = val[2]['street'] if val[2].has_key('street') else con_data.street
		                delivery_street2 = val[2]['street2'] if val[2].has_key('street2') else con_data.street2
                		delivery_city = val[2]['city'] if val[2].has_key('city') else con_data.city
		                delivery_state = self.env['res.country.state'].browse(val[2]['state_id']).name if val[2].has_key('state_id') else con_data.state_id.name
		                delivery_country = self.env['res.country'].browse(val[2]['country_id']).name if val[2].has_key('country_id') else con_data.country_id.name
		                delivery_zip1 = val[2]['zip'] if val[2].has_key('zip') else con_data.zip
		                delev_add = delivery_street+","+ delivery_street2+","+ delivery_city+","+ delivery_state+","+ delivery_country+","+ delivery_zip1,

		    if val[2]:
                        con_id = val[1]
                        con_data = self.env['res.partner'].browse(con_id)
                        if con_data.type == 'invoice':
                                postal_street = val[2]['street'] if val[2].has_key('street') else con_data.street
                                postal_street2 = val[2]['street2'] if val[2].has_key('street2') else con_data.street2
                                postal_city = val[2]['city'] if val[2].has_key('city') else con_data.city
                                postal_state = self.env['res.country.state'].browse(val[2]['state_id']).name if val[2].has_key('state_id') else con_data.state_id.name
                                postal_country = self.env['res.country'].browse(val[2]['country_id']).name if val[2].has_key('country_id') else con_data.country_id.name
                                postal_zip1 = val[2]['zip'] if val[2].has_key('zip') else con_data.zip
                                postal_add = postal_street+","+ postal_street2+","+ postal_city+","+ postal_state+","+ postal_country+","+ postal_zip1,

	      
	sup = list(postal_add)
	sup2 = str(sup[0])
	duv = list(delev_add)
        duv2 = str(duv[0])
	data = {
	  "clientHandle": str(client_handle),
	  "Customer": {
	    "_blocked": vals['account_blocked'] if vals.has_key('account_blocked') else self.account_blocked,
	    "_countryCode": None,
	    "_createDate": "/Date("+str(a)+"+0200"+")/",
	    "_creditLimit": vals.has_key('credit_limit') and vals['credit_limit'] or self.credit_limit,
	    "_currencyCode": 0,
	    "_currentBalance": 0.00,
	    "_customerBranches": [
	      {
	        "_branchID": "00000000-0000-0000-0000-000000000000",
	        "_branchName": "1",
	        "_createDate": "/Date("+str(a)+"+0200"+")/",
	        "_customerContacts": [
	          {
	            "_branchID": "00000000-0000-0000-0000-000000000000",
		    "_cell":cell,#self.child_ids and self.child_ids.mobile,# vals.has_key('mobile') and str(vals['mobile']) or self.mobile,
                    "_contact": contact,#self.child_ids and self.child_ids.name,
                    "_contactID": "00000000-0000-0000-0000-000000000000",
                    "_createDate": "/Date("+str(a)+"+0200"+")/",
                    "_email": email,#self.child_ids and self.child_ids.email,
                    "_fax": fax,#vals.has_key('fax') and str(vals['fax']) or self.fax,
                    "_telephone":telephone,# self.child_ids and self.child_ids.phone,

	            "_updatedOn": "/Date("+str(a)+"+0200"+")/"
	          }
	        ],
	        "_customerDescription": vals.has_key('name') and vals['name'] or self.name,
	        "_customerID": "00000000-0000-0000-0000-000000000000",
	        "_emailAddress": None,
	        "_partnerContact": None,
	        "_partnerCustomerCode": None,
	        "_partnerMobile": None,
	        "_partnerSalesmanCode": str(salesman_code),
	        "_partnerTelephone": None,
		"_physicalAddress": duv2,
                "_postalAddress": sup2,#str(postal_add),
	        "_salesmanID": None,
	        "_updatedOn": "/Date("+str(a)+"+0200"+")/"
	      }
	    ],
	    "_customerCategory": None,
	    "_customerCategoryID": "00000000-0000-0000-0000-000000000000",
	    "_customerDescription": vals.has_key('name') and vals['name'] or self.name,
	    "_customerID": "00000000-0000-0000-0000-000000000000",
	    "_dayBased": False,
	    "_defaultTax": 0,
	    "_discountPercent": 0,
	    "_docPrintorEmail": 1,
	    "_freight": None,
	    "_incExc": False,
	    "_interestAfter": -1,
	    "_lCardNumber": None,
	    "_loyaltyProg": None,
	    "_openItem": True,
	    "_openingBalance": 3470,
	    "_partnerAddress": {
	      "_branchID": "00000000-0000-0000-0000-000000000000",
	      "_branchName": None,
	      "_createDate": "/Date("+str(a)+"+0200"+")/",
	      "_customerContacts": [
	        {
		    "_branchID": "00000000-0000-0000-0000-000000000000",
		    "_cell":cell,#self.child_ids and self.child_ids.mobile,# vals.has_key('mobile') and str(vals['mobile']) or self.mobile,
                    "_contact": contact,#self.child_ids and self.child_ids.name,
                    "_contactID": "00000000-0000-0000-0000-000000000000",
                    "_createDate": "/Date("+str(a)+"+0200"+")/",
                    "_email":email,# self.child_ids and self.child_ids.email,
                    "_fax": fax,#vals.has_key('fax') and str(vals['fax']) or self.fax,
                    "_telephone": telephone,#self.child_ids and self.child_ids.phone,
  	            "_updatedOn": "/Date("+str(a)+"+0200"+")/"
	        }
	      ],
	      "_customerDescription": None,
	      "_customerID": "00000000-0000-0000-0000-000000000000",
	      "_emailAddress": None,
	      "_partnerContact": None,
	      "_partnerCustomerCode": None,
	      "_partnerMobile": None,
	      "_partnerSalesmanCode": str(salesman_code),
	      "_partnerTelephone": None,
	      "_physicalAddress": duv2,
              "_postalAddress": sup2,#str(postal_add),
	      "_salesmanID": None,
	      "_updatedOn": "/Date("+str(a)+"+0200"+")/"
	    },
	    "_partnerAgeing": [
	      0,
	      "0",
	      "0",
	      "0",
	      "0"
	    ],
	    "_partnerBranches": None,
	    "_partnerCustomerCategory": 0,
	    "_partnerCustomerCode": self.ref,
	    "_partnerOverrideTax": 0,
	    "_partnerVatCode": None,
	    "_paymentTerms": 0,
	    "_priceListID": "00000000-0000-0000-0000-000000000000",
	    "_settlementTerms": False,
	    "_ship": None,
	    "_statPrintorEmail": 1,
	    "_taxReference": self.vat_no and self.vat_no or '',
	    "_taxTypeID": "00000000-0000-0000-0000-000000000000",
	    "_updatedOn": "/Date("+str(a)+"+0200"+")/",
	    "partnerPriceListId": 1,
	    "partnerTaxTypeId": 0
	  }
	}

	supp_data = {
          "clientHandle": str(client_handle),
          "supplier": {
            "_blocked": vals['account_blocked'] if vals.has_key('account_blocked') else self.account_blocked,
            "_countryCode": None,
            "_createDate": "/Date("+str(a)+"+0200"+")/",
            "_creditLimit": vals['credit_limit'] if vals.has_key('credit_limit') else self.credit_limit,
            "_currencyCode": 0,
            "_currentBalance": 0.00,
            "_dayBased": True,
            "_defaultTax": 0,
            "_discountPercent": 0,
            "_docPrintorEmail": 1,
            "_freight": "",
            "_incExc": True,
            "_openItem": True,
            "_openingBalance": 0,
            "_partnerAddress":
              {
                "_branchID": "00000000-0000-0000-0000-000000000000",
                "_branchName": "1",
                "_createDate": "/Date("+str(a)+"+0200"+")/",
                "_physicalAddress": duv2,
                "_postalAddress": sup2,#
                "_supplierContact":
                  {
                    "_branchID": "00000000-0000-0000-0000-000000000000",
                    "_cell": cell,#self.supplier and self.child_ids and self.child_ids.mobile,
                    "_contact": contact,#self.supplier and self.child_ids and self.child_ids.name,
                    "_contactID": "00000000-0000-0000-0000-000000000000",
                    "_createDate": "/Date("+str(a)+"+0200"+")/",
                    "_email": email,#self.supplier and self.child_ids and self.child_ids.email,
                    "_fax": fax,#self.supplier and self.child_ids and self.child_ids.fax,
                    "_telephone": telephone,#self.supplier and self.child_ids and self.child_ids.phone,
                    "_updatedOn": "/Date("+str(a)+"+0200"+")/"
                  }
                ,
                "_supplierDescription": vals.has_key('name') and str(vals['name']) or self.name,
                "_supplierID": "00000000-0000-0000-0000-000000000000",
                "_emailAddress": None,
                "_partnerContact": None,
                "_partnerSupplierCode": vals.has_key('ref') and str(vals['ref']),
                "_partnerMobile": None,
                "_partnerSalesmanCode": str(salesman_code),
                "_partnerTelephone": None,
                "_physicalAddress": duv2,
                "_postalAddress": sup2,
                "_salesmanID": None,
                "_updatedOn": "/Date("+str(a)+"+0200"+")/"
              }
            ,
            "_supplierCategoryID": "00000000-0000-0000-0000-000000000000",
            "_supplierCode":vals.has_key('ref') and str(vals['ref']) or self.ref,
            "_supplierDescription": vals.has_key('name') and str(vals['name']) or self.name,
            "_supplierID": "00000000-0000-0000-0000-000000000000",
            "_paymentTerms": 1,
            "_settlementTerms": False,
            "_ship": None,
            "_statPrintorEmail": 1,
            "_taxReference": vals.has_key('vat_no') and str(vals['vat_no']) or self.vat_no,
            "_taxTypeID": "00000000-0000-0000-0000-000000000000",
            "_updatedOn": "/Date("+str(a)+"+0200"+")/",
          }
        }
	######
	try:
		url = "http://letsap.dedicated.co.za/Letsap.Framework.WebHost/KMQAPIService.svc/GetTestConnection/"+str(client_handle)
		conn = requests.get(url)
                if conn.status_code == 200:

			if self and self.customer:
				save_customer = requests.post(url='http://letsap.dedicated.co.za/Letsap.Framework.WebHost/KMQAPIService.svc/SaveCustomer', headers=headers,json=mydict(data))
			elif self and self.supplier:
				save_supplier = requests.post(url='http://letsap.dedicated.co.za/Letsap.Framework.WebHost/KMQAPIService.svc/SaveSupplier', headers=headers,json=mydict(supp_data))


	except Exception,e:
		print "Exception is:",e
	return super(ResPartner,self).write(vals)

    def search_and_create_partner_at_pastel(self):
	partners = self.search([('created_at_pastel','=',False),('customer','=',True)])
	headers = {"Content-type": "application/json"}
	
        client_data = {"username" : "Daniel"}
        client_data_resp = requests.post(url='http://letsap.dedicated.co.za/portmapping/CompanyList.asmx/GetCompanyList', headers=headers,  json=client_data)
        client_data_res = json.loads(client_data_resp.content)
	client_handle = client_data_res['d'][0]['ClientHandle']
	for partner in partners:
		salesman_code = partner.user_id.partner_id.ref
		a = datetime.strptime(str(datetime.now().date()), '%Y-%m-%d')
        	a = int(unix_time_millis(a))
		if vals.has_key('user_id') and vals['user_id']:
			user = self.env['res.users'].browse(vals['user_id'])
			salesman_code = user.partner_id.ref
		else:
			salesman_code = self.user_id and self.user_id.partner_id.ref or ' '

		postal_add = delev_add = cell = contact = email = fax = telephone = ' '

		if vals.has_key('child_ids') and vals['child_ids']:
	            for val in vals['child_ids']:
        	        if val[2] and val[2].has_key('type') and val[2]['type']=='invoice':
                	    if val[2].has_key('state_id'):
                        	state_name = self.env['res.country.state'].search([('id','=',val[2]['state_id'])]).name
	                    if val[2].has_key('country_id'):
        	                country_name = self.env['res.country'].search([('id','=',val[2]['country_id'])]).name
                	    postal_street = val[2]['street']
	                    postal_street2 = val[2]['street2']
        	            postal_city = val[2]['city']
                	    postal_state = state_name
	                    postal_country = country_name
        	            postal_zip1 = val[2]['zip']
                	    postal_add = postal_street+","+ postal_street2+","+ postal_city+","+ postal_state+","+ postal_country+","+ postal_zip1,

	                if val[2] and val[2].has_key('type') and val[2]['type']=='delivery':
        	            if val[2].has_key('state_id'):
                	        state_name = self.env['res.country.state'].search([('id','=',val[2]['state_id'])]).name
	                    if val[2].has_key('country_id'):
        	                country_name = self.env['res.country'].search([('id','=',val[2]['country_id'])]).name
                	    delivery_street = val[2]['street']
	                    delivery_street2 = val[2]['street2']
        	            delivery_city = val[2]['city']
                	    delivery_state = state_name
	                    delivery_country = country_name
        	            delivery_zip1 = val[2]['zip']
                	    delev_add = delivery_street+","+ delivery_street2+","+ delivery_city+","+ delivery_state+","+ delivery_country+","+ delivery_zip1,
	                if val[2] and val[2].has_key('type') and val[2]['type']=='contact':
        	            cell = val[2]['mobile']
                	    contact = val[2]['name']
	                    email = val[2]['email']
        	            fax = val[2]['fax']
                	    telephone = val[2]['phone']


		if self.child_ids:
		    for val in self.child_ids:
		      if val.type=='invoice':
        	        if val.state_id:
                	        state_name = self.env['res.country.state'].search([('id','=',val.state_id.id)]).name
	                if val.country_id:
        	                country_name = self.env['res.country'].search([('id','=',val.country_id.id)]).name
                	postal_street = val.street
	                postal_street2 = val.street2
        	        postal_city = val.city
                	postal_state = state_name
	                postal_country = country_name
        	        postal_zip1 = val.zip
                	postal_add = postal_street+","+ postal_street2+","+ postal_city+","+ postal_state+","+ postal_country+","+ postal_zip1,
                
	              if val.type=='delivery':
        	        if val.state_id:
                	        state_name = self.env['res.country.state'].search([('id','=',val.state_id.id)]).name
	                if val.country_id:
        	                country_name = self.env['res.country'].search([('id','=',val.country_id.id)]).name
                	delivery_street = val.street
	                delivery_street2 = val.street2
        	        delivery_city = val.city
	                delivery_state = state_name
        	        delivery_country = country_name
	                delivery_zip1 = val.zip
        	        delev_add = delivery_street+","+ delivery_street2+","+ delivery_city+","+ delivery_state+","+ delivery_country+","+ delivery_zip1,
                
	              if val.type == 'contact':
        	        cell = val.mobile
	                contact = val.name
			email = val.email
			fax = val.fax
			telephone = val.phone

		      if vals.has_key('child_ids') and vals['child_ids']:
		      	for val in vals['child_ids']:
			    if val[2] and val[2].has_key('email'):
	        	        email = val[2]['email']
			    if val[2] and val[2].has_key('mobile'):
        	                cell = val[2]['mobile']
			    if val[2] and val[2].has_key('name'):
	                        contact = val[2]['name']
			    if val[2] and val[2].has_key('fax'):
                	        fax = val[2]['fax']
			    if val[2] and val[2].has_key('phone'):
        	                telephone = val[2]['phone']

			    if val[2]:
		                con_id = val[1]
				con_data = self.env['res.partner'].browse(con_id)
				if con_data.type == 'delivery':
					delivery_street = val[2]['street'] if val[2].has_key('street') else con_data.street
			                delivery_street2 = val[2]['street2'] if val[2].has_key('street2') else con_data.street2
        	        		delivery_city = val[2]['city'] if val[2].has_key('city') else con_data.city
			                delivery_state = self.env['res.country.state'].browse(val[2]['state_id']).name if val[2].has_key('state_id') else con_data.state_id.name
		        	        delivery_country = self.env['res.country'].browse(val[2]['country_id']).name if val[2].has_key('country_id') else con_data.country_id.name
		                	delivery_zip1 = val[2]['zip'] if val[2].has_key('zip') else con_data.zip
			                delev_add = delivery_street+","+ delivery_street2+","+ delivery_city+","+ delivery_state+","+ delivery_country+","+ delivery_zip1,

			    if val[2]:
                	        con_id = val[1]
	                        con_data = self.env['res.partner'].browse(con_id)
        	                if con_data.type == 'invoice':
                	                postal_street = val[2]['street'] if val[2].has_key('street') else con_data.street
                        	        postal_street2 = val[2]['street2'] if val[2].has_key('street2') else con_data.street2
                                	postal_city = val[2]['city'] if val[2].has_key('city') else con_data.city
	                                postal_state = self.env['res.country.state'].browse(val[2]['state_id']).name if val[2].has_key('state_id') else con_data.state_id.name
        	                        postal_country = self.env['res.country'].browse(val[2]['country_id']).name if val[2].has_key('country_id') else con_data.country_id.name
                	                postal_zip1 = val[2]['zip'] if val[2].has_key('zip') else con_data.zip
                        	        postal_add = postal_street+","+ postal_street2+","+ postal_city+","+ postal_state+","+ postal_country+","+ postal_zip1,

	      
		sup = list(postal_add)
		sup2 = str(sup[0])
		duv = list(delev_add)
	        duv2 = str(duv[0])
		data = {
		  "clientHandle": str(client_handle),
		  "Customer": {
		    "_blocked": vals['account_blocked'] if vals.has_key('account_blocked') else self.account_blocked,
		    "_countryCode": None,
		    "_createDate": "/Date("+str(a)+"+0200"+")/",
		    "_creditLimit": vals.has_key('credit_limit') and vals['credit_limit'] or self.credit_limit,
		    "_currencyCode": 0,
		    "_currentBalance": 0.00,
		    "_customerBranches": [
		      {
		        "_branchID": "00000000-0000-0000-0000-000000000000",
		        "_branchName": "1",
		        "_createDate": "/Date("+str(a)+"+0200"+")/",
		        "_customerContacts": [
		          {
	        	    "_branchID": "00000000-0000-0000-0000-000000000000",
			    "_cell":cell,#self.child_ids and self.child_ids.mobile,# vals.has_key('mobile') and str(vals['mobile']) or self.mobile,
        	            "_contact": contact,#self.child_ids and self.child_ids.name,
	                    "_contactID": "00000000-0000-0000-0000-000000000000",
        	            "_createDate": "/Date("+str(a)+"+0200"+")/",
	                    "_email": email,#self.child_ids and self.child_ids.email,
        	            "_fax": fax,#vals.has_key('fax') and str(vals['fax']) or self.fax,
	                    "_telephone":telephone,# self.child_ids and self.child_ids.phone,
	
		            "_updatedOn": "/Date("+str(a)+"+0200"+")/"
		          }
		        ],
		        "_customerDescription": vals.has_key('name') and vals['name'] or self.name,
		        "_customerID": "00000000-0000-0000-0000-000000000000",
		        "_emailAddress": None,
		        "_partnerContact": None,
		        "_partnerCustomerCode": None,
		        "_partnerMobile": None,
		        "_partnerSalesmanCode": str(salesman_code),
		        "_partnerTelephone": None,
			"_physicalAddress": duv2,
        	        "_postalAddress": sup2,#str(postal_add),
		        "_salesmanID": None,
		        "_updatedOn": "/Date("+str(a)+"+0200"+")/"
		      }
		    ],
		    "_customerCategory": None,
		    "_customerCategoryID": "00000000-0000-0000-0000-000000000000",
		    "_customerDescription": vals.has_key('name') and vals['name'] or self.name,
		    "_customerID": "00000000-0000-0000-0000-000000000000",
		    "_dayBased": False,
		    "_defaultTax": 0,
		    "_discountPercent": 0,
		    "_docPrintorEmail": 1,
		    "_freight": None,
		    "_incExc": False,
		    "_interestAfter": -1,
		    "_lCardNumber": None,
		    "_loyaltyProg": None,
		    "_openItem": True,
		    "_openingBalance": 3470,
		    "_partnerAddress": {
		      "_branchID": "00000000-0000-0000-0000-000000000000",
		      "_branchName": None,
		      "_createDate": "/Date("+str(a)+"+0200"+")/",
		      "_customerContacts": [
		        {
			    "_branchID": "00000000-0000-0000-0000-000000000000",
			    "_cell":cell,#self.child_ids and self.child_ids.mobile,# vals.has_key('mobile') and str(vals['mobile']) or self.mobile,
                	    "_contact": contact,#self.child_ids and self.child_ids.name,
	                    "_contactID": "00000000-0000-0000-0000-000000000000",
        	            "_createDate": "/Date("+str(a)+"+0200"+")/",
                	    "_email":email,# self.child_ids and self.child_ids.email,
	                    "_fax": fax,#vals.has_key('fax') and str(vals['fax']) or self.fax,
        	            "_telephone": telephone,#self.child_ids and self.child_ids.phone,
	  	            "_updatedOn": "/Date("+str(a)+"+0200"+")/"
		        }
		      ],
		      "_customerDescription": None,
		      "_customerID": "00000000-0000-0000-0000-000000000000",
		      "_emailAddress": None,
		      "_partnerContact": None,
		      "_partnerCustomerCode": None,
		      "_partnerMobile": None,
		      "_partnerSalesmanCode": str(salesman_code),
		      "_partnerTelephone": None,
		      "_physicalAddress": duv2,
	              "_postalAddress": sup2,#str(postal_add),
		      "_salesmanID": None,
		      "_updatedOn": "/Date("+str(a)+"+0200"+")/"
		    },
		    "_partnerAgeing": [
		      0,
		      "0",
		      "0",
		      "0",
		      "0"
		    ],
		    "_partnerBranches": None,
		    "_partnerCustomerCategory": 0,
		    "_partnerCustomerCode": self.ref,
		    "_partnerOverrideTax": 0,
		    "_partnerVatCode": None,
		    "_paymentTerms": 0,
		    "_priceListID": "00000000-0000-0000-0000-000000000000",
		    "_settlementTerms": False,
		    "_ship": None,
		    "_statPrintorEmail": 1,
		    "_taxReference": self.vat_no and self.vat_no or '',
		    "_taxTypeID": "00000000-0000-0000-0000-000000000000",
		    "_updatedOn": "/Date("+str(a)+"+0200"+")/",
		    "partnerPriceListId": 1,
		    "partnerTaxTypeId": 0
		  }
		}

		supp_data = {
        	  "clientHandle": str(client_handle),
	          "supplier": {
        	    "_blocked": vals['account_blocked'] if vals.has_key('account_blocked') else self.account_blocked,
	            "_countryCode": None,
	            "_createDate": "/Date("+str(a)+"+0200"+")/",
	            "_creditLimit": vals['credit_limit'] if vals.has_key('credit_limit') else self.credit_limit,
	            "_currencyCode": 0,
	            "_currentBalance": 0.00,
	            "_dayBased": True,
	            "_defaultTax": 0,
	            "_discountPercent": 0,
	            "_docPrintorEmail": 1,
	            "_freight": "",
	            "_incExc": True,
	            "_openItem": True,
	            "_openingBalance": 0,
	            "_partnerAddress":
	              {
	                "_branchID": "00000000-0000-0000-0000-000000000000",
	                "_branchName": "1",
	                "_createDate": "/Date("+str(a)+"+0200"+")/",
	                "_physicalAddress": duv2,
        	        "_postalAddress": sup2,#
	                "_supplierContact":
	                  {
	                    "_branchID": "00000000-0000-0000-0000-000000000000",
	                    "_cell": cell,#self.supplier and self.child_ids and self.child_ids.mobile,
	                    "_contact": contact,#self.supplier and self.child_ids and self.child_ids.name,
	                    "_contactID": "00000000-0000-0000-0000-000000000000",
	                    "_createDate": "/Date("+str(a)+"+0200"+")/",
	                    "_email": email,#self.supplier and self.child_ids and self.child_ids.email,
	                    "_fax": fax,#self.supplier and self.child_ids and self.child_ids.fax,
	                    "_telephone": telephone,#self.supplier and self.child_ids and self.child_ids.phone,
	                    "_updatedOn": "/Date("+str(a)+"+0200"+")/"
	                  }
	                ,
	                "_supplierDescription": vals.has_key('name') and str(vals['name']) or self.name,
	                "_supplierID": "00000000-0000-0000-0000-000000000000",
	                "_emailAddress": None,
	                "_partnerContact": None,
	                "_partnerSupplierCode": vals.has_key('ref') and str(vals['ref']),
	                "_partnerMobile": None,
	                "_partnerSalesmanCode": str(salesman_code),
	                "_partnerTelephone": None,
	                "_physicalAddress": duv2,
	                "_postalAddress": sup2,
	                "_salesmanID": None,
	                "_updatedOn": "/Date("+str(a)+"+0200"+")/"
	              }
	            ,
	            "_supplierCategoryID": "00000000-0000-0000-0000-000000000000",
	            "_supplierCode":vals.has_key('ref') and str(vals['ref']) or self.ref,
	            "_supplierDescription": vals.has_key('name') and str(vals['name']) or self.name,
	            "_supplierID": "00000000-0000-0000-0000-000000000000",
	            "_paymentTerms": 1,
	            "_settlementTerms": False,
	            "_ship": None,
	            "_statPrintorEmail": 1,
	            "_taxReference": vals.has_key('vat_no') and str(vals['vat_no']) or self.vat_no,
	            "_taxTypeID": "00000000-0000-0000-0000-000000000000",
	            "_updatedOn": "/Date("+str(a)+"+0200"+")/",
	          }
	        }
		######
		try:
			conn = "http://letsap.dedicated.co.za/Letsap.Framework.WebHost/KMQAPIService.svc/GetTestConnection/"+str(client_handle)
	                if conn.status_code == 200:
	
				if self and self.customer:
					save_customer = requests.post(url='http://letsap.dedicated.co.za/Letsap.Framework.WebHost/KMQAPIService.svc/SaveCustomer', headers=headers,json=mydict(data))
				elif self and self.supplier:
					save_supplier = requests.post(url='http://letsap.dedicated.co.za/Letsap.Framework.WebHost/KMQAPIService.svc/SaveSupplier', headers=headers,json=mydict(supp_data))
	
	
		except Exception,e:
			print "Exception is:",e
		return True"""
	
