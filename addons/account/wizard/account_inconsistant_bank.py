# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountInconsistantBank(models.TransientModel):
    _name = 'account.inconsistant.bank.wizard'
    _description = ' Wizard for inconsistant bank account on partner when importing file'

    inconsistant_banks_line_ids = fields.One2many('account.inconsistant.bank.wizard.line', 'inconsistant_bank_id')
    invoice_redirect_ids = fields.Many2many('account.move')
    nb_create_bank_account = fields.Integer(compute='_compute_nb_create_bank_account', help='Technical field to hide button in view')

    @api.depends('inconsistant_banks_line_ids.should_create')
    def _compute_nb_create_bank_account(self):
        for rec in self:
            rec.nb_create_bank_account = len(rec.inconsistant_banks_line_ids.filtered(lambda lines: lines.should_create))

    def action_done(self):
        for to_correct in self.inconsistant_banks_line_ids.filtered(lambda l: l.should_create):
            to_correct.partner_id.write({
                'bank_ids': [(0, 0, {'acc_number': to_correct.acc_number})]
            })
        return self.invoice_redirect_ids.journal_id._redirect_to_generated_documents(self.invoice_redirect_ids)

    def action_discard(self):
        return self.invoice_redirect_ids.journal_id._redirect_to_generated_documents(self.invoice_redirect_ids)


class AccountInconsistantBankLine(models.TransientModel):
    _name = 'account.inconsistant.bank.wizard.line'
    _description = 'Account Inconsistant Bank Line'

    inconsistant_bank_id = fields.Many2one('account.inconsistant.bank.wizard')
    partner_id = fields.Many2one('res.partner')
    acc_number = fields.Char('Bank Account Number')
    should_create = fields.Boolean('Keep')
