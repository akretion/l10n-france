# Copyright 2026 Akretion France (https://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
import re
from datetime import datetime

from stdnum.iban import calc_check_digits as iban_calc_check_digits

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools.misc import format_amount, format_date

_logger = logging.getLogger(__name__)
CFONB_WIDTH = 240


class AccountPaymentOrderRejectionImport(models.TransientModel):
    _name = "account.payment.order.rejection.import"
    _description = "Wizard to import payment order rejection files"

    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    attachment_ids = fields.Many2many(
        "ir.attachment", string="CFONB Rejection Files", required=True
    )
    state = fields.Selection(
        [
            ("import", "Import File"),
            ("check", "Check Rejection Lines"),
        ],
        default="import",
        required=True,
    )
    line_ids = fields.One2many(
        "account.payment.order.rejection.line", "wizard_id", string="Rejection Lines"
    )

    def _prepare_rejection_line(self, pivot_line, speedy):
        lvals = {
            "company_name": pivot_line.get("company_name"),
            "reason": pivot_line.get("reason"),
            "label": pivot_line.get("label"),
            "rejection_amount": pivot_line.get("rejection_amount"),
            "partner_name": pivot_line.get("partner_name"),
            "payment_date": pivot_line.get("payment_date"),
            "rejection_date": pivot_line.get("rejection_date"),
            "payment_type": pivot_line.get("payment_type"),
            "payment_method_code": pivot_line.get("payment_method_code"),
            "attachment_id": pivot_line.get("attachment_id"),
        }
        if pivot_line.get("currency_code"):
            currency_code = pivot_line["currency_code"].upper()
            if currency_code not in speedy["currency_code2id"]:
                raise UserError(
                    _(
                        "Filename %(filename)s line %(line)s: "
                        "extracted currency %(currency_code)s is not a valid currency.",
                        filename=pivot_line["filename"],
                        line=pivot_line["line"],
                        currency_code=currency_code,
                    )
                )
            lvals["currency_id"] = speedy["currency_code2id"][currency_code]
        if (
            pivot_line.get("company_iban")
            and pivot_line["company_iban"] in speedy["company_iban2id"]
        ):
            lvals["company_partner_bank_id"] = speedy["company_iban2id"][
                pivot_line["company_iban"]
            ]
            if lvals["company_partner_bank_id"] in speedy["partner_bank_id2journal_id"]:
                lvals["journal_id"] = speedy["partner_bank_id2journal_id"][
                    lvals["company_partner_bank_id"]
                ]
        if (
            pivot_line.get("partner_iban")
            and pivot_line["partner_iban"] in speedy["partner_iban2id"]
        ):
            lvals["partner_bank_id"] = speedy["partner_iban2id"][
                pivot_line["partner_iban"]
            ]
        return lvals

    def import_files(self):
        self.ensure_one()
        if not self.attachment_ids:
            raise UserError(_("Missing rejection file(s)."))
        pivot_lines = []
        for attach in self.attachment_ids:
            pivot_lines += self._parse_cfonb_reject_file(attach)
        vals = {"state": "check", "line_ids": []}
        currency_code2id = {
            x["name"]: x["id"]
            for x in self.env["res.currency"].search_read([], ["name"])
        }
        company = self.company_id
        company_partner = company.partner_id
        company_iban2id = {
            x.sanitized_acc_number: x.id
            for x in company_partner.bank_ids
            if x.acc_type == "iban"
        }
        bank_journals = self.env["account.journal"].search_read(
            [
                ("company_id", "=", company.id),
                ("type", "=", "bank"),
                ("bank_account_id", "!=", False),
            ],
            ["bank_account_id"],
        )
        partner_bank_id2journal_id = {
            x["bank_account_id"][0]: x["id"] for x in bank_journals
        }
        partner_bank_accounts = self.env["res.partner.bank"].search_read(
            [
                ("company_id", "in", (False, company.id)),
                ("partner_id", "!=", company_partner.id),
                ("sanitized_acc_number", "=like", "FR%"),
            ],
            ["sanitized_acc_number"],
        )
        partner_iban2id = {
            x["sanitized_acc_number"]: x["id"] for x in partner_bank_accounts
        }
        speedy = {
            "currency_code2id": currency_code2id,
            "company_iban2id": company_iban2id,
            "partner_bank_id2journal_id": partner_bank_id2journal_id,
            "partner_iban2id": partner_iban2id,
        }
        for pivot_line in pivot_lines:
            lvals = self._prepare_rejection_line(pivot_line, speedy)
            vals["line_ids"].append(Command.create(lvals))
        self.write(vals)
        action = self.env["ir.actions.actions"]._for_xml_id(
            "account_payment_batch_oca_rejection_fr_cfonb."
            "account_payment_order_rejection_import_action"
        )
        action["res_id"] = self.id
        return action

    # PIVOT format: list of dicts
    # {
    # 'filename': ,
    # 'line': 2,  # line number inside file
    # 'company_iban': 'FR76xxxxx',
    # 'company_name': 'My company',
    # 'partner_iban': 'FR76zzzzz',
    # 'partner_name': 'Deco Addict',
    # 'label': '',
    # 'reason': '',
    # 'rejection_amount': 12.22,  # positive
    # 'currency_code': 'EUR',
    # 'rejection_date': python date object,
    # 'payment_date': python date object,
    # 'payment_type': 'inbound',
    # 'payment_method_code': 'sepa_direct_debit'  # or 'fr_lcr'
    # 'attachment_id': 15,
    # }

    def _parse_cfonb_reject_file(self, attach):
        filename = attach.name
        _logger.info("Starting to parse file %s", filename)
        lines = self._cfonb_split_lines(attach)
        pivot_lines = []
        reason_code2label = self._cfonb_rejection_reason_codes()
        operation_code2payment_code = {
            "81": "sepa_direct_debit",
            "61": "fr_lcr",
        }
        i = 0
        for line in lines:
            i += 1
            err_prefix = _("File '%(filename)s' line %(i)s:", filename=filename, i=i)
            _logger.debug("Line %d: %s" % (i, line))
            assert len(line) == CFONB_WIDTH
            rec_type = line[0:2]
            if rec_type == "34":  # regular line
                operation_code = line[8:10]
                if operation_code not in operation_code2payment_code:
                    _logger.info(
                        "Ignoring line %s because operation code is %s",
                        i,
                        operation_code,
                    )
                    continue
                payment_code = operation_code2payment_code[operation_code]
                currency_cfonb = line[16]
                if currency_cfonb != "E":
                    raise UserError(
                        _(
                            "%(err_prefix)s on position 17, letter is "
                            "%(currency_cfonb)s instead of 'E' (for Euro).",
                            err_prefix=err_prefix,
                            currency_cfonb=currency_cfonb,
                        )
                    )
                currency_code = "EUR"
                company_bank_code = line[21:26]
                company_guichet_code = line[26:31]
                company_acc_number = line[31:42]
                company_name = line[42:66].strip()
                amount_str_cents = line[228:240].strip()
                try:
                    amount_int_cents = int(amount_str_cents)
                except Exception as e:
                    raise UserError(
                        _(
                            "%(err_prefix)s could not parse the amount (%(amount_str_cents)s).",
                            err_prefix=err_prefix,
                            amount_str_cents=amount_str_cents,
                        )
                    ) from e
                amount = amount_int_cents / 100
                rejection_date_str = line[10:16]
                reason_code = line[226:228]
                reason = reason_code2label.get(reason_code)
                partner_bank_code = line[77:82]
                partner_guichet_code = line[82:87]
                partner_acc_number = line[87:98]
                partner_name = line[98:122].strip()
                # different between SDD and LCR:
                if payment_code == "sepa_direct_debit":
                    label = line[152:183].strip()
                    payment_date_str = line[214:220]
                elif payment_code == "fr_lcr":
                    label = line[138:148]
                    payment_date_str = line[212:218]
                try:
                    payment_date = datetime.strptime(payment_date_str, "%d%m%y")
                except Exception:
                    payment_date = False
                try:
                    rejection_date = datetime.strptime(rejection_date_str, "%d%m%y")
                except Exception:
                    rejection_date = False

                pivot_dict = {
                    "filename": filename,
                    "line": i,
                    "company_name": company_name,
                    "company_iban": self._generate_fr_iban(
                        company_bank_code, company_guichet_code, company_acc_number
                    ),
                    "rejection_amount": amount,
                    "currency_code": currency_code,
                    "rejection_date": rejection_date,
                    "payment_date": payment_date,
                    "label": label,
                    "reason": reason,
                    "partner_name": partner_name,
                    "partner_iban": self._generate_fr_iban(
                        partner_bank_code, partner_guichet_code, partner_acc_number
                    ),
                    "payment_type": "inbound",
                    "payment_method_code": payment_code,
                    "attachment_id": attach.id,
                }
                pivot_lines.append(pivot_dict)
        _logger.info("End of parsing of file %s", filename)
        return pivot_lines

    def _generate_fr_iban(self, bank_code, guichet_code, acc_number):
        assert bank_code
        assert guichet_code
        assert acc_number
        assert len(bank_code) == 5
        assert len(guichet_code) == 5
        assert len(acc_number) == 11
        raw_acc_number = bank_code + guichet_code + acc_number
        assert len(raw_acc_number) == 21

        rib_letter2number = {
            "A": "1",
            "B": "2",
            "C": "3",
            "D": "4",
            "E": "5",
            "F": "6",
            "G": "7",
            "H": "8",
            "I": "9",
            "J": "1",
            "K": "2",
            "L": "3",
            "M": "4",
            "N": "5",
            "O": "6",
            "P": "7",
            "Q": "8",
            "R": "9",
            "S": "2",
            "T": "3",
            "U": "4",
            "V": "5",
            "W": "6",
            "X": "7",
            "Y": "8",
            "Z": "9",
        }
        raw_acc_number_no_letters = "".join(
            rib_letter2number.get(char.upper(), char) for char in raw_acc_number
        )
        rib_key = (97 - int(raw_acc_number_no_letters) * 100) % 97
        rib_key_str = str(rib_key).zfill(2)
        iban_key_xx = f"FRxx{raw_acc_number}{rib_key_str}"
        iban_key = iban_calc_check_digits(iban_key_xx)
        iban = f"FR{iban_key}{raw_acc_number}{rib_key_str}"
        return iban

    def _cfonb_rejection_reason_codes(self):
        reason_code2label = {
            "01": "Endos erroné",  # LCR only
            "02": "Échéance hors limite",  # LCR only
            "03": "Date incohérente",  # LCR only
            "04": "Réclamation partielle",  # LCR only
            "05": "Réclamation totale",  # LCR only
            "06": "Non retour d'acceptation",  # LCR only
            "11": "Annulation bancaire",  # LCR only
            "12": "Coordonnées bancaires inexploitables",
            "13": "Créance non identifiable",
            "14": "Compte bancaire cloturé",
            "16": "Destinataire non reconnu",
            "18": "Émetteur non reconnu",
            "19": "Créance cédée à une autre banque",  # LCR only
            "20": "Provision insuffisante",
            "31": "Pas d'autorisation",
            "32": "Décision judiciaire (procédure collective)",
            "34": "Opposition sur compte",
            "35": "Titulaire décédé",
            "39": "Ne paie que LCRA ou BOR",  # LCR only
            "52": "Code opération incorrect",
            "54": "Adresse invalide",
            "57": "Format invalide",
            "58": "Sur ordre du client",
            "59": "Raison non communiquée",
            "60": "Code banque incorrect",
            "61": "Heure limite dépassée",
            "62": "Motif réglementaire",
            "63": "Service spécifique",
            "64": "Doublon",
            "65": "Retour suite demande",
            "66": "Donnée mandat incorrecte",  # SDD only
            "70": "Tirage contesté",  # LCR only
            "71": "Reçu à tort / Déjà réglé",
            "72": "Code acceptation erroné",  # LCR only
            "73": "Montant contesté",  # LCR only
            "74": "Date d'échéance contestée",  # LCR only
            "75": "Demande de prorogation",
            "76": "Réclamation tardive",
            "80": "Contestation débiteur",
            "88": "Banque hors échanges",
            "90": "Paiement partiel du tiré",  # LCR only
            "99": "Opération non admise",
        }
        return reason_code2label

    def _cfonb_split_lines(self, attach):
        filename = attach.name
        try:
            data_file = attach.raw.decode("latin1")
        except Exception as e:
            raise UserError(_("Cannot decode file '%s' as latin1.", filename)) from e

        # remove linebreaks
        data_file_without_linebreaks = data_file.replace("\n", "").replace("\r", "")

        # check length of file
        max_len = len(data_file_without_linebreaks)
        lines = []

        if max_len % CFONB_WIDTH:
            raise UserError(
                _("The file '%s' is not divisible in 240 char lines.", filename)
            )
        if max_len == 0:
            raise UserError(_("The file '%s' is empty.", filename))
        for index in range(0, max_len, CFONB_WIDTH):
            lines.append(data_file_without_linebreaks[index : index + CFONB_WIDTH])
        return lines

    def validate(self):
        self.ensure_one()
        i = 0
        payorderattach = set()
        today = fields.Date.context_today(self)
        for line in self.line_ids:
            i += 1
            prefix = _(
                "Rejection line n°%(i)s for partner %(partner_name)s:",
                i=i,
                partner_name=line.partner_name,
            )
            payment = line.payment_id
            if not payment:
                raise UserError(_("%(prefix)s no payment selected.", prefix=prefix))
            if payment.currency_id.compare_amounts(
                line.rejection_amount, payment.amount
            ):
                raise UserError(
                    _(
                        "%(prefix)s the amount of the rejection (%(rej_amount)s) "
                        "is different from the amount of the payment (%(pay_amount)s). "
                        "This scenario is not supported for the moment.",
                        prefix=prefix,
                        rej_amount=format_amount(
                            self.env, line.rejection_amount, line.currency_id
                        ),
                        pay_amount=format_amount(
                            self.env,
                            line.payment_id.amount,
                            line.payment_id.currency_id,
                        ),
                    )
                )
            reason_msg = (
                line.reason
                and " "
                + _("Reason given by our bank: <strong>%s</strong>.") % line.reason
                or ""
            )
            if line.rejection_date:
                msg = _(
                    "Payment <a href=# data-oe-model=account.payment "
                    "data-oe-id=%(pay_id)s>%(pay_name)s</a> "
                    "rejected on %(date)s.%(reason)s",
                    pay_id=payment.id,
                    pay_name=payment.display_name,
                    date=format_date(self.env, line.rejection_date),
                    reason=reason_msg,
                )
            else:
                msg = _(
                    "Payment <a href=# data-oe-model=account.payment "
                    "data-oe-id=%(pay_id)s>%(pay_name)s</a> rejected.%(reason)s",
                    pay_id=payment.id,
                    pay_name=payment.display_name,
                    reason=reason_msg,
                )
            for invoice in payment.reconciled_invoice_ids:
                invoice.message_post(body=msg)
            payment.write(
                {
                    "rejection_date": line.rejection_date or today,
                    "rejection_reason": line.reason,
                }
            )
            payment.message_post(body=_("Payment rejected."))
            if payment.payment_order_id:
                msg_detail = _(
                    "Payment <a href=# data-oe-model=account.payment "
                    "data-oe-id=%(pay_id)s>%(pay_name)s</a> of %(partner)s "
                    "amount %(amount)s rejected.%(reason)s",
                    pay_id=payment.id,
                    pay_name=payment.display_name,
                    partner=payment.partner_id.display_name,
                    amount=format_amount(self.env, payment.amount, payment.currency_id),
                    reason=reason_msg,
                )
                payment.payment_order_id.message_post(body=msg_detail)
                if (
                    line.attachment_id
                    and (payment.payment_order_id.id, line.attachment_id.id)
                    not in payorderattach
                ):
                    self.env["ir.attachment"].create(
                        {
                            "name": line.attachment_id.name,
                            "raw": line.attachment_id.raw,
                            "res_model": "account.payment.order",
                            "res_id": payment.payment_order_id.id,
                        }
                    )
                    payorderattach.add(
                        (payment.payment_order_id.id, line.attachment_id.id)
                    )
            lines_to_unrec = payment.line_ids.filtered(
                lambda x: x.account_id.account_type
                in ("asset_receivable", "liability_payable")
                and x.account_id.reconcile
            )
            lines_to_unrec.remove_move_reconcile()


