# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import datetime
import logging
import time
from pprint import pformat

import requests
from lxml import etree, objectify
from werkzeug import urls

from odoo import api, fields, models, _
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment_ogone.data import ogone
from odoo.http import request
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, ustr
from odoo.tools.float_utils import float_compare

_logger = logging.getLogger(__name__)


class PaymentTxOgone(models.Model):
    _inherit = 'payment.transaction'
    # ogone status
    _ogone_valid_tx_status = [5, 9, 8]
    _ogone_wait_tx_status = [41, 50, 51, 52, 55, 56, 91, 92, 99]
    _ogone_pending_tx_status = [46, 81, 82]   # 46 = 3DS HTML response
    _ogone_cancel_tx_status = [1]

    ogone_html_3ds = fields.Char('3D Secure HTML')

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------

    @api.model
    def _get_tx_from_data(self, provider, data):
        """ Given a data dict coming from ogone, verify it and find the related
        transaction record. Create a payment token if an alias is returned."""
        if provider != 'ogone':
            return super()._get_tx_from_data(provider, data)
        reference, pay_id, shasign, alias = data.get('Alias.orderId'), data.get('PAYID'), data.get('SHASIGN'), data.get('ALIAS')
        if not reference or not pay_id or not shasign:
            error_msg = _('Ogone: received data with missing reference (%s) or pay_id (%s) or shasign (%s)') % (reference, pay_id, shasign)
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        # find tx -> @TDENOTE use paytid ?
        tx = self.search([('reference', '=', reference)])
        if not tx or len(tx) > 1:
            error_msg = _('Ogone: received data for reference %s') % (reference)
            if not tx:
                error_msg += _('; no order found')
            else:
                error_msg += _('; multiple order found')
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        # verify shasign
        shasign_check = tx.acquirer_id._ogone_generate_shasign('out', data)
        if shasign_check.upper() != shasign.upper():
            error_msg = _('Ogone: invalid shasign, received %s, computed %s, for data %s') % (shasign, shasign_check, data)
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        if not tx.acquirer_reference:
            tx.acquirer_reference = pay_id

        # alias was created on ogone server, store it
        if alias and tx.type == 'form_save':
            Token = self.env['payment.token']
            domain = [('acquirer_ref', '=', alias)]
            cardholder = data.get('CN')
            if not Token.search_count(domain):
                _logger.info('Ogone: saving alias %s for partner %s' % (data.get('CARDNO'), tx.partner_id))
                ref = Token.create({'name': data.get('CARDNO') + (' - ' + cardholder if cardholder else ''),
                                    'partner_id': tx.partner_id.id,
                                    'acquirer_id': tx.acquirer_id.id,
                                    'acquirer_ref': alias})
                tx.write({'payment_token_id': ref.id})

        return tx

    def _get_invalid_parameters(self, data):
        if self.provider != 'ogone':
            return super()._get_invalid_parameters(data)
        invalid_parameters = []

        # TODO: txn_id: should be false at draft, set afterwards, and verified with txn details
        if self.acquirer_reference and data.get('PAYID') != self.acquirer_reference:
            invalid_parameters.append(('PAYID', data.get('PAYID'), self.acquirer_reference))
        # check what is bought
        if float_compare(float(data.get('amount', '0.0')), self.amount, 2) != 0:
            invalid_parameters.append(('amount', data.get('amount'), '%.2f' % self.amount))
        if data.get('currency') != self.currency_id.name:
            invalid_parameters.append(('currency', data.get('currency'), self.currency_id.name))

        return invalid_parameters

    def _process_feedback_data(self, data):
        if self.provider != 'ogone':
            return super()._process_feedback_data(data)

        if self.state not in ['draft', 'pending']:
            _logger.info('Ogone: trying to validate an already validated tx (ref %s)', self.reference)
            return True

        status = int(data.get('STATUS', '0'))
        if status in self._ogone_valid_tx_status:
            vals = {
                'date': datetime.datetime.strptime(data['TRXDATE'], '%m/%d/%y').strftime(DEFAULT_SERVER_DATE_FORMAT),
                'acquirer_reference': data['PAYID'],
            }
            # if data.get('ALIAS') and self.partner_id and \
            #    (self.type == 'form_save' or self.acquirer_id.save_token == 'always')\
            #    and not self.payment_token_id:
            #     pm = self.env['payment.token'].create({
            #         'partner_id': self.partner_id.id,
            #         'acquirer_id': self.acquirer_id.id,
            #         'acquirer_ref': data.get('ALIAS'),
            #         'name': '%s - %s' % (data.get('CARDNO'), data.get('CN')),
            #         'verified': True
            #     })
            #     vals.update(payment_token_id=pm.id)
            self.write(vals)
            if self.payment_token_id:
                self.payment_token_id.verified = True
            self._set_transaction_done()
            # self.execute_callback()
            # if this transaction is a validation one, then we refund the money we just withdrawn
            if self.type == 'validation':
                self.s2s_do_refund()

            return True
        elif status in self._ogone_cancel_tx_status:
            self._set_cancelled()
        elif status in self._ogone_pending_tx_status or status in self._ogone_wait_tx_status:
            self._set_pending()
        else:
            error = 'Ogone: feedback error: %(error_str)s\n\n%(error_code)s: %(error_msg)s' % {
                'error_str': data.get('NCERRORPLUS'),
                'error_code': data.get('NCERROR'),
                'error_msg': ogone.OGONE_ERROR_MAP.get(data.get('NCERROR')),
            }
            _logger.info(error)
            self._set_cancelled()
            return False

    def _get_specific_processing_values(self, _processing_values):
        if self.provider != 'ogone':
            return super()._get_specific_processing_values(_processing_values)
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        data = {'acquirer_id': 2, 'provider': 'ogone', 'reference': 'atestARJ-1', 'amount': 300.0, 'currency_id': 1,
         'partner_id': 3}


        tx_values = ({
            # '_input_charset': 'utf-8',
            # 'notify_url': urls.url_join(base_url, AlipayController._notify_url),
            # 'out_trade_no': _processing_values.get('reference'),
            # 'partner': self.acquirer_id.alipay_merchant_partner_id,
            # 'return_url': urls.url_join(base_url, AlipayController._return_url),
            # 'subject': _processing_values.get('reference'),
            # 'total_fee': _processing_values.get('amount') + self.fees
        })
        return super()._get_specific_processing_values(_processing_values)

    # def _get_specific_rendering_values(self, _processing_values):
    #     if self.provider != 'ogone':
    #         return super()._get_specific_rendering_values(_processing_values)
    #     values = {
    #         # 'tx_url': self.acquirer_id._get_alipay_urls(),
    #         # '_input_charset': _processing_values.get('_input_charset'),
    #         # 'currency': _processing_values.get('currency'),
    #         # 'notify_url': _processing_values.get('notify_url'),
    #         # 'out_trade_no': _processing_values.get('out_trade_no'),
    #         # 'partner': self.acquirer_id.alipay_merchant_partner_id,
    #         # 'product_code': _processing_values.get('product_code'),
    #         # 'return_url': _processing_values.get('return_url'),
    #         # 'service': _processing_values.get('service'),
    #         # 'sign': _processing_values.get('sign'),
    #         # 'subject': _processing_values.get('subject'),
    #         # 'sign_type': _processing_values.get('sign_type'),
    #         # 'total_fee': _processing_values.get('total_fee'),
    #         # 'payment_type': _processing_values.get('payment_type'),
    #         # 'seller_email': _processing_values.get('seller_email'),
    #     }
    #     return super()._get_specific_rendering_values(_processing_values)

    # --------------------------------------------------
    # S2S RELATED METHODS
    # --------------------------------------------------
    def _send_payment_request(self):
        super()._send_payment_request()  # Log the 'sent' message
        if self.provider != 'ogone':
            return
        account = self.acquirer_id
        reference = self.reference or "ODOO-%s-%s" % (datetime.datetime.now().strftime('%y%m%d_%H%M%S'), self.partner_id.id)

        # param_plus = {
        #     'return_url': kwargs.get('return_url', False)
        # }

        data = {
            'PSPID': account.ogone_pspid,
            'USERID': account.ogone_userid,
            'PSWD': account.ogone_password,
            'ORDERID': reference,
            'AMOUNT': int(self.amount * 100),
            'CURRENCY': self.currency_id.name,
            'OPERATION': 'SAL',
            'ECI': 9,   # Recurring (from eCommerce)
            'ALIAS': self.token_id.acquirer_ref, # arj fixme problem if the token is not saved.
            'RTIMEOUT': 30,
            # 'PARAMPLUS': urls.url_encode(param_plus),
            'EMAIL': self.partner_id.email or '',
            'CN': self.partner_id.name or '',
        }

        data.update({
            'FLAG3D': 'Y',
            'LANGUAGE': self.partner_id.lang or 'en_US',
        })
        if request:
            data['REMOTE_ADDR'] = request.httprequest.remote_addr

        # if kwargs.get('3d_secure'):
        #     data.update({
        #         'FLAG3D': 'Y',
        #         'LANGUAGE': self.partner_id.lang or 'en_US',
        #     })
        #
        #     for url in 'accept decline exception'.split():
        #         key = '{0}_url'.format(url)
        #         val = kwargs.pop(key, None)
        #         if val:
        #             key = '{0}URL'.format(url).upper()
        #             data[key] = val

        data['SHASIGN'] = self.acquirer_id._ogone_generate_shasign('in', data)

        direct_order_url = self.acquirer_id._ogone_get_urls()['ogone_direct_order_url']

        logged_data = data.copy()
        logged_data.pop('PSWD')
        _logger.info("ogone_s2s_do_transaction: Sending values to URL %s, values:\n%s", direct_order_url, pformat(logged_data))
        result = requests.post(direct_order_url, data=data).content

        try:
            tree = objectify.fromstring(result)
            _logger.info('ogone_s2s_do_transaction: Values received:\n%s', etree.tostring(tree, pretty_print=True, encoding='utf-8'))
        except etree.XMLSyntaxError:
            # invalid response from ogone
            _logger.exception('Invalid xml response from ogone')
            _logger.info('ogone_s2s_do_transaction: Values received:\n%s', result)
            raise

        return self._ogone_s2s_validate_tree(tree)

    def ogone_s2s_do_refund(self, **kwargs):
        # arj todo: we keep them but rename
        account = self.acquirer_id
        reference = self.reference or "ODOO-%s-%s" % (datetime.datetime.now().strftime('%y%m%d_%H%M%S'), self.partner_id.id)

        data = {
            'PSPID': account.ogone_pspid,
            'USERID': account.ogone_userid,
            'PSWD': account.ogone_password,
            'ORDERID': reference,
            'AMOUNT': int(self.amount * 100),
            'CURRENCY': self.currency_id.name,
            'OPERATION': 'RFS',
            'PAYID': self.acquirer_reference,
        }
        data['SHASIGN'] = self.acquirer_id._ogone_generate_shasign('in', data)
        # arj fixme: update that
        direct_order_url = 'https://secure.ogone.com/ncol/%s/maintenancedirect.asp' % ('prod' if self.acquirer_id.state == 'enabled' else 'test')

        logged_data = data.copy()
        logged_data.pop('PSWD')
        _logger.info("ogone_s2s_do_refund: Sending values to URL %s, values:\n%s", direct_order_url, pformat(logged_data))
        result = requests.post(direct_order_url, data=data).content

        try:
            tree = objectify.fromstring(result)
            _logger.info('ogone_s2s_do_refund: Values received:\n%s', etree.tostring(tree, pretty_print=True, encoding='utf-8'))
        except etree.XMLSyntaxError:
            # invalid response from ogone
            _logger.exception('Invalid xml response from ogone')
            _logger.info('ogone_s2s_do_refund: Values received:\n%s', result)
            self.ogone_feedback_message = str(result)
            raise

        return self._ogone_s2s_validate_tree(tree)

    def _ogone_s2s_validate(self):
        # arj todo: we keep them but rename
        tree = self._ogone_s2s_get_tx_status()
        return self._ogone_s2s_validate_tree(tree)

    def _ogone_s2s_validate_tree(self, tree, tries=2):
        # arj todo: we keep them but rename
        if self.state not in ['draft', 'pending']:
            _logger.info('Ogone: trying to validate an already validated tx (ref %s)', self.reference)
            return True

        status = int(tree.get('STATUS') or 0)
        if status in self._ogone_valid_tx_status:
            self.write({
                'acquirer_reference': tree.get('PAYID'),
            })
            if tree.get('ALIAS') and self.partner_id and \
               (self.type == 'form_save' or self.acquirer_id.save_token == 'always')\
               and not self.payment_token_id:
                pm = self.env['payment.token'].create({
                    'partner_id': self.partner_id.id,
                    'acquirer_id': self.acquirer_id.id,
                    'acquirer_ref': tree.get('ALIAS'),
                    'name': tree.get('CARDNO'),
                })
                self.write({'payment_token_id': pm.id})
            if self.token_id:
                self.token_id.verified = True
            self._set_done()
            # if this transaction is a validation one, then we refund the money we just withdrawn
            # if self.is_validation == 'validation':
            #     self.s2s_do_refund()
            return True
        elif status in self._ogone_cancel_tx_status:
            self.write({'acquirer_reference': tree.get('PAYID')})
            self._set_canceled()
        elif status in self._ogone_pending_tx_status:
            vals = {
                'acquirer_reference': tree.get('PAYID'),
            }
            if status == 46: # HTML 3DS
                vals['ogone_html_3ds'] = ustr(base64.b64decode(tree.HTML_ANSWER.text))
            self.write(vals)
            self._set_pending()
            return False
        elif status in self._ogone_wait_tx_status and tries > 0:
            time.sleep(0.5)
            self.write({'acquirer_reference': tree.get('PAYID')})
            tree = self._ogone_s2s_get_tx_status()
            return self._ogone_s2s_validate_tree(tree, tries - 1)
        else:
            error = 'Ogone: feedback error: %(error_str)s\n\n%(error_code)s: %(error_msg)s' % {
                'error_str': tree.get('NCERRORPLUS'),
                'error_code': tree.get('NCERROR'),
                'error_msg': ogone.OGONE_ERROR_MAP.get(tree.get('NCERROR')),
            }
            _logger.info(error)

            self.write({
                'state_message': error,
                'acquirer_reference': tree.get('PAYID'),
            })
            self._set_canceled()
            return False

    def _ogone_s2s_get_tx_status(self):
        account = self.acquirer_id
        #reference = tx.reference or "ODOO-%s-%s" % (datetime.datetime.now().strftime('%Y%m%d_%H%M%S'), tx.partner_id.id)

        data = {
            'PAYID': self.acquirer_reference,
            'PSPID': account.ogone_pspid,
            'USERID': account.ogone_userid,
            'PSWD': account.ogone_password,
        }

        query_direct_url = 'https://secure.ogone.com/ncol/%s/querydirect.asp' % ('prod' if self.acquirer_id.state == 'enabled' else 'test')

        logged_data = data.copy()
        logged_data.pop('PSWD')

        _logger.info("_ogone_s2s_get_tx_status: Sending values to URL %s, values:\n%s", query_direct_url, pformat(logged_data))
        result = requests.post(query_direct_url, data=data).content

        try:
            tree = objectify.fromstring(result)
            _logger.info('_ogone_s2s_get_tx_status: Values received:\n%s', etree.tostring(tree, pretty_print=True, encoding='utf-8'))
        except etree.XMLSyntaxError:
            # invalid response from ogone
            _logger.exception('Invalid xml response from ogone')
            _logger.info('_ogone_s2s_get_tx_status: Values received:\n%s', result)
            raise

        return tree
