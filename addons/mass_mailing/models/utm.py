# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class UtmCampaign(models.Model):
    _inherit = 'utm.campaign'

    mailing_mail_ids = fields.One2many(
        'mailing.mailing', 'campaign_id',
        domain=[('mailing_type', '=', 'mail')],
        string='Mass Mailings')
    mailing_mail_count = fields.Integer('Number of Mass Mailing', compute="_compute_mailing_mail_count")
    # stat fields
    received_ratio = fields.Integer(compute="_compute_statistics", string='Received Ratio')
    opened_ratio = fields.Integer(compute="_compute_statistics", string='Opened Ratio')
    replied_ratio = fields.Integer(compute="_compute_statistics", string='Replied Ratio')
    bounced_ratio = fields.Integer(compute="_compute_statistics", string='Bounced Ratio')

    @api.depends('mailing_mail_ids')
    def _compute_mailing_mail_count(self):
        for campaign in self:
            campaign.mailing_mail_count = len(campaign.mailing_mail_ids)

    def _compute_statistics(self):
        """ Compute statistics of the mass mailing campaign """
        self.env.cr.execute("""
            SELECT
                c.id as campaign_id,
                COUNT(s.id) AS expected,
                COUNT(CASE WHEN s.sent is not null THEN 1 ELSE null END) AS sent,
                COUNT(CASE WHEN s.scheduled is not null AND s.sent is null AND s.exception is null AND s.canceled is not null THEN 1 ELSE null END) AS canceled,
                COUNT(CASE WHEN s.id is not null AND s.bounced is null THEN 1 ELSE null END) AS delivered,
                COUNT(CASE WHEN s.opened is not null THEN 1 ELSE null END) AS opened,
                COUNT(CASE WHEN s.replied is not null THEN 1 ELSE null END) AS replied,
                COUNT(CASE WHEN s.bounced is not null THEN 1 ELSE null END) AS bounced
            FROM
                mail_notification s
            RIGHT JOIN
                utm_campaign c
                ON (c.id = s.campaign_id)
            WHERE
                c.id IN %s
            GROUP BY
                c.id
        """, (tuple(self.ids), ))

        all_stats = self.env.cr.dictfetchall()
        stats_per_campaign = {
            stats['campaign_id']: stats
            for stats in all_stats
        }

        for campaign in self:
            stats = stats_per_campaign.get(campaign.id)
            if not stats:
                vals = {
                    'received_ratio': 0,
                    'opened_ratio': 0,
                    'replied_ratio': 0,
                    'bounced_ratio': 0
                }
            else:
                total = (stats['expected'] - stats['canceled']) or 1
                delivered = stats['sent'] - stats['bounced']
                vals = {
                    'received_ratio': 100.0 * delivered / total,
                    'opened_ratio': 100.0 * stats['opened'] / total,
                    'replied_ratio': 100.0 * stats['replied'] / total,
                    'bounced_ratio': 100.0 * stats['bounced'] / total
                }

            campaign.update(vals)

    def _get_mailing_recipients(self, model=None):
        """Return the recipients of a mailing campaign. This is based on the statistics
        build for each mailing. """
        res = dict.fromkeys(self.ids, {})
        for campaign in self:
            domain = [('campaign_id', '=', campaign.id)]
            if model:
                domain += [('model', '=', model)]
            res[campaign.id] = set(self.env['mail.notification'].search(domain).mapped('res_id'))
        return res
