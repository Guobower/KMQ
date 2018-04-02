import xmlrpclib

username = 'admin' #the user
pwd = 'Str@teg1c321'      #the password of the user
dbname = 'kmq'    #the database

# OpenERP Common login Service proxy object 
sock_common = xmlrpclib.ServerProxy ('http://kmq.odoo.co.za/xmlrpc/common')
print"success =========="
uid = sock_common.login(dbname, username, pwd)
print"******** Connected ******** ",uid

# replace localhost with the address of the server
#  OpenERP Object manipulation service 
sock = xmlrpclib.ServerProxy('http://kmq.odoo.co.za/xmlrpc/object')
sale_ids = sock.execute(dbname, uid, pwd, 'sale.order', 'search', [])
print"******** Starts Update ******** "
for sale in sale_ids:
    sock.execute(dbname, uid, pwd, 'sale.order', 'compute_invoice_set_has_invoice', sale)
print"******** Successfully updated ********"
