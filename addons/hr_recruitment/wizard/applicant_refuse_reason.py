# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ApplicantGetRefuseReason(models.TransientModel):
    _name = 'applicant.get.refuse.reason'
    _inherits = {'mail.compose.message':'composer_id'}
    _description = 'Get Refuse Reason'

    refuse_reason_id = fields.Many2one('hr.applicant.refuse.reason', 'Refuse Reason')
    applicant_ids = fields.Many2many('hr.applicant')
    composer_id = fields.Many2one('mail.compose.message', string='Composer', required=True, ondelete='cascade')
    template_id = fields.Many2one(
        'mail.template', "Email Templates", active=True, index=True, domain="[('model', '=', 'hr.applicant')]")

    @api.onchange('refuse_reason_id')
    def onchange_refuse_reason_id(self):
        ''' Get the default incoterm for invoice. '''
        self.template_id = self.composer_id.template_id = self.refuse_reason_id.template_id
        self.composer_id.onchange_template_id_wrapper()
        active_id = self.env['hr.applicant'].browse(self._context.get('active_id'))
        if active_id.partner_id:
            self.partner_ids = active_id.partner_id
        else:
            self.partner_ids = active_id.user_id.partner_id
        return

    def action_refuse_reason_apply(self):
        return self.applicant_ids.write({'refuse_reason_id': self.refuse_reason_id.id, 'active': False})

    def action_send_mail(self):
        self.ensure_one()
        self.composer_id.with_context(mail_notify_author=self.env.user.partner_id in self.composer_id.partner_ids).send_mail()
        return self.applicant_ids.write({
            'refuse_reason_id': self.refuse_reason_id.id
        })
