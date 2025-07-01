# Copyright 2017-2020 Akretion France (http://www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    invoice_transmit_method_id = fields.Many2one(
        related="partner_invoice_id.customer_invoice_transmit_method_id",
        string="Invoice Transmission Method",
    )
    invoice_transmit_method_code = fields.Char(
        related="partner_invoice_id.customer_invoice_transmit_method_id.code",
    )

    def action_confirm(self):
        """Check validity of Chorus orders"""
        for order in self.filtered(
            lambda so: so.invoice_transmit_method_code == "fr-chorus"
        ):
            order._chorus_validation_checks()
        return super().action_confirm()

    def _chorus_validation_checks(self):
        invpartner = self.partner_invoice_id
        cpartner = invpartner.commercial_partner_id
        if not cpartner.siren or not cpartner.nic:
            raise UserError(
                _(
                    "Missing SIRET on partner '%s'. "
                    "This information is required for Chorus invoices."
                )
                % cpartner.display_name
            )
        if (
            cpartner.fr_chorus_required in ("service", "service_and_engagement")
            and not invpartner.chorus_service_ok()
        ):
            raise UserError(
                _(
                    "Partner '%s' is configured as "
                    "Service required for Chorus, so you must "
                    "select a contact as invoicing address for the order %s "
                    "and this contact should have a name and a Chorus service "
                    "and the Chorus service must be active."
                )
                % (cpartner.display_name, self.name)
            )
        if cpartner.fr_chorus_required in ("engagement", "service_and_engagement"):
            if self.ej_number:
                self.chorus_order_check_commitment_number()
            else:
                raise UserError(
                    _(
                        "The field 'Customer Reference' of order %s should "
                        "contain the engagement number because customer '%s' is "
                        "configured as Engagement required for Chorus."
                    )
                    % (self.name, cpartner.display_name)
                )
        elif (
            invpartner.fr_chorus_service_id
            and invpartner.fr_chorus_service_id.engagement_required
        ):
            if self.ej_number:
                self.chorus_order_check_commitment_number()
            else:
                raise UserError(
                    _(
                        "Partner '%s' is linked to Chorus service '%s' "
                        "which is marked as 'Engagement required', so the "
                        "field 'Customer Reference' of its orders must "
                        "contain an engagement number."
                    )
                    % (
                        invpartner.display_name,
                        invpartner.fr_chorus_service_id.code,
                    )
                )
        if cpartner.fr_chorus_required == "service_or_engagement":
            if not invpartner.chorus_service_ok():
                if not self.ej_number:
                    raise UserError(
                        _(
                            "Partner '%s' is configured as "
                            "Service or Engagement required for Chorus but "
                            "there is no engagement number in the field "
                            "'Customer Reference' of order %s and the invoice "
                            "address is not a contact (Chorus Service can only be "
                            "configured on contacts)"
                        )
                        % (cpartner.display_name, self.name)
                    )
                else:
                    self.chorus_order_check_commitment_number()

    def chorus_order_check_commitment_number(self, raise_if_not_found=True):
        self.ensure_one()
        res = self.env["account.move"].chorus_check_commitment_number(
            self.company_id,
            self.ej_number,
            raise_if_not_found=raise_if_not_found,
        )
        if res is True:
            self.message_post(
                body=_("Engagement juridique <b>%s</b> checked via Chorus Pro API.")
                % self.ej_number
            )
        return res
