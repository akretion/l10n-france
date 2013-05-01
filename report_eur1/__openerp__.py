# -*- encoding: utf-8 -*-
#################################################################################
#
#    report_eur1 module for OpenERP
#    Copyright (C) 2012-2013 Akretion
#    @author: Alexis de Lattre <alexis.delattre@akretion.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#################################################################################


{
    'name': 'EUR-1 report',
    'version': '1.0',
    'category': 'Localisation/Report Intrastat',
    'license': 'AGPL-3',
    'summary': 'Adds EUR-1 report on stock picking',
    'description': """This module adds an EUR-1 report on stock picking, that can be directly printed on the official EUR-1 form.

Please contact Alexis de Lattre from Akretion <alexis.delattre@akretion.com> for any help or question about this module.
    """,
    'author': 'Akretion',
    'website': 'http://www.akretion.com/',
    'depends': ['l10n_fr_intrastat_product', 'report_aeroo', 'sale'], # we display some fields that are declared in "sale"
    'init_xml': [],
    'update_xml': ['report.xml'],
    'demo_xml': [],
    'installable': True,
    'active': False,
}

