# © 2014-2023 Akretion (http://www.akretion.com)
#   @author Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    ecotaxe_classification_ids = fields.Many2many(
        "account.ecotaxe.classification",
        "product_template_rel_ecotaxe_classif",
        string="Ecotaxe Classifications",
    )
    ecotaxe_amount = fields.Monetary(
        compute="_compute_ecotaxe",
        help="Ecotaxe Amount computed form Classification",
        store=True,
    )
    force_ecotaxe_amount = fields.Monetary(
        help="Force ecotaxe amount.\n"
        "Allow to subtite default Ecotaxe Classification\n"
    )

    @api.depends(
        "ecotaxe_classification_ids",
        "ecotaxe_classification_ids.ecotaxe_type",
        "ecotaxe_classification_ids.ecotaxe_coef",
        "weight",
        "force_ecotaxe_amount",
    )
    def _compute_ecotaxe(self):
        for tmpl in self:
            amt = 0.0
            for ecotax_cls in tmpl.ecotaxe_classification_ids:
                if ecotax_cls.ecotaxe_type == "weight_based":
                    amt += ecotax_cls.ecotaxe_coef * (tmpl.weight or 0.0)
                elif tmpl.force_ecotaxe_amount:
                    amt += tmpl.force_ecotaxe_amount
                else:
                    amt += ecotax_cls.default_fixed_ecotaxe
            tmpl.ecotaxe_amount = amt
