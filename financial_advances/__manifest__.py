{
    "name": "Financial Advances",
    "author": "Yaseen Kouteh",
    "category": "",
    "version": "1.0",
    "depends": [
        "hr",'account','mail'
        ],
    "license": "LGPL-3",
    'application': True,
    "data": [
        'security/ir.model.access.csv',
        "views/base_menu.xml",
        "views/employee_financial.xml",
        "views/farmer_financial.xml",
        "views/financia_configuration.xml",
        "views/res_partner_inherit.xml",
        "views/hr_employee_inherit.xml",
        "views/website_account_custom.xml",
        # "views/financial_advance_portal.xml",
        "views/financial_advanced_po.xml",
    ],
    "assets": {
        "web.assets_backend": [
        ],
    },
}