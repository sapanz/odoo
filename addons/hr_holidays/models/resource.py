# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


class CalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"
    _rec_name = "public_name"

    holiday_id = fields.Many2one("hr.leave", string='Leave Request')
    # Override name field and apply a group to restrict the reason of leave
    name = fields.Char(groups='hr_holidays.group_hr_holidays_user')
    public_name = fields.Char('Leave Reason', compute='_compute_public_name', inverse='_inverse_public_name', search='_search_public_name')

    @api.depends_context('uid')
    def _compute_public_name(self):
        self.check_access_rights('read')
        self.check_access_rule('read')

        is_officer = self.user_has_groups('hr_holidays.group_hr_holidays_user')

        for leave in self:
            holiday = leave.sudo().holiday_id
            if not holiday or is_officer or leave.resource_id.user_id == self.env.user or holiday.manager_id == self.env.user:
                leave.public_name = leave.sudo().name
            else:
                leave.public_name = '*****'

    def _inverse_public_name(self):
        is_officer = self.user_has_groups('hr_holidays.group_hr_holidays_user')

        for leave in self:
            holiday = leave.sudo().holiday_id
            if not holiday or is_officer or leave.resource_id.user_id == self.env.user or holiday.manager_id == self.env.user:
                leave.sudo().name = leave.public_name

    def _search_public_name(self, operator, value):
        is_officer = self.user_has_groups('hr_holidays.group_hr_holidays_user')
        domain = [('name', operator, value)]

        if not is_officer:
            domain = expression.AND([domain, [('resource_id.user_id', '=', self.env.uid)]])

        leaves = self.search(domain)
        return [('id', 'in', leaves.ids)]
