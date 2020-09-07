# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model_create_multi
    def create(self, values):
        company = super(ResCompany, self).create(values)
        # use sudo as the user could have the right to create a company
        # but not to create a project. On the other hand, when the company
        # is created, it is not in the allowed_company_ids on the env
        company.sudo()._create_internal_project_task()
        return company

    def _create_internal_project_task(self):
        results = []
        for company in self:
            company = company.with_company(company)
            internal_project = company.env['project.project'].sudo().create({
                'name': _('Internal'),
                'allow_timesheets': True,
                'company_id': company.id,
            })

            company.env['project.task'].sudo().create([{
                'name': _('Training'),
                'project_id': internal_project.id,
                'company_id': company.id,
            }, {
                'name': _('Meeting'),
                'project_id': internal_project.id,
                'company_id': company.id,
            }])
            results.append(internal_project)
        return results
