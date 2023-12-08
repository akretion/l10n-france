# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Ecotaxe Accounting",
    "summary": "Automatically isolate ecotaxe amount in a dedicated account",
    "version": "16.0.1.0.0",
    "category": "French Localization",
    "author": "Akretion,Odoo Community Association (OCA)",
    "maintainers": ["florian-dacosta"],
    "website": "https://github.com/OCA/l10n-france",
    "license": "AGPL-3",
    "depends": ["l10n_fr_ecotaxe"],
    "data": [
        "views/account_ecotaxe_classification.xml",
        "views/res_config_settings.xml",
    ],
    "installable": True,
}
