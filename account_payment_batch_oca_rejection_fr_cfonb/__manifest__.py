# Copyright 2026 Akretion France (https://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Payment order CFONB rejection files for France",
    "version": "16.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "summary": "Import payment order rejection files in CFONB format",
    "author": "Akretion,Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "development_status": "Beta",
    "website": "https://github.com/OCA/l10n-france",
    "depends": ["account_payment_order"],
    "data": [
        "security/ir.model.access.csv",
        "wizards/account_payment_order_rejection_import_view.xml",
        "views/account_payment.xml",
    ],
    "installable": True,
}
