# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MailingList(models.Model):
    _inherit = 'mailing.list'

    contact_nbr_sms = fields.Integer(compute="_compute_mailing_list_statistics", string="SMS Contacts")

    def action_view_mailings(self):
        if self.env.context.get('mailing_sms'):
            action = self.env["ir.actions.actions"]._for_xml_id('mass_mailing_sms.mailing_mailing_action_sms')
            action['domain'] = [('id', 'in', self.mailing_ids.ids)]
            action['context'] = {
                'default_mailing_type': 'sms',
                'default_contact_list_ids': self.ids,
                'mailing_sms': True
            }
            return action
        else:
            return super(MailingList, self).action_view_mailings()

    def _get_contact_nbr_select_fields(self):
        """ See super method docstring for more info.
        Adds:
        - contact_nbr_sms:        all valid sms"""

        values = super(MailingList, self)._get_contact_nbr_select_fields()
        values['contact_nbr_sms'] = '''
            SUM(CASE WHEN
                (c.phone_sanitized IS NOT NULL
                AND COALESCE(r.opt_out,FALSE) = FALSE
                AND bl_sms.id IS NULL)
                THEN 1 ELSE 0 END) AS contact_nbr_sms'''
        return values

    def _get_blacklist_join(self):
        return super(MailingList, self)._get_blacklist_join() + '''
            LEFT JOIN phone_blacklist bl_sms ON c.phone_sanitized = bl_sms.number and bl_sms.active
        '''

    def _get_blacklisted_condition(self):
        return '(bl.id IS NOT NULL OR bl_sms.id IS NOT NULL)'

    def action_view_contacts_sms(self):
        action = self.action_view_contacts()
        action['context'] = dict(action.get('context', {}), search_default_filter_valid_sms_recipient=1)
        return action
