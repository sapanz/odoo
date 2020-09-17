# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools.misc import get_lang


class ApplicantGetRefuseReason(models.TransientModel):
    _name = 'applicant.get.refuse.reason'
    _inherits = {'mail.compose.message': 'composer_id'}
    _description = 'Get Refuse Reason'

    @api.model
    def default_get(self, fields):
        res = super(ApplicantGetRefuseReason, self).default_get(fields)
        res_ids = self._context.get('default_applicant_ids')

        composer = self.env['mail.compose.message'].create({
            'composition_mode': 'comment' if len(res_ids) == 1 else 'mass_mail',
        })
        res.update({
            'applicant_ids': res_ids,
            'composer_id': composer.id,
        })
        return res

    refuse_reason_id = fields.Many2one('hr.applicant.refuse.reason', 'Refuse Reason')
    applicant_ids = fields.Many2many('hr.applicant')
    applicant_without_email = fields.Text(compute="_compute_applicant_without_email", string='applicant(s) not having email')
    composer_id = fields.Many2one('mail.compose.message', string='Composer', required=True, ondelete='cascade')
    template_id = fields.Many2one('mail.template', "Email Templates", index=True, domain="[('model', '=', 'hr.applicant')]")

    def _compute_applicant_without_email(self):
        for wizard in self:
            if len(wizard.applicant_ids) > 1:
                applicants = self.env['hr.applicant'].search([
                    ('id', 'in', self.env.context['default_applicant_ids']),
                    ('email_from', '=', False)
                ])
                if applicants:
                    wizard.applicant_without_email = "%s\n%s" % (
                        _("The following invoice(s) will not be sent by email, because the customers don't have email address."),
                        "\n".join([i.name for i in applicants])
                    )
                else:
                    wizard.applicant_without_email = False
            else:
                wizard.applicant_without_email = False

    @api.onchange('applicant_ids')
    def _compute_composition_mode(self):
        for wizard in self:
            wizard.composer_id.composition_mode = 'comment' if len(wizard.applicant_ids) == 1 else 'mass_mail'

    @api.onchange('template_id')
    def onchange_template_id(self):
        for wizard in self:
            if wizard.composer_id:
                wizard.composer_id.template_id = wizard.template_id.id
                wizard._compute_composition_mode()
                wizard.composer_id.onchange_template_id_wrapper()

    @api.onchange('refuse_reason_id')
    def onchange_refuse_reason_id(self):
        if self.refuse_reason_id:
            res_ids = self._context.get('default_applicant_ids')
            if not self.composer_id:
                self.composer_id = self.env['mail.compose.message'].create({
                    'composition_mode': 'comment' if len(res_ids) == 1 else 'mass_mail',
                    'template_id': self.refuse_reason_id.template_id.id
                })
            self.template_id = self.composer_id.template_id = self.refuse_reason_id.template_id
            self.composer_id.onchange_template_id_wrapper()
            self.partner_ids = self.applicant_ids.partner_id


    def action_refuse_reason_apply(self):
        return self.applicant_ids.write({'refuse_reason_id': self.refuse_reason_id.id, 'active': False})

    def _send_email(self):
        self.composer_id.send_mail()
        self.applicant_ids.write({'refuse_reason_id': self.refuse_reason_id.id})

    def action_send_mail(self):
        self.ensure_one()
        if self.composition_mode == 'mass_mail' and self.template_id:
            active_records = self.applicant_ids
            langs = active_records.mapped('partner_id.lang')
            default_lang = get_lang(self.env)
            for lang in (set(langs) or [default_lang]):
                active_ids_lang = active_records.filtered(lambda r: r.partner_id.lang == lang).ids
                self_lang = self.with_context(active_ids=active_ids_lang, lang=lang)
                self_lang.onchange_template_id()
                self_lang._send_email()
        else:
            self._send_email()
        return {'type': 'ir.actions.act_window_close'}
