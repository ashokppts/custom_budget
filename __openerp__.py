# -*- encoding: utf-8 -*-
###########################################################################
#    Module Writen to OpenERP, Open Source Management Solution
#
##############################################################################

{
    "name" : "Account Budget Improvements",
    "version" : "1.0",
    "author" : "PPTS",
    'category' : 'Accounting & Finance',
    "description" : """
Improvements to Account Budget
==============================

The Account Budget view will be used to comply with need to show the executed
Budget per period.
    """,
    "website" : "http://www.pptssolutions.com/",
    "license" : "AGPL-3",
    "depends" : [
        "account_budget",
        "account_accountant",
        "ifrs_report",
        "web_kanban",
    ],
    "data" : [
        "view/account_budget_view.xml",
        "security/res_groups.xml",
        "data/account_budget_data.xml",
    ],
    "demo" : [
    ],
    "css": [
        "static/src/css/account_budget.css",
    ],
    "js": [
        "static/src/js/account_budget_imp.js",
    ],
    "test" : [
    ],
    "installable" : True,
    "active" : False,
}
