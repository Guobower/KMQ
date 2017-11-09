import json
from lxml import etree
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.tools import float_is_zero, float_compare
from odoo.tools.misc import formatLang
from odoo.tools.float_utils import float_round
from odoo.exceptions import UserError, RedirectWarning, ValidationError

import odoo.addons.decimal_precision as dp
import logging
import MySQLdb
import base64
import os.path
import unicodedata
from datetime import datetime,date
import requests

epoch = datetime.utcfromtimestamp(0)

def unix_time_millis(dt):
    return (dt - epoch).total_seconds() * 1000.0

class mydict(dict):
        def __str__(self):
            return json.dumps(self)
class Pricelist(models.Model):
    _inherit = "product.pricelist"
    _description = "Pricelist"
    _order = "name asc"

class PricelistItem(models.Model):
    _inherit = "product.pricelist.item"
    _description = "Pricelist item"
    _order = "applied_on, min_quantity desc, categ_id desc,fixed_price desc"

class Product(models.Model):
    _inherit = "product.product"

    stock_available = fields.Float('Stock Available',compute='_compute_quantities_revised',digits=dp.get_precision('Product Unit of Measure'))
    sale_stock_available = fields.Float('Sale Orders',compute='_compute_quantities_revised',digits=dp.get_precision('Product Unit of Measure'))
    purchase_stock_available = fields.Float('Purchase Orders',compute='_compute_quantities_revised',digits=dp.get_precision('Product Unit of Measure'))
    created_at_pastel = fields.Boolean('Created at Pastel')

    #@api.depends('stock_quant_ids', 'stock_move_ids')
    def _compute_quantities_revised(self):
	qty_inv = 0
	a = "WH/Stock"
	b = "004/Stock"
	wh_stock_location_id = self.env['stock.location'].search([('complete_name','=',a)]).id
	print wh_stock_location_id,'wh_stock_location_id============='
	wh_stock_location_id_4 = self.env['stock.location'].search([('complete_name','=',b)]).id
	print wh_stock_location_id_4,'wh_stock_location_id_4========='
	#sale_qty_inv = 0
        for product in self:
	    qty_inv = 0
	    sale_qty_inv = 0
	    initial_qty = 0
            sale_order_lines = self.env['sale.order.line'].search([('state', 'in', ['sale', 'done']),('product_id','=',product.id)])
	    if sale_order_lines:
	    	for line in sale_order_lines:
			stock_moves = self.env['stock.move'].search([('orogin','=',False),('picking_id','=',False),('product_id','=',line.product_id.id)])
			if stock_moves:
				for move in stock_moves:
					initial_qty+=move.product_uom_qty
	        	qty_inv+=line.qty_invoiced
			sale_qty_inv+= (line.qty_to_invoice)
		product.stock_available = product.qty_available - qty_inv
	        product.sale_stock_available = sale_qty_inv#product.qty_available - qty_inv
		#product.purchase_stock_available = product.qty_available - qty_inv
	    
	    stock_move_lines = self.env['stock.move'].search([('state', 'in', ['assigned']),('product_id','=',product.id)])	
	    purchase_qty_inv = 0
	    if stock_move_lines:
		for line in stock_move_lines:
			if line.picking_id.state != 'done' and line.picking_id.picking_type_id.name == 'Receipts':
				purchase_qty_inv+=line.product_uom_qty
                product.purchase_stock_available = purchase_qty_inv
	    

    @api.multi
    def import_product_images(self,product_ids):
        count = 0
        for obj in [self.browse(product_id) for product_id in product_ids ]:
            file_path = '/home/kmquat/public_html/odoo/addons/kt_kmq/static/src/img/IMAGES_KMQ/'
            if obj.default_code:
                default_code = obj.default_code.replace('/','-')
                #if type(default_code) == 'unicode':
                #    default_code = unicodedata.normalize('NFKD', default_code).encode('ascii','ignore')
                file_path += str(default_code)+'.jpg'
                if os.path.isfile(file_path):
                    count += 1
                    with open(file_path,'rb') as f:
                        encoded_string = base64.b64encode(f.read())
                        f.close()
                        obj.image_medium = encoded_string
                        #self.image_medium = False

    """@api.model
    def create(self,vals):
        headers = {"Content-type": "application/json"}
        client_data = {"username" : "Daniel"}
        client_data_resp = requests.post(url='http://letsap.dedicated.co.za/portmapping/CompanyList.asmx/GetCompanyList', headers=headers,  json=client_data)
        client_data_res = json.loads(client_data_resp.content)
	for data in client_data_res['d']:
                if data['Alias'] == 'PASTELCONNECT':
                        client_handle = data['ClientHandle']
                        continue

        #client_handle = client_data_res['d'][0]['ClientHandle']
	product = self.env['product.template'].browse(vals['product_tmpl_id'])

	a = datetime.strptime(str(datetime.now().date()), '%Y-%m-%d')
        a = int(unix_time_millis(a))
	## Product Dict
	data = {
	  "clientHandle": str(client_handle),
	  "item": {
	    "_allowTax": True,
	    "_barcode": vals.has_key('barcode') and str(vals['barcode']) or '',
	    "_batchSerialItem": 1,
	    "_blocked": False,
	    "_changeDescription": False,
	    "_changeUnitAndQty": False,
	    "_commodityCode": "98",
	    "_createDate": "/Date("+str(a)+"+0200"+")/",
	    "_description": product.name,
	    "_discountType": 0,
	    "_documentLines": None,
	    "_itemCategory": {
	      "_categoryDescription": None,
	      "_createDate": "/Date("+str(a)+"+0200"+")/",
	      "_itemCategoryID": "00000000-0000-0000-0000-000000000000",
	      "_pastelItemCategory": "001",
	      "_updatedOn": "/Date("+str(a)+"+0200"+")/"
	    },
	    "_itemCategoryID": "00000000-0000-0000-0000-000000000000",
	    "_itemID": "00000000-0000-0000-0000-000000000000",
	    "_itemPrices": None,
	    "_itemStoreLinks": [
	      {
	        "_actualQty": 0,
	        "_binNumber": 1,
	        "_createDate": "/Date("+str(a)+"+0200"+")/",
	        "_itemID": "00000000-0000-0000-0000-000000000000",
	        "_itemStoreID": "00000000-0000-0000-0000-000000000000",
	        "_lastInvoiceAmount": 0,
	        "_lastInvoiceDate": None,
	        "_lastPurchaseAmount": 0000,
	        "_lastPurchaseDate": None,
	        "_maximumLevel": 91,
	        "_openingQty": 0,
	        "_reorderLevel": 32,
	        "_storeID": "00000000-0000-0000-0000-000000000000",
	        "_stores": {
	          "_blocked": None,
	          "_cellphone": None,
	          "_contact": None,
	          "_createDate": "/Date("+str(a)+"+0200"+")/",
	          "_description": None,
	          "_email": None,
	          "_fax": None,
	          "_itemPrices": None,
	          "_pastelStoreCode": "001",
	          "_physicalAddress": None,
	          "_postalAddress": None,
	          "_specialPrices": None,
	          "_storeID": "00000000-0000-0000-0000-000000000000",
	          "_telephone": None,
	          "_updatedOn": "/Date("+str(a)+"+0200"+")/"
	        },
	        "_updatedOn": "/Date("+str(a)+"+0200"+")/"
	      }
	    ],
	    "_nettMass": 25,
	    "_packSizeAction": None,
	    "_packSizeItem": None,
	    "_packSizeRatio": 0,
	    "_partnerItemCode": vals.has_key('default_code') and str(vals['default_code']) or '',
	    "_partnerQtyInStore": 0,
	    "_partnerQtyOnHand": 0,
	    "_partnerQtySalesOrder": 0,
	    "_partnerQtyUnPosted": 0,
	    "_physical": False,
	    "_picture": None,
	    "_purchTaxType": 2,
	    "_salesCommision": True,
	    "_salesTaxType": 2,
	    "_specialPrices": None,
	    "_unit": "each",
	    "_updatedOn": "/Date("+str(a)+"+0200"+")/"
	  }
	}

	try:
            if (vals.has_key('default_code') and vals['default_code']):
                resp = requests.post(url='http://letsap.dedicated.co.za/Letsap.Framework.WebHost/KMQAPIService.svc/SaveItem', headers=headers,json=mydict(data))
                if resp.status_code == '200':
                       vals['created_at_pastel'] = True

        except Exception,e:
                print "Exception is:",e
	## End
	return super(Product,self).create(vals) #res

    def write(self,vals):
        if vals.has_key('default_code') and self.default_code:
                raise UserError(_('You cannot change the Internal Reference for a Product.'))
        #res = super(Product,self).write(vals)
       
        headers = {"Content-type": "application/json"}
        client_data = {"username" : "Daniel"}
        client_data_resp = requests.post(url='http://letsap.dedicated.co.za/portmapping/CompanyList.asmx/GetCompanyList', headers=headers,  json=client_data)
        client_data_res = json.loads(client_data_resp.content)
        client_handle = client_data_res['d'][0]['ClientHandle']
	
	a = datetime.strptime(str(datetime.now().date()), '%Y-%m-%d')
        a = int(unix_time_millis(a))

        ## Product Dict
        data = {
          "clientHandle": str(client_handle),
          "item": {
            "_allowTax": True,
            "_barcode": vals.has_key('barcode') and vals['barcode'] or self.barcode,
            "_batchSerialItem": 1,
            "_blocked": False,
            "_changeDescription": False,
            "_changeUnitAndQty": False,
            "_commodityCode": "98",
            "_createDate": "/Date("+str(a)+"+0200"+")/",
            "_description": vals.has_key('name') and vals['name'] or self.product_tmpl_id.name,
            "_discountType": 0,
            "_documentLines": None,
            "_itemCategory": {
              "_categoryDescription": None,
              "_createDate": "/Date("+str(a)+"+0200"+")/",
              "_itemCategoryID": "00000000-0000-0000-0000-000000000000",
              "_pastelItemCategory": "001",
              "_updatedOn": "/Date("+str(a)+"+0200"+")/"
            },
	    "_itemCategoryID": "00000000-0000-0000-0000-000000000000",
            "_itemID": "00000000-0000-0000-0000-000000000000",
            "_itemPrices": None,
            "_itemStoreLinks": [
              {
                "_actualQty": 0,
                "_binNumber": 1,
                "_createDate": "/Date("+str(a)+"+0200"+")/",
                "_itemID": "00000000-0000-0000-0000-000000000000",
                "_itemStoreID": "00000000-0000-0000-0000-000000000000",
                "_lastInvoiceAmount": 0,
                "_lastInvoiceDate": None,
                "_lastPurchaseAmount": 0000,
                "_lastPurchaseDate": None,
                "_maximumLevel": 91,
                "_openingQty": 0,
                "_reorderLevel": 32,
                "_storeID": "00000000-0000-0000-0000-000000000000",
                "_stores": {
                  "_blocked": None,
                  "_cellphone": None,
                  "_contact": None,
                  "_createDate": "/Date("+str(a)+"+0200"+")/",
                  "_description": None,
                  "_email": None,
                  "_fax": None,
                  "_itemPrices": None,
                  "_pastelStoreCode": "001",
                  "_physicalAddress": None,
                  "_postalAddress": None,
                  "_specialPrices": None,
                  "_storeID": "00000000-0000-0000-0000-000000000000",
                  "_telephone": None,
                  "_updatedOn": "/Date("+str(a)+"+0200"+")/"
                },
		"_updatedOn": "/Date("+str(a)+"+0200"+")/"
              }
            ],
            "_nettMass": 25,
            "_packSizeAction": None,
            "_packSizeItem": None,
            "_packSizeRatio": 0,
            "_partnerItemCode": str(self.default_code) or '',
            "_partnerQtyInStore": 0,
            "_partnerQtyOnHand": 0,
            "_partnerQtySalesOrder": 0,
            "_partnerQtyUnPosted": 0,
            "_physical": False,
            "_picture": None,
            "_purchTaxType": 2,
            "_salesCommision": True,
            "_salesTaxType": 2,
            "_specialPrices": None,
            "_unit": "each",
            "_updatedOn": "/Date("+str(a)+"+0200"+")/"
          }
        }

	try:
            
                resp = requests.post(url='http://letsap.dedicated.co.za/Letsap.Framework.WebHost/KMQAPIService.svc/SaveItem', headers=headers,json=mydict(data))
                if resp.status_code == 200:
                        #vals.update({'created_at_pastel':True})
                        vals['created_at_pastel'] = True

        except Exception,e:
                print "Exception is:",e
	

	return super(Product,self).write(vals) #res"""






class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.multi
    def import_product_images(self,product_ids):
        count = 0
        for obj in [self.browse(product_id) for product_id in product_ids ]:
            file_path = '/home/kmquat/public_html/odoo/addons/kt_kmq/static/src/img/IMAGES_KMQ/'
            if obj.default_code:
                default_code = obj.default_code.replace('/','-')
                #if type(default_code) == 'unicode':
                #    default_code = unicodedata.normalize('NFKD', default_code).encode('ascii','ignore')
                file_path += str(default_code)+'.jpg'
                if os.path.isfile(file_path):
                    count += 1
                    with open(file_path,'rb') as f:
                        encoded_string = base64.b64encode(f.read())
                        f.close()
                        obj.image_medium = encoded_string
                        #self.image_medium = False



