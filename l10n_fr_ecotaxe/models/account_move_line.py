# © 2014-2023 Akretion (http://www.akretion.com)
#   @author Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AcountMoveLine(models.Model):
    _inherit = "account.move.line"

    ecotaxe_line_ids = fields.One2many(
        'account.move.line.ecotaxe',
        "account_move_line_id",
        string="Ecotaxe lines",
        copy = True,
    )
    subtotal_ecotaxe = fields.Float(store=True, compute="_compute_ecotaxe")
    ecotaxe_amount_unit = fields.Float(
        string="Ecotaxe Unit.",
        store=True,
        compute="_compute_ecotaxe",
    )

    @api.depends("move_id.currency_id", "ecotaxe_line_ids",
                 "ecotaxe_line_ids.ecotaxe_amount_unit",
                 "ecotaxe_line_ids.ecotaxe_amount_total")
    def _compute_ecotaxe(self):
        for line in self:
            unit = sum(line.ecotaxe_line_ids.mapped('ecotaxe_amount_unit'))
            subtotal_ecotaxe = sum(line.ecotaxe_line_ids.mapped('ecotaxe_amount_total'))

            if line.move_id.currency_id:
                unit = line.move_id.currency_id.round(unit)
                subtotal_ecotaxe = line.move_id.currency_id.round(subtotal_ecotaxe)
            line.update(
                {
                    "ecotaxe_amount_unit": unit,
                    "subtotal_ecotaxe": subtotal_ecotaxe,
                }
            )

    @api.onchange('product_id')
    def _onchange_product_ecotaxe_line(self):
        """ Unlink and recreate ecotaxe_lines when modifying the product_id."""
        if not self.product_id:
            self.ecotaxe_line_ids = [(5,)]  # Remove all ecotaxe classification
        else:
            ecotax_cls_vals = []
            for ecotax_cls in self.product_id.ecotaxe_classification_ids:
                ecotax_cls_vals.append(
                    (0, 0, {'ecotaxe_classification_id': ecotax_cls.id})
                )
            self.ecotaxe_line_ids = ecotax_cls_vals
