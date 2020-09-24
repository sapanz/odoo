# -*- coding: utf-8 -*-

from odoo import models, fields
from datetime import datetime
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    def write(self, vals):
        for acc in self:
            if 'acc_number' in vals:
                mail_template = self.env.ref('mail.partner_bank_account_changed_template')
                ctx = {
                    'user': self.env.user,
                    'timestamp': fields.Datetime.context_timestamp(self, datetime.now()).strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }
                mail_template.with_context(ctx).send_mail(acc.partner_id, force_send=True)

                acc.partner_id.message_post(body=_('Bank account number %s --> %s', acc.acc_number, vals['acc_number']))
        return super().write(vals)
