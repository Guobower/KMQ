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

    _sql_constraints = [
        ('customer_ref_uniq', 'unique (ref)', 'The reference of the customer must be unique!')
    ]

    @api.onchange('ref')
    def onchange_ref(self):
	if self.ref:
		existing_ref = self.search([('ref','=',self.ref)])
		if existing_ref:
			raise UserError(_('Entered reference number already exist.'))
		

    @api.model
    def create(self,vals):
        #if vals.has_key('parent_id') and vals['parent_id'] == False:
       	salesman_code = False
	if not vals.has_key('child_ids') and not vals['parent_id']:
		raise UserError(_('Please add a contact for the customer.'))
	if vals.has_key('user_id') and vals['user_id']:
		salesman_code = self.env['res.users'].browse(vals['user_id']).partner_id.ref 
	headers = {"Content-type": "application/json"}
        client_data = {"username" : "Daniel"}
        client_data_resp = requests.post(url='http://letsap.dedicated.co.za/portmapping/CompanyList.asmx/GetCompanyList', headers=headers,  json=client_data)
        client_data_res = json.loads(client_data_resp.content)
        client_handle = client_data_res['d'][0]['ClientHandle'] 

	a = datetime.strptime(str(datetime.now().date()), '%Y-%m-%d')
        a = int(unix_time_millis(a))

	street = street2 = city = zip1 = state = country = ''	
	street = street2 = city = zip1 = state = country = ''
	if vals.has_key('street') and vals['street']:
                street = str(vals['street']) or ''

        if vals.has_key('street2') and vals['street2']:
                street2 = str(vals['street2']) or ''

        if vals.has_key('city') and vals['city']:
                city = str(vals['city']) or ''

        if vals.has_key('state_id') and vals['state_id']:
                state = self.env['res.country.state'].search([('id','=',vals['state_id'])]).name or ''  

        if vals.has_key('country_id') and vals['country_id']:
                country = self.env['res.country'].search([('id','=',vals['country_id'])]).name or ''


        if vals.has_key('zip') and vals['zip']:
                zip1 = str(vals['zip']) or ''
	print vals,'valsssssssss'
	if vals.has_key('child_ids') and vals['child_ids'] and vals['child_ids'][0][2]['type']=='invoice':
		if vals['child_ids'][0][2].has_key('state_id'):
			state_name = self.env['res.country.state'].search([('id','=',vals['child_ids'][0][2]['state_id'])]).name
		if vals['child_ids'][0][2].has_key('country_id'):
			country_name = self.env['res.country'].search([('id','=',vals['child_ids'][0][2]['country_id'])]).name
                delivery_street = vals['child_ids'][0][2]['street']
                delivery_street2 = vals['child_ids'][0][2]['street2']
                delivery_city = vals['child_ids'][0][2]['city']
                delivery_state = state_name
                delivery_country = country_name
                delivery_zip1 = vals['child_ids'][0][2]['zip']
		postal_add = delivery_street+","+ delivery_street2+","+ delivery_city+","+ delivery_state+","+ delivery_country+","+ delivery_zip1,
		delev_add = ''
        elif vals.has_key('child_ids') and vals['child_ids'] and vals['child_ids'][0][2]['type']=='delivery':
                if vals['child_ids'][0][2].has_key('state_id'):
                        state_name = self.env['res.country.state'].search([('id','=',vals['child_ids'][0][2]['state_id'])]).name
                if vals['child_ids'][0][2].has_key('country_id'):
                        country_name = self.env['res.country'].search([('id','=',vals['child_ids'][0][2]['country_id'])]).name
                delivery_street = vals['child_ids'][0][2]['street']
                delivery_street2 = vals['child_ids'][0][2]['street2']
                delivery_city = vals['child_ids'][0][2]['city']
                delivery_state = state_name
                delivery_country = country_name
                delivery_zip1 = vals['child_ids'][0][2]['zip']
                delev_add = delivery_street+","+ delivery_street2+","+ delivery_city+","+ delivery_state+","+ delivery_country+","+ delivery_zip1,
                postal_add = ''
	else:
		postal_add = ''
		delev_add = ''
	######
	data = {
	  "clientHandle": str(client_handle),
	  "Customer": {
	    "_blocked": vals.has_key('account_blocked') and vals['account_blocked'] or False,
	    "_countryCode": None,
	    "_createDate": "/Date("+str(a)+"+0200"+")/",
	    "_creditLimit": vals.has_key('credit_limit') and vals['credit_limit'] or 0.0,
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
		    "_cell": vals.has_key('child_ids') and vals['child_ids'] and vals['child_ids'][0][2].has_key('mobile') and vals['child_ids'][0][2]['mobile'],
                    "_contact": vals.has_key('child_ids') and vals['child_ids'] and vals['child_ids'][0][2].has_key('name') and vals['child_ids'][0][2]['name'],
                    "_contactID": "00000000-0000-0000-0000-000000000000",
                    "_createDate": "/Date("+str(a)+"+0200"+")/",
                    "_email": vals.has_key('child_ids') and vals['child_ids'] and vals['child_ids'][0][2].has_key('email') and vals['child_ids'][0][2]['email'],
                    "_fax": vals.has_key('child_ids') and vals['child_ids'] and vals['child_ids'][0][2].has_key('fax') and vals['child_ids'][0][2]['fax'],
                    "_telephone": vals.has_key('child_ids') and vals['child_ids'] and vals['child_ids'][0][2].has_key('phone') and vals['child_ids'][0][2]['phone'],
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
	          "_cell": vals.has_key('child_ids') and vals['child_ids'] and vals['child_ids'][0][2].has_key('mobile') and vals['child_ids'][0][2]['mobile'],
	          "_contact": vals.has_key('child_ids') and vals['child_ids'] and vals['child_ids'][0][2].has_key('name') and vals['child_ids'][0][2]['name'],
	          "_contactID": "00000000-0000-0000-0000-000000000000",
	          "_createDate": "/Date("+str(a)+"+0200"+")/",
	          "_email": vals.has_key('child_ids') and vals['child_ids'] and vals['child_ids'][0][2].has_key('email') and vals['child_ids'][0][2]['email'],
	          "_fax": vals.has_key('child_ids') and vals['child_ids'] and vals['child_ids'][0][2].has_key('fax') and vals['child_ids'][0][2]['fax'],
	          "_telephone": vals.has_key('child_ids') and vals['child_ids'] and vals['child_ids'][0][2].has_key('phone') and vals['child_ids'][0][2]['phone'],
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
	      "_physicalAddress": str(delev_add),
	      "_postalAddress": str(postal_add),
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
		    "_cell": vals.has_key('child_ids') and vals['child_ids'] and vals['child_ids'][0][2].has_key('mobile') and vals['child_ids'][0][2]['mobile'],
                    "_contact": vals.has_key('child_ids') and vals['child_ids'] and vals['child_ids'][0][2].has_key('name') and vals['child_ids'][0][2]['name'],
                    "_contactID": "00000000-0000-0000-0000-000000000000",
                    "_createDate": "/Date("+str(a)+"+0200"+")/",
                    "_email": vals.has_key('child_ids') and vals['child_ids'] and vals['child_ids'][0][2].has_key('email') and vals['child_ids'][0][2]['email'],
                    "_fax": vals.has_key('child_ids') and vals['child_ids'] and vals['child_ids'][0][2].has_key('fax') and vals['child_ids'][0][2]['fax'],
                    "_telephone": vals.has_key('child_ids') and vals['child_ids'] and vals['child_ids'][0][2].has_key('phone') and vals['child_ids'][0][2]['phone'],
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
		print "Exception is:",e
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
	if vals.has_key('user_id') and vals['user_id']:
		user = self.env['res.users'].browse(vals['user_id'])
		salesman_code = user.partner_id.ref
	else:
		salesman_code = self.user_id.partner_id.ref
	if vals.has_key('street') and vals['street']:
		street = str(vals['street']) 
	else :
		street = self.street or ''

	if vals.has_key('street2') and vals['street2']:
		street2 = str(vals['street2']) 
	else :
		street2 = self.street2 or ''

	if vals.has_key('city') and vals['city']:
		city = str(vals['city']) 
	else :
		city = self.city or ''

	if vals.has_key('state_id') and vals['state_id']:
                state = self.env['res.country.state'].search([('id','=',vals['state_id'])]).name or ''	
        else :
                state = self.state_id.name or ''

	if vals.has_key('country_id') and vals['country_id']:
                country = self.env['res.country'].search([('id','=',vals['country_id'])]).name or ''  
        else :
                country = self.country_id.name or ''

	
	if vals.has_key('zip') and vals['zip']:
		zip1 = str(vals['zip']) 
	else :
		zip1 = self.zip or ''

	"""if self.child_ids:
	        delivery_street = self.child_ids.street or ''
                delivery_street2 = self.child_ids.street2 or ''
                delivery_city = self.child_ids.city or ''
                delivery_state = self.child_ids.state_id.name or ''
                delivery_country = self.child_ids.country_id.name or ''
                delivery_zip1 = self.child_ids.zip or ''
	else:
		delivery_street = ''
                delivery_street2 = ''
                delivery_city =  ''
                delivery_state = ''
                delivery_country = ''
                delivery_zip1 = ''"""
	postal_add = ''
	delev_add = ''
	if self.child_ids:
	    for child in self.child_ids:
	      print child.type,'==================='
	      if child.type=='invoice':
                if child.state_id:
                        state_name = self.env['res.country.state'].search([('id','=',child.state_id.id)]).name
                if child_id.country_id:
                        country_name = self.env['res.country'].search([('id','=',child.country_id.id)]).name
                post_street = child.street
                post_street2 = child.street2
                post_city = child.city
                post_state = state_name
                post_country = country_name
                post_zip1 = child.zip
                postal_add = post_street+","+ post_street2+","+ post_city+","+ post_state+","+ post_country+","+ post_zip1,
        
	      elif child.type=='delivery':
                if child.state_id:
                        state_name = self.env['res.country.state'].search([('id','=',child.state_id.id)]).name
                if child.country_id:
                        country_name = self.env['res.country'].search([('id','=',child.country_id.id)]).name
                delivery_street = child.street
                delivery_street2 = child.street2
                delivery_city = child.city
                delivery_state = state_name
                delivery_country = country_name
                delivery_zip1 = child.zip
                delev_add = delivery_street+","+ delivery_street2+","+ delivery_city+","+ delivery_state+","+ delivery_country+","+ delivery_zip1,
		
	      else:
                postal_add = ''
                delev_add = ''

	print postal_add,'postal add=============='
	######
	mobile = [child.mobile for child in self.child_ids if child.type=='contact']
	contact= [child.name for child in self.child_ids if child.type=='contact']
        email = [child.email for child in self.child_ids if child.type=='contact']
        fax = [child.fax for child in self.child_ids if child.type=='contact']
	telephone = [child.phone for child in self.child_ids if child.type=='contact']

	data = {
	  "clientHandle": str(client_handle),
	  "Customer": {
	    "_blocked": vals.has_key('account_blocked') and vals['account_blocked'] or False,
	    "_countryCode": None,
	    "_createDate": "/Date(1152741600000+0200)/",
	    "_creditLimit": vals.has_key('credit_limit') and vals['credit_limit'] or self.credit_limit,
	    "_currencyCode": 0,
	    "_currentBalance": 0.00,
	    "_customerBranches": [
	      {
	        "_branchID": "00000000-0000-0000-0000-000000000000",
	        "_branchName": "1",
	        "_createDate": "/Date(1488348181076+0200)/",
	        "_customerContacts": [
	          {
	            "_branchID": "00000000-0000-0000-0000-000000000000",
        	    "_cell":str(mobile),
	            "_contact": str(contact),
        	    "_contactID": "00000000-0000-0000-0000-000000000000",
	            "_createDate": "/Date(1490191926874+0200)/",
        	    "_email": str(email),
	            "_fax": str(fax),
	            "_telephone": str(telephone),
	            "_updatedOn": "/Date(1490191926874+0200)/"
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
		"_physicalAddress": str(delev_add),
                "_postalAddress": str(postal_add),
	        "_salesmanID": None,
	        "_updatedOn": "/Date(1488348181076+0200)/"
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
	      "_createDate": "/Date(1488348181076+0200)/",
	      "_customerContacts": [
	        {
		    "_cell":str(mobile),
                    "_contact": str(contact),
                    "_contactID": "00000000-0000-0000-0000-000000000000",
                    "_createDate": "/Date(1490191926874+0200)/",
                    "_email": str(email),
                    "_fax": str(fax),
                    "_telephone": str(telephone),
  	            "_updatedOn": "/Date(1490191926874+0200)/"
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
	      "_physicalAddress": str(delev_add),
              "_postalAddress": str(postal_add),
	      "_salesmanID": None,
	      "_updatedOn": "/Date(1488348181076+0200)/"
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
	    "_updatedOn": "/Date(1486713747000+0200)/",
	    "partnerPriceListId": 1,
	    "partnerTaxTypeId": 0
	  }
	}
	######
	try:
		save_customer = requests.post(url='http://letsap.dedicated.co.za/Letsap.Framework.WebHost/KMQAPIService.svc/SaveCustomer', headers=headers,json=mydict(data))
		print save_customer.status_code,'statusssssssssss'

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
		check_customer_data = {"clientHandle":client_handle,"customerID":partner.ref}
		check_customer = requests.post(url='http://letsap.dedicated.co.za/Letsap.Framework.WebHost/KMQAPIService.svc/GetCustomer', headers=headers,  json=mydict(check_customer_data))
		check_customer_res = json.loads(check_customer.content)
		if check_customer_res['GetCustomerResult']['_partnerCustomerCode']:
			partner.created_at_pastel = True
		if partner.child_ids:
	                delivery_street = partner.child_ids.street or ''
        	        delivery_street2 = partner.child_ids.street2 or ''
	                delivery_city = partner.child_ids.city or ''
	                delivery_state = partner.child_ids.state_id.name or ''
        	        delivery_country = partner.child_ids.country_id.name or ''
	                delivery_zip1 = partner.child_ids.zip or ''
		else:
			delivery_street = ''
                        delivery_street2 = ''
                        delivery_city =  ''
                        delivery_state = ''
                        delivery_country = ''
                        delivery_zip1 = ''

			######
			data = {
			  "clientHandle": str(client_handle),
			  "Customer": {
			    "_blocked": partner.account_blocked or False,
			    "_countryCode": None,
			    "_createDate": "/Date(1152741600000+0200)/",
			    "_creditLimit": partner.credit_limit or 0.0,
			    "_currencyCode": 0,
			    "_currentBalance": 0.00,
			    "_customerBranches": [
			      {
			        "_branchID": "00000000-0000-0000-0000-000000000000",
			        "_branchName": "1",
			        "_createDate": "/Date(1488348181076+0200)/",
			        "_customerContacts": [
			          {
			            "_branchID": "00000000-0000-0000-0000-000000000000",
		        	    "_cell": "1",
			            "_contact": "1",
		        	    "_contactID": "00000000-0000-0000-0000-000000000000",
			            "_createDate": "/Date(1490191926874+0200)/",
		        	    "_email": "1",
			            "_fax": "1",
			            "_telephone": "1",
			            "_updatedOn": "/Date(1490191926874+0200)/"
			          }
			        ],
			        "_customerDescription": str(partner.name) or '',
			        "_customerID": "00000000-0000-0000-0000-000000000000",
			        "_emailAddress": None,
			        "_partnerContact": None,
			        "_partnerCustomerCode": None,
			        "_partnerMobile": None,
			        "_partnerSalesmanCode": str(salesman_code) or '',
			        "_partnerTelephone": None,
			        "_physicalAddress": "1,1,1,1,1",
			        "_postalAddress": "2,2,2,2,",
			        "_salesmanID": None,
			        "_updatedOn": "/Date(1488348181076+0200)/"
			      }
			    ],
			    "_customerCategory": None,
			    "_customerCategoryID": "00000000-0000-0000-0000-000000000000",
			    "_customerDescription": str(partner.name) or '',
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
			      "_createDate": "/Date(1488348181076+0200)/",
			      "_customerContacts": [
			        {
			          "_branchID": "00000000-0000-0000-0000-000000000000",
			          "_cell": str(partner.mobile) or '',
			          "_contact": str(partner.name) or ''+"Contact",
			          "_contactID": "00000000-0000-0000-0000-000000000000",
			          "_createDate": "/Date(1490191926874+0200)/",
			          "_email": str(partner.email) or '',
			          "_fax": str(partner.fax) or '',
			          "_telephone": str(partner.phone) or '',
			          "_updatedOn": "/Date(1490191926874+0200)/"
			        }
			      ],
			      "_customerDescription": None,
			      "_customerID": "00000000-0000-0000-0000-000000000000",
			      "_emailAddress": None,
			      "_partnerContact": None,
			      "_partnerCustomerCode": None,
			      "_partnerMobile": None,
			      "_partnerSalesmanCode": None,
			      "_partnerTelephone": None,
			      "_physicalAddress": delivery_street+","+ delivery_street2+","+ delivery_city+","+ delivery_state+","+ delivery_country+","+ delivery_zip1,
			      "_postalAddress": str(partner.street) or ''+", "+str(partner.street2) or ''+", "+str(partner.city) or ''+", "+"JHB"+", "+"RSA"+", "+str(partner.zip) or '',
			      "_salesmanID": None,
			      "_updatedOn": "/Date(1488348181076+0200)/"
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
			    "_partnerCustomerCode": str(partner.ref) or '',
			    "_partnerOverrideTax": 0,
			    "_partnerVatCode": None,
			    "_paymentTerms": 0,
			    "_priceListID": "00000000-0000-0000-0000-000000000000",
			    "_settlementTerms": False,
			    "_ship": None,
			    "_statPrintorEmail": 1,
			    "_taxReference": "0",
			    "_taxTypeID": "00000000-0000-0000-0000-000000000000",
			    "_updatedOn": "/Date(1486713747000+0200)/",
			    "partnerPriceListId": 1,
			    "partnerTaxTypeId": 0
			  }
			}
			######
			try:
			    if partner.ref and partner.company_type == 'company':
				resp = requests.post(url='http://letsap.dedicated.co.za/Letsap.Framework.WebHost/KMQAPIService.svc/SaveCustomer', headers=headers,json=mydict(data))
				if resp.status_code == 200:
	                                partner.created_at_pastel = True

				#if resp.status_code == "200":
			except Exception,e:
				print "Exception is:",e
			return True
