# -*- encoding: utf-8 -*-
##############################################################################
#
#    Report intrastat service module for OpenERP
#    Copyright (C) 2014 Akretion (http://www.akretion.com)
#    @author Alexis de Lattre <alexis.delattre@akretion.com>
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
##############################################################################

from openupgradelib import openupgrade


table_renames = [
    ('l10n_fr_report_intrastat_service_line',
     'l10n_fr_intrastat_service_declaration_line'),
    ('l10n_fr_report_intrastat_service',
     'l10n_fr_intrastat_service_declaration'),
    ]

model_renames = [
    ('l10n.fr.report.intrastat.service.line',
     'l10n.fr.intrastat.service.declaration.line'),
    ('l10n.fr.report.intrastat.service',
     'l10n.fr.intrastat.service.declaration'),
    ]


@openupgrade.migrate(use_env=True)
def migrate(env, version):
    openupgrade.rename_models(env.cr, model_renames)
    openupgrade.rename_tables(env.cr, table_renames)
