# -*- coding: utf-8 -*-

from odoo import models, fields, _
from datetime import datetime
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    def write(self, vals):
        for acc in self:
            if 'acc_number' in vals:
                mail_template = self.env.ref('mail.partner_bank_account_changed_template')
                ctx = {
                    'user_name': self.env.user.name,
                    'partner': acc.partner_id,
                    'timestamp': fields.Datetime.context_timestamp(self, datetime.now()).strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }
                mail_body = mail_template._render(ctx, engine='ir.qweb', minimal_qcontext=True)
                mail = self.env['mail.mail'].sudo().create({
                    'subject': _('Warning: bank account of %s modified', acc.partner_id.name),
                    'email_to': self.env.user.email,
                    'auto_delete': True,
                    'body_html': mail_body,
                })
                mail.send()

                acc.partner_id.message_post(body=_('<ul><li>Bank account number: %s <div class="fa fa-long-arrow-right"/> %s</ul></li>', acc.acc_number, vals['acc_number']))
        return super().write(vals)
