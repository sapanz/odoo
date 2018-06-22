# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'


    @api.multi
    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        res = super(AccountChartTemplate, self)._prepare_all_journals(
            acc_template_ref, company, journals_dict=journals_dict)
        if not self == self.env.ref('l10n_in.indian_chart_template_standard'):
            return res
        for journal in res:
            if journal['code'] == 'INV':
                journal['name'] = _('Tax Invoices')

        res += [{'type': 'sale', 'name': _('Retail Invoices'), 'code': 'RETINV', 'company_id': company.id, 'show_on_dashboard': True,},
                {'type': 'sale', 'name': _('Export Invoices'), 'code': 'EXPINV', 'company_id': company.id, 'show_on_dashboard': True, 'l10n_in_import_export': True},]
        return res


class AccountTaxTemplate(models.Model):
    _inherit = 'account.tax.template'

    #use in GSTR export report as Rate of tax.
    l10n_in_description = fields.Char(string='Label GST Report')

    def _get_tax_vals(self, company, tax_template_to_tax):
        val = super(AccountTaxTemplate, self)._get_tax_vals(company, tax_template_to_tax)
        if self.tax_group_id:
            val['l10n_in_description'] = self.l10n_in_description
        return val
