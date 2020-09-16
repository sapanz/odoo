# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from hashlib import md5
from werkzeug import urls

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare
from odoo.addons.payment_alipay.controllers.main import AlipayController
from odoo.addons.payment.models.payment_acquirer import ValidationError

_logger = logging.getLogger(__name__)


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[
        ('alipay', 'Alipay')
    ], ondelete={'alipay': 'set default'})
    alipay_payment_method = fields.Selection([
        ('express_checkout', 'Express Checkout (only for Chinese Merchant)'),
        ('standard_checkout', 'Cross-border'),
    ], string='Account', default='express_checkout',
        help="  * Cross-border: For the Overseas seller \n  * Express Checkout: For the Chinese Seller")
    alipay_merchant_partner_id = fields.Char(
        string='Merchant Partner ID', required_if_provider='alipay', groups='base.group_user',
        help='The Merchant Partner ID is used to ensure communications coming from Alipay are valid and secured.')
    alipay_md5_signature_key = fields.Char(
        string='MD5 Signature Key', required_if_provider='alipay', groups='base.group_user',
        help="The MD5 private key is the 32-byte string which is composed of English letters and numbers.")
    alipay_seller_email = fields.Char(string='Alipay Seller Email', groups='base.group_user')

    # def _get_feature_support(self):
        # arj fixme: this method is not used
        # res = super(PaymentAcquirer, self)._get_feature_support()
        # res['fees'].append('alipay')
        # return res

    @api.model
    def _get_alipay_urls(self):
        """ Alipay URLS """
        environment = 'prod' if self.state == 'enabled' else 'test'
        if environment == 'prod':
            return 'https://mapi.alipay.com/gateway.do'
        return 'https://openapi.alipaydev.com/gateway.do'

    def _compute_fees(self, amount, currency_id, country_id):
        """ Compute alipay fees.

            :param float amount: the amount to pay
            :param integer country_id: an ID of a res.country, or None. This is
                                       the customer's country, to be compared to
                                       the acquirer company country.
            :return float fees: computed fees
        """
        fees = 0.0
        if self.fees_active:
            country = self.env['res.country'].browse(country_id)
            if country and self.company_id.country_id.id == country.id:
                percentage = self.fees_dom_var
                fixed = self.fees_dom_fixed
            else:
                percentage = self.fees_int_var
                fixed = self.fees_int_fixed
            fees = (percentage / 100.0 * amount + fixed) / (1 - percentage / 100.0)
        return fees

    def _build_sign(self, val):
        # Rearrange parameters in the data set alphabetically
        data_to_sign = sorted(val.items())
        # Exclude parameters that should not be signed
        data_to_sign = ["{}={}".format(k, v) for k, v in data_to_sign if k not in ['sign', 'sign_type', 'reference']]
        # And connect rearranged parameters with &
        data_string = '&'.join(data_to_sign)
        data_string += self.alipay_md5_signature_key
        return md5(data_string.encode('utf-8')).hexdigest()

    def alipay_get_form_action_url(self):
        self.ensure_one()
        environment = 'prod' if self.state == 'enabled' else 'test'
        return self._get_alipay_urls(environment)
