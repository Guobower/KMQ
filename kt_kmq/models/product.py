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

class ProductCategory(models.Model):
	_inherit = 'product.category'
	pastel_code = fields.Char('Pastel Code')

class StockMove(models.Model):
    _inherit = "stock.move"
    ordered_qty = fields.Float('Ordered Quantity', digits=dp.get_precision('Product Unit of Measure2'))
    product_uom_qty = fields.Float(
        'Quantity',
        digits=dp.get_precision('Product Unit of Measure2'),
        default=1.0, required=True, states={'done': [('readonly', True)]},
        help="This is the quantity of products from an inventory "
             "point of view. For moves in the state 'done', this is the "
             "quantity of products that were actually moved. For other "
             "moves, this is the quantity of product that is planned to "
             "be moved. Lowering this quantity does not generate a "
             "backorder. Changing this quantity on assigned moves affects "
             "the product reservation, and should be done with care.")

class PackOperation(models.Model):
    _inherit = "stock.pack.operation"
    product_qty = fields.Float('To Do', default=0.0, digits=dp.get_precision('Product Unit of Measure2'), required=True)
    ordered_qty = fields.Float('Ordered Quantity', digits=dp.get_precision('Product Unit of Measure2'))
    qty_done = fields.Float('Done', default=0.0, digits=dp.get_precision('Product Unit of Measure2'))





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

    fixed_price = fields.Float('Fixed Price', digits=dp.get_precision('Product Price'))
    
    @api.multi
    def set_price(self):
        print"set_price========",self
        tmpl_id = self.product_tmpl_id.id
        pricelist_items = self.search([('product_tmpl_id', '=', tmpl_id)])
        print"pricelist_items=========",pricelist_items
        
#     @api.onchange('fixed_price')
#     def onchange_fixed_price(self):
#         

