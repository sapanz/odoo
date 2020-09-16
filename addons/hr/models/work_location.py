# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import fields, models


class WorkLocation(models.Model):

    _name = "work.location"
    _description = "Work Location"
    _order = 'name'

    name = fields.Char(string="Work Location")
    company_id = fields.Many2one('res.company', string="Company")
    active = fields.Boolean(default=True)