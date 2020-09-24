from odoo import models, fields, _

from datetime import datetime
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    def document_layout_save(self):
        res = super(BaseDocumentLayout, self).document_layout_save()

        for wizard in self:
            wizard.company_id.action_save_onboarding_invoice_layout()

            # warn the user (only if at least one invoice is posted)
            if self.env['account.move'].search([('state', '=', 'posted'), ('move_type', '=', 'out_invoice'), ('company_id', '=', wizard.company_id.id)], limit=1):
                mail_template = self.env.ref('account.document_layout_changed_template')
                ctx = {
                    'user_name': self.env.user.name,
                    'company_name': wizard.company_id.name,
                    'timestamp': fields.Datetime.context_timestamp(self, datetime.now()).strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }
                mail_body = mail_template._render(ctx, engine='ir.qweb', minimal_qcontext=True)
                mail = self.env['mail.mail'].sudo().create({
                    'subject': _('Warning: document template of %s - %s has been modified', self._cr.dbname, wizard.company_id.name),
                    'email_to': self.env.user.email,
                    'auto_delete': True,
                    'body_html': mail_body,
                })
                mail.send()
        return res