class Product(models.Model):
    _inherit = "product.product"

    stock_available = fields.Float('Stock Available(001)',compute='_compute_quantities_revised',digits=dp.get_precision('Product Unit of Measure'))
    stock_available2 = fields.Float('Stock Available(004)',compute='_compute_quantities_revised',digits=dp.get_precision('Product Unit of Measure'))
    sale_stock_available = fields.Float('Sale Orders',compute='_compute_quantities_revised',digits=dp.get_precision('Product Unit of Measure'))
    purchase_stock_available = fields.Float('Purchase Orders',compute='_compute_quantities_revised',digits=dp.get_precision('Product Unit of Measure'))
    created_at_pastel = fields.Boolean('Created at Pastel')
    page_number = fields.Char('Page Number')
    size = fields.Char('Size')
    box_size = fields.Char('Box Size')
    qty_per_box = fields.Float('Qty per Box')
    weight_per_box = fields.Float('Weight per Box')
    pricelist_item_ids = fields.Many2many('product.pricelist.item', 'Pricelist Items')

    #@api.depends('stock_quant_ids', 'stock_move_ids')
    def _compute_quantities_revised(self):
        #qty_inv = 0
        #sale_qty_inv = 0
        #wh_stock_location_id = self.env['stock.location'].search([('complete_name','=','WH/Stock')]).id
        #004_stock_location_id = self.env['stock.location'].search([('complete_name','=','004/Stock')]).id
        a = "WH/Stock"
        b = "004/Stock"

        wh_stock_location_id = self.env['stock.location'].search([('complete_name','=',a)]).id
        wh_stock_location_id_4 = self.env['stock.location'].search([('complete_name','=',b)]).id

        for product in self:
            sale_qty_inv = 0
            qty_inv = 0
            sale_order_lines = self.env['sale.order.line'].search([('state', 'in', ['sale', 'done']),('product_id','=',product.id)])
            if sale_order_lines:
                for line in sale_order_lines:
                    qty_inv+=line.qty_invoiced
                    sale_qty_inv+= (line.qty_to_invoice)
                    product.stock_available = product.with_context({'location' : wh_stock_location_id}).qty_available - product.with_context({'location' : wh_stock_location_id}).outgoing_qty#qty_inv
                    product.stock_available2 = product.with_context({'location' : wh_stock_location_id_4}).qty_available
                    product.sale_stock_available = sale_qty_inv#product.qty_available - qty_inv
                
                stock_move_lines = self.env['stock.move'].search([('state', 'in', ['assigned']),('product_id','=',product.id)])    
                purchase_qty_inv = 0
                if stock_move_lines:
                    for line in stock_move_lines:
                        if line.picking_id.state != 'done' and line.picking_id.picking_type_id.name == 'Receipts':
                            purchase_qty_inv+=line.product_uom_qty
                product.purchase_stock_available = purchase_qty_inv
                    #product.purchase_stock_available = product.qty_available - qty_inv
            else:
                product.stock_available = product.with_context({'location' : wh_stock_location_id}).qty_available #product.qty_available
                product.stock_available2 = product.with_context({'location' : wh_stock_location_id_4}).qty_available
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
            file_path = '/home/kmq/public_html/odoo/addons/kt_kmq/static/src/img/IMAGES_KMQ/'
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

    @api.model
    def create222222(self,vals):
        headers = {"Content-type": "application/json"}
        client_data = {"username" : "Daniel"}
        client_data_resp = requests.post(url='http://letsap.dedicated.co.za/portmapping/CompanyList.asmx/GetCompanyList', headers=headers,  json=client_data)
        client_data_res = json.loads(client_data_resp.content)
	for data in client_data_res['d']:
                if data['Alias'] == 'PASTELCONNECT':
                        client_handle = data['ClientHandle']
                        continue

        #client_handle = client_data_res['d'][0]['ClientHandle']
	if vals.has_key('product_tmpl_id') and vals['product_tmpl_id']:
		product = self.env['product.template'].browse(vals['product_tmpl_id'])
		if vals.has_key('type') and vals['type'] == 'product':
			physical = True
		else:
			physical = False

		if vals.has_key('categ_id') and vals['categ_id']:
			pastel_categ_code = self.env['product.category'].browse(vals['categ_id']).pastel_code
		else:
			pastel_categ_code = None

		if vals.has_key('tracking') and vals['tracking'] == 'serial':
                	batch_serial_no = 1
	        else:
        	        batch_serial_no = 0

	        if vals.has_key('active') and vals['active'] == True:
        	        blocked = False
	        else:
        	        blocked = True


		a = datetime.strptime(str(datetime.now().date()), '%Y-%m-%d')
	        a = int(unix_time_millis(a))
		## Product Dict
		data = {
		  "clientHandle": str(client_handle),
		  "item": {
		    "_allowTax": True,
		    "_barcode": vals.has_key('barcode') and str(vals['barcode']) or None,
		    "_batchSerialItem": batch_serial_no,
		    "_blocked": blocked,
		    "_changeDescription": False,
		    "_changeUnitAndQty": False,
		    "_commodityCode": None,
		    "_createDate": "/Date("+str(a)+"+0200"+")/",
		    "_description": product.name,
		    "_discountType": 3,
		    "_documentLines": None,
		    "_itemCategory": {
		      "_categoryDescription": None,
		      "_createDate": "/Date("+str(a)+"+0200"+")/",
		      "_itemCategoryID": "00000000-0000-0000-0000-000000000000",
		      "_pastelItemCategory": pastel_categ_code,
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
		    "_nettMass": 0,
		    "_packSizeAction": None,
		    "_packSizeItem": None,
		    "_packSizeRatio": 0,
		    "_partnerItemCode": vals.has_key('default_code') and str(vals['default_code']) or '',
		    "_partnerQtyInStore": 0,
		    "_partnerQtyOnHand": 0,
		    "_partnerQtySalesOrder": 0,
		    "_partnerQtyUnPosted": 0,
		    "_physical": physical,
		    "_picture": None,
		    "_purchTaxType": 1,
		    "_salesCommision": True,
		    "_salesTaxType": 1,
		    "_specialPrices": None,
		    "_unit": "Each",
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
	
    def write2222(self,vals):
        if vals.has_key('default_code') and self.default_code:
                raise UserError(_('You cannot change the Internal Reference for a Product.'))
        #res = super(Product,self).write(vals)
       
        headers = {"Content-type": "application/json"}
        client_data = {"username" : "Daniel"}
        client_data_resp = requests.post(url='http://letsap.dedicated.co.za/portmapping/CompanyList.asmx/GetCompanyList', headers=headers,  json=client_data)
        client_data_res = json.loads(client_data_resp.content)
        client_handle = client_data_res['d'][0]['ClientHandle']

	prod_data_resp = requests.post(url='http://letsap.dedicated.co.za/Letsap.Framework.WebHost/KMQAPIService.svc/GetItem', headers=headers,  json={"itemID":self.default_code})
	prod_data = json.loads(prod_data_resp.content)
	create_date = prod_data['GetItemResult']['_createDate']
	
	a = datetime.strptime(str(datetime.now().date()), '%Y-%m-%d')
        a = int(unix_time_millis(a))

	if vals.has_key('type') and vals['type'] == 'product':
                physical = True
	elif self.type and self.type == 'product':
		physical = True
	else:
	        physical = False

	if vals.has_key('categ_id') and vals['categ_id']:
	        pastel_categ_code = self.env['product.category'].browse(vals['categ_id']).pastel_code
	elif self.categ_id:
		pastel_categ_code = self.categ_id.pastel_code
	else:
        	pastel_categ_code = None

	if vals.has_key('tracking') and vals['tracking'] == 'serial':
		batch_serial_no = 1
	elif self.tracking == 'serial':
		batch_serial_no = 1
	else:
		batch_serial_no = 0

	if vals.has_key('active') and vals['active'] == True:	
		blocked = False
	elif self.active == True:
		blocked = False
	else:
		blocked = True

        ## Product Dict
        data = {
          "clientHandle": str(client_handle),
          "item": {
            "_allowTax": True,
            "_barcode": vals.has_key('barcode') and vals['barcode'] or self.barcode or None,
            "_batchSerialItem": batch_serial_no,
            "_blocked": blocked,
            "_changeDescription": False,
            "_changeUnitAndQty": False,
            "_commodityCode": None,
            "_createDate": str(create_date),
            "_description": vals.has_key('name') and vals['name'] or self.product_tmpl_id.name,
            "_discountType": 3,
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
            "_nettMass": 0,
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
            "_purchTaxType": 1,
            "_salesCommision": True,
            "_salesTaxType": 1,
            "_specialPrices": None,
            "_unit": "Each",
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
	

	return super(Product,self).write(vals)






class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.multi
    def import_product_images(self,product_ids):
        count = 0
        for obj in [self.browse(product_id) for product_id in product_ids ]:
            file_path = '/home/kmq/public_html/odoo/addons/kt_kmq/static/src/img/IMAGES_KMQ/'
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



