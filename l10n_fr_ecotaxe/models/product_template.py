# © 2014-2023 Akretion (http://www.akretion.com)
#   @author Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    ecotaxe_line_product_ids = fields.One2many(
        "ecotaxe.line.product",
        "product_tmplt_id",
        string="Ecotaxe lines",
        copy=True,
    )
    ecotaxe_amount = fields.Float(
        digits="Ecotaxe",
        compute="_compute_ecotaxe",
        help="Ecotaxe Amount computed form Classification",
        store=True,
    )
    fixed_ecotaxe = fields.Float(
        "Fixed Ecotaxe",
        compute="_compute_ecotaxe",
        help="Fixed ecotaxe of the " "Ecotaxe Classification\n",
    )
    weight_based_ecotaxe = fields.Float(
        "Weight Based Ecotaxe",
        compute="_compute_ecotaxe",
        help="Ecotaxe value :\n"
        "product weight * ecotaxe coef of "
        "Ecotaxe Classification\n",
    )

    @api.depends(
        "ecotaxe_line_product_ids",
        "ecotaxe_line_product_ids.classification_id",
        "ecotaxe_line_product_ids.classification_id.ecotaxe_type",
        "ecotaxe_line_product_ids.classification_id.ecotaxe_coef",
        "ecotaxe_line_product_ids.force_amount",
        "weight",
    )
    def _compute_ecotaxe(self):
        for tmpl in self:
            amount_ecotaxe = 0.0
            weight_based_ecotaxe = 0.0
            fixed_ecotaxe = 0.0
            for ecotaxeline_prod in tmpl.ecotaxe_line_product_ids:
                ecotax_cls = ecotaxeline_prod.classification_id
                if ecotax_cls.ecotaxe_type == "weight_based":
                    weight_based_ecotaxe += ecotaxeline_prod.amount
                else:
                    fixed_ecotaxe += ecotaxeline_prod.amount

                amount_ecotaxe += ecotaxeline_prod.amount
            tmpl.fixed_ecotaxe = fixed_ecotaxe
            tmpl.weight_based_ecotaxe = weight_based_ecotaxe
            tmpl.ecotaxe_amount = amount_ecotaxe
