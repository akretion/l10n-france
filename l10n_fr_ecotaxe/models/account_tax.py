# © 2014-2024 Akretion (http://www.akretion.com)
#   @author Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    is_ecotaxe = fields.Boolean(
        "Ecotaxe",
        help="Warning : To include Ecotaxe "
        "in the VAT tax check this :\n"
        '1: check  "included in base amount "\n'
        "2: The Ecotaxe sequence must be less then "
        "VAT tax (in sale and purchase)",
    )

    @api.onchange("is_ecotaxe")
    def onchange_is_ecotaxe(self):
        if self.is_ecotaxe:
            self.amount_type = "code"
            self.include_base_amount = True
            self.python_compute = """
# price_unit
# product: product.product object or None
# partner: res.partner object or None
# for weight based ecotaxe
# result = product.weight_based_ecotaxe or 0.0
result = product.ecotaxe_amount or 0.0
            """
