{
    'name' : 'KMQ Quotation System',
    'version' : '1.1',
    'summary': 'Provide ability for the sales users to generate the quote with product branding options',
    'category': 'Sales',
    'sequence': 30,
    'description': """ KMQ Quotation : Provide ability for the sales users to generate the quote with product branding options """,
    'depends' : ['base_setup', 'product', 'sale', 'sales_team','purchase','website_quote',
                 'project', 'website_sale', 'website_sign', 'smsclient', 'crm',
                 'delivery', 'partner_credit_limit','sale_exception_credit_limit'],
    'data': [
		'security/kmq_security.xml',
		'views/branding_customizations_view.xml',
		'views/sale_order_view.xml',
		'views/account_invoice_view.xml',#Jagadeesh
		'views/project_view.xml',	
		'views/res_partner_view.xml',#Jagadeesh
		'views/templates.xml',
		'views/website_quote_templates.xml',
		'report/sale_report_template.xml',#Jagadeesh
		'report/invoice_report.xml',
		'report/delivery_slip_report.xml',
		'report/stock_operation_report.xml',
		'security/ir.model.access.csv',
		'security/sale_security.xml', #Jagadeesh
        'report/invoice_stock_report.xml',
        'wizard/inventory_check_wizard_views.xml',
        'views/product_view.xml',
            ],
    'installable': True,
    'application': True,
    'auto_install': False,
}

