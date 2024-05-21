# © 2014-2023 Akretion (http://www.akretion.com)
#   @author Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AcountMoveLine(models.Model):
    _inherit = "account.move.line"

    ecotaxe_line_ids = fields.One2many(
        "account.move.line.ecotaxe",
        "account_move_line_id",
        string="Ecotaxe lines",
        copy=True,
    )
    subtotal_ecotaxe = fields.Float(
        digits="Ecotaxe", store=True, compute="_compute_ecotaxe"
    )
    ecotaxe_amount_unit = fields.Float(
        digits="Ecotaxe",
        string="Ecotaxe Unit.",
        store=True,
        compute="_compute_ecotaxe",
    )

    @api.depends(
        "move_id.currency_id",
        "ecotaxe_line_ids",
        "ecotaxe_line_ids.amount_unit",
        "ecotaxe_line_ids.amount_total",
    )
    def _compute_ecotaxe(self):
        for line in self:
            ecotaxe_ids = line.tax_ids.filtered(lambda tax: tax.is_ecotaxe)
            import pdb

            pdb.set_trace()

            if line.display_type == "tax" or not ecotaxe_ids:
                continue
            if line.display_type == "product" and line.move_id.is_invoice(True):
                amount_currency = line.price_unit * (1 - line.discount / 100)
                handle_price_include = True
                quantity = line.quantity
            else:
                amount_currency = line.amount_currency
                handle_price_include = False
                quantity = 1
            compute_all_currency = ecotaxe_ids.compute_all(
                amount_currency,
                currency=line.currency_id,
                quantity=quantity,
                product=line.product_id,
                partner=line.move_id.partner_id or line.partner_id,
                is_refund=line.is_refund,
                handle_price_include=handle_price_include,
                include_caba_tags=line.move_id.always_tax_exigible,
            )
            subtotal_ecotaxe = 0.0
            for tax in compute_all_currency["taxes"]:
                subtotal_ecotaxe += tax["amount"]

            unit = quantity and subtotal_ecotaxe / quantity or subtotal_ecotaxe
            line.ecotaxe_amount_unit = unit
            line.subtotal_ecotaxe = subtotal_ecotaxe

    @api.onchange("product_id")
    def _onchange_product_ecotaxe_line(self):
        """Unlink and recreate ecotaxe_lines when modifying the product_id."""
        if self.product_id:
            self.ecotaxe_line_ids = [(5,)]  # Remove all ecotaxe classification
            ecotax_cls_vals = []
            for ecotaxeline_prod in self.product_id.all_ecotaxe_line_product_ids:
                classif_id = ecotaxeline_prod.classification_id.id
                forced_amount = ecotaxeline_prod.force_amount
                ecotax_cls_vals.append(
                    (
                        0,
                        0,
                        {
                            "classification_id": classif_id,
                            "force_amount_unit": forced_amount,
                        },
                    )
                )
            self.ecotaxe_line_ids = ecotax_cls_vals
        else:
            self.ecotaxe_line_ids = [(5,)]  # Remove all ecotaxe classification

    def edit_ecotaxe_lines(self):
        view = {
            "name": ("Ecotaxe classification"),
            "view_type": "form",
            "view_mode": "form",
            "res_model": "account.move.line",
            "view_id": self.env.ref("l10n_fr_ecotaxe.view_move_line_ecotaxe_form").id,
            "type": "ir.actions.act_window",
            "target": "new",
            "res_id": self.id,
        }
        return view

    def _get_computed_taxes(self):
        tax_ids = super()._get_computed_taxes()
        if self.move_id.is_sale_document(include_receipts=True):
            # Out invoice.
            sale_ecotaxes = self.product_id.all_ecotaxe_line_product_ids.mapped(
                "classification_id"
            ).mapped("sale_ecotaxe_ids")
            ecotaxe_ids = sale_ecotaxes.filtered(
                lambda tax: tax.company_id == self.move_id.company_id
            )

        elif self.move_id.is_purchase_document(include_receipts=True):
            # In invoice.
            purchase_ecotaxes = self.product_id.all_ecotaxe_line_product_ids.mapped(
                "classification_id"
            ).mapped("purchase_ecotaxe_ids")
            ecotaxe_ids = purchase_ecotaxes.filtered(
                lambda tax: tax.company_id == self.move_id.company_id
            )

        if ecotaxe_ids and self.move_id.fiscal_position_id:
            ecotaxe_ids = self.move_id.fiscal_position_id.map_tax(ecotaxe_ids)
        if ecotaxe_ids:
            tax_ids |= ecotaxe_ids

        return tax_ids
