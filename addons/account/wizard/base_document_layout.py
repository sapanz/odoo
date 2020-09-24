from odoo import models, fields

from datetime import datetime
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    def document_layout_save(self):
        res = super(BaseDocumentLayout, self).document_layout_save()

        for wizard in self:
            wizard.company_id.action_save_onboarding_invoice_layout()

            # warn the user (only if at least one invoice is posted)
            if self.env['account.move'].search([('state', '=', 'posted'), ('move_type', '=', 'out_invoice'), ('company_id', '=', company.id)], limit=1):
                mail_template = self.env.ref('account.document_layout_changed_template')
                ctx = {
                    'company_id': self.company_id,
                    'timestamp': fields.Datetime.context_timestamp(self, datetime.now()).strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'db_name': self._cr.dbname,
                }
                mail_template.with_context(ctx).send_mail(self.env.user.id, force_send=True)
        return res
