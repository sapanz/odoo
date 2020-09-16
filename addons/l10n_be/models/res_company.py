from odoo import api, fields, models, tools, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    company_registry = fields.Char(compute='_compute_company_registry', store='True', readonly=False)

    # If a belgian company has a VAT number then it's company registry is it's VAT Number (without country code).
    @api.depends('vat')
    def _compute_company_registry(self):
        for company in self:
            # set value only if no previous value and if VAT number is valid
            if company.country_id.code == 'BE' and company.vat and not company.company_registry:
                ResPartner = self.env['res.partner']
                vat_country, vat_number = ResPartner._split_vat(company.vat)
                if ResPartner.simple_vat_check('be', vat_number):
                    company.company_registry = vat_number