class AccountPaymentOrderRejectionLine(models.TransientModel):
    _name = "account.payment.order.rejection.line"
    _description = "Payment Order Rejection Lines"
    _check_company_auto = True

    wizard_id = fields.Many2one(
        "account.payment.order.rejection.import", ondelete="cascade"
    )
    company_id = fields.Many2one(related="wizard_id.company_id", store=True)
    company_name = fields.Char(readonly=True)
    company_partner_bank_id = fields.Many2one(
        "res.partner.bank", string="Company Bank Account", readonly=True
    )
    journal_id = fields.Many2one(
        "account.journal", string="Bank Journal", check_company=True, readonly=True
    )

    rejection_date = fields.Date(readonly=True)
    payment_date = fields.Date(readonly=True)
    partner_bank_id = fields.Many2one(
        "res.partner.bank", readonly=True, string="Bank Account"
    )
    partner_id = fields.Many2one("res.partner", related="partner_bank_id.partner_id")
    partner_name = fields.Char(readonly=True)
    label = fields.Char()
    reason = fields.Char(readonly=True)
    rejection_amount = fields.Monetary(currency_field="currency_id", readonly=True)
    currency_id = fields.Many2one("res.currency", required=True, readonly=True)
    payment_id = fields.Many2one(
        "account.payment",
        check_company=True,
        compute="_compute_payment_id",
        readonly=False,
        store=True,
        precompute=True,
        domain="[('company_id', '=', company_id), ('payment_type', '=', payment_type), "
        "('state', '=', 'posted'), ('currency_id', '=', currency_id), "
        "('journal_id', '=', journal_id), ('payment_order_id', '!=', False), "
        "('partner_bank_id', '=', partner_bank_id)]",
    )
    payment_match = fields.Char(
        compute="_compute_payment_id", store=True, precompute=True
    )
    payment_order_id = fields.Many2one(
        related="payment_id.payment_order_id", string="Payment/Debit Order"
    )
    payment_type = fields.Selection(
        [("inbound", "Inbound"), ("outbound", "Outbound")], readonly=True
    )
    payment_method_code = fields.Char(readonly=True)
    attachment_id = fields.Many2one("ir.attachment", readonly=True)

    @api.depends(
        "journal_id",
        "partner_bank_id",
        "label",
        "currency_id",
        "payment_type",
        "payment_method_code",
    )
    def _compute_payment_id(self):
        # for v18
        # inbound_seq = self.env.ref('account_payment_order.account_payment_order_inbound_seq')
        outbound_seq = self.env.ref("account_payment_order.account_payment_order_seq")
        for line in self:
            payment_id = False
            payment_match = False
            payment_memo_extracted = False

            if (
                line.journal_id
                and line.company_id
                and line.currency_id
                and line.payment_type
                and line.partner_bank_id
            ):
                company_id = line.company_id.id
                payment_type = line.payment_type
                domain = [
                    ("company_id", "=", company_id),
                    ("journal_id", "=", line.journal_id.id),
                    ("payment_type", "=", payment_type),
                    ("currency_id", "=", line.currency_id.id),
                    ("state", "=", "posted"),
                    ("is_reconciled", "=", True),
                    ("partner_bank_id", "=", line.partner_bank_id.id),
                    ("payment_order_id", "!=", False),
                ]
                payment_match = _("Approximate match")
                if line.label and line.payment_method_code:
                    pay_mode_domain = expression.AND(
                        [
                            [("company_id", "=", company_id)],
                            [("payment_type", "=", payment_type)],
                            [("payment_order_ok", "=", True)],
                            [("payment_method_code", "=", line.payment_method_code)],
                            expression.OR(
                                [
                                    [
                                        ("bank_account_link", "=", "fixed"),
                                        ("fixed_journal_id", "=", line.journal_id.id),
                                    ],
                                    [
                                        ("bank_account_link", "=", "variable"),
                                        (
                                            "variable_journal_ids",
                                            "in",
                                            line.journal_id.id,
                                        ),
                                    ],
                                ]
                            ),
                        ]
                    )
                    payment_mode = self.env["account.payment.mode"].search(
                        pay_mode_domain, limit=1
                    )
                    if payment_mode and payment_mode.specific_sequence_id:
                        seq = payment_mode.specific_sequence_id
                    # for v18
                    # elif payment_type == 'inbound':
                    #    seq = inbound_seq
                    else:
                        seq = outbound_seq
                    # TODO  add support for year/month/... in prefix
                    if seq.prefix:
                        # update for v18
                        prefix = re.escape(seq.prefix)
                        padding = seq.padding
                        pattern = f"{prefix}\d{{{padding},{padding + 1}}}/\d{{1,3}}"
                        res_find = re.findall(pattern, line.label)
                        if res_find:
                            if len(res_find) > 1:
                                _logger.info(
                                    "Several matches on payment sequence found: %s. "
                                    "Using the first one",
                                    res_find,
                                )
                            payment_memo_extracted = res_find[0]
                            payment_match = (
                                _("Exact match on %s") % payment_memo_extracted
                            )
                            domain.append(("ref", "=", payment_memo_extracted))

                    else:
                        _logger.warning(
                            "Sequence ID %d doesn't have a prefix, which breaks the "
                            "detection of the payment from the label",
                            seq.id,
                        )
                payments = self.env["account.payment"].search(domain, order="date desc")
                for payment in payments:
                    if not payment.currency_id.compare_amounts(
                        payment.amount, line.rejection_amount
                    ):
                        payment_id = payment.id
                        break
            if not payment_id:
                if payment_memo_extracted:
                    payment_match = _("No match on %s") % payment_memo_extracted
                else:
                    payment_match = _("No match")
            line.payment_id = payment_id
            line.payment_match = payment_match
