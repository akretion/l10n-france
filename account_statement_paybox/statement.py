# -*- coding: utf-8 -*-
###############################################################################
#
#   account_statement_paybox for OpenERP
#   Copyright (C) 2013-TODAY Akretion <http://www.akretion.com>.
#   @author Florian DA COSTA <florian.dacosta@akretion.com>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of the
#   License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################


from openerp.osv import orm, fields
from tools.translate import _

class AccountStatementProfil(orm.Model):
    _inherit = "account.statement.profile"

    def _get_import_type_selection(self, cr, uid, context=None):
        """
        Has to be inherited to add parser
        """
        res = super(AccountStatementProfil, self)._get_import_type_selection(cr, uid, context=context)
        res.extend([('paybox_csvparser', 'Parser for Paybox import statement'),
                    ])
        return res


class AccountBankSatementLine(orm.Model):

    _inherit = "account.bank.statement.line"

    _columns = {
        'customer_email': fields.char('Customer Email', size=240),
    }



