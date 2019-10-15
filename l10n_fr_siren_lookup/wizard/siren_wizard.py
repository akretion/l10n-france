# -*- coding: utf-8 -*-

# © 2018 Le Filament (<http://www.le-filament.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import requests
from openerp import api, fields, models, _
from unidecode import unidecode

URL = "https://data.opendatasoft.com/api/records/1.0/"\
    "search/?dataset=sirene_v3%40public&q={request}&rows=100"


class SirenWizard(models.TransientModel):
    _name = 'siren.wizard'
    _description = 'Get values from companies'

    state = fields.Selection([
        ('select', 'Select'),
        ('confirm', 'Confirm'),
        ], default='select', readonly=True, string='State')
    name = fields.Char(string='Company', required=True)
    line_ids = fields.One2many('siren.wizard.line', 'wizard_id',
                               string="Results", readonly=True)
    partner_id = fields.Many2one(
        'res.partner', string='Partner to Update',
        required=True, readonly=True)
    selected_line_id = fields.Many2one(
        'siren.wizard.line', string='Selected Line', readonly=True)
    diff = fields.Text(readonly=True)

    @api.model
    def _prepare_partner_from_data(self, data):
        return {
            'name': data.get('denominationunitelegale'),
            'street': data.get('adresseetablissement'),
            'zip': data.get('codepostaletablissement'),
            'city': data.get('libellecommuneetablissement'),
            'siren': data.get('siren'),
            'nic': data.get('nic'),
            'category': data.get('categorieentreprise'),
            'creation_date': data.get('datecreationunitelegale'),
            'close_date': data.get('datefermetureunitelegale'),
            'ape': data.get('activiteprincipaleunitelegale'),
            'ape_label': data.get('divisionunitelegale'),
            'legal_type': data.get('naturejuridiqueunitelegale'),
            'staff': data.get('trancheeffectifsunitelegale'),
        }

    @api.multi
    def get_lines(self):
        # Get request
        r = requests.get(URL.format(request=unidecode(self.name)))
        # Serialization request to JSON
        companies = r.json()
        # Fill new company lines
        companies_vals = []
        for company in companies['records']:
            res = self._prepare_partner_from_data(company['fields'])
            companies_vals.append((0, 0, res))
        self.line_ids.unlink()
        self.line_ids = companies_vals
        action = self.env.ref(
            'l10n_fr_siren_lookup.siren_wizard_action').read()[0]
        action['res_id'] = self.id
        return action

    @api.multi
    def update_partner(self):
        vals = self.selected_line_id.compare_values()[0]
        if vals:
            self.partner_id.write(vals)


class SirenWizardLine(models.TransientModel):
    _name = 'siren.wizard.line'
    _description = 'Company Selection'

    wizard_id = fields.Many2one('siren.wizard', string='Wizard')
    name = fields.Char(string='Name')
    street = fields.Char(string='Street')
    zip = fields.Char(string='Zip')
    city = fields.Char(string='City')
    legal_type = fields.Char("Legal Type")
    siren = fields.Char("SIREN")
    nic = fields.Char("NIC")
    ape = fields.Char("APE Code")
    ape_label = fields.Char("APE Label")
    creation_date = fields.Date("Creation date")
    close_date = fields.Date("Close date")
    staff = fields.Char("# Staff")
    category = fields.Char("Category")

    @api.multi
    def compare_values(self):
        partner = self.wizard_id.partner_id
        diff = {}
        diff_txt = []
        fields_list = ['name', 'street', 'zip', 'city', 'siren', 'nic']
        fget = self.env['res.partner'].fields_get(fields_list)
        for pfield in fields_list:
            if partner[pfield] != self[pfield]:
                diff[pfield] = self[pfield]
                diff_txt.append(
                    _('%s : %s -> %s') % (
                        fget[pfield].get('string', pfield),
                        partner[pfield],
                        self[pfield]))
        diff_txt = '\n'.join(diff_txt)
        return diff, diff_txt

    @api.multi
    def select_line(self):
        self.wizard_id.write({
            'selected_line_id': self.id,
            'diff': self.compare_values()[1],
            'state': 'confirm',
            })
        action = self.env.ref(
            'l10n_fr_siren_lookup.siren_wizard_action').read()[0]
        action['res_id'] = self.wizard_id.id
        return action
