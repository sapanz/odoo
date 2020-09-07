# coding: utf-8

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PaypalPaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[
        ('paypal', 'Paypal')
    ], ondelete={'paypal': 'set default'})
    paypal_email_account = fields.Char('Email', required_if_provider='paypal', groups='base.group_user')
    paypal_seller_account = fields.Char(
        'Merchant Account ID', groups='base.group_user',
        help='The Merchant ID is used to ensure communications coming from Paypal are valid and secured.')
    paypal_use_ipn = fields.Boolean('Use IPN', default=True, help='Paypal Instant Payment Notification',
                                    groups='base.group_user')
    paypal_pdt_token = fields.Char(string='PDT Identity Token',
                                   help='Payment Data Transfer allows you to receive notification of successful payments as they are made.',
                                   groups='base.group_user')

    def _compute_fees(self, amount, currency_id, country_id):
        """
        override method from payment

        Note: self.ensure_one();
        """
        self.ensure_one()

        if self.provider != 'paypal':
            return super()._compute_fees(self, amount, currency_id, country_id)

        if not self.fees_active:
            return 0.0
        country = self.env['res.country'].browse(country_id)
        if country and self.company_id.country_id.id == country.id:
            percentage = self.fees_dom_var
            fixed = self.fees_dom_fixed
        else:
            percentage = self.fees_int_var
            fixed = self.fees_int_fixed
        fees = (percentage / 100.0 * amount) + fixed / (1 - percentage / 100.0)
        return fees

    def _get_redirect_action_url(self):
        """
        provide action for Paypal form depending on provider state (enabled, test or disabled)

        Note: self.ensure_one()
        """
        self.ensure_one()

        if self.state == 'enabled':
            return 'https://www.paypal.com/cgi-bin/webscr'
        else:
            return 'https://www.sandbox.paypal.com/cgi-bin/webscr'
