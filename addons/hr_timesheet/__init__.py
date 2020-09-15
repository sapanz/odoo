# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report
from . import wizard

from odoo import api, fields, SUPERUSER_ID, _


def create_internal_project(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    admin = env.ref('base.user_admin', raise_if_not_found=False)
    if not admin:
        return
    project_ids = env['res.company'].search([])._create_internal_project_task()
    env['account.analytic.line'].create([{
        'name': _("Analysis"),
        'user_id': admin.id,
        'date': fields.datetime.today(),
        'unit_amount': 0,
        'project_id': task.project_id.id,
        'task_id': task.id,
    } for task in project_ids.task_ids.filtered(lambda t: t.company_id in admin.employee_ids.company_id)])
