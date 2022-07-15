# Copyright 2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    if openupgrade.table_exists(env.cr, "account_invoice"):
        openupgrade.logged_query(
            env.cr,
            """
            UPDATE account_move am
            SET chorus_flow_id=ai.chorus_flow_id,
            chorus_identifier=ai.chorus_identifier,
            chorus_status=ai.chorus_status,
            chorus_status_date=ai.chorus_status_date
            FROM account_invoice ai
            WHERE am.old_invoice_id = ai.id""",
        )
