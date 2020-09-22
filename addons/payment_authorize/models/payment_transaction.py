import time
import logging
from werkzeug import urls

from odoo import models, api, _, fields
from odoo.addons.payment_authorize.controllers.main import AuthorizeController
from odoo.addons.payment_authorize.models.authorize_request import AuthorizeAPI
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare
from odoo.tools.float_utils import float_repr


_logger = logging.getLogger(__name__)


class AuthorizePaymentToken(models.Model):
    _inherit = 'payment.transaction'

    _authorize_valid_tx_status = 1
    _authorize_pending_tx_status = 4
    _authorize_cancel_tx_status = 2
    _authorize_error_tx_status = 3

    def _get_specific_rendering_values(self, _processing_values):
        """
        override from payment

        Note: self.ensure_one()
        """
        self.ensure_one()
        # State code is only supported in US, use state name by default
        # See https://developer.authorize.net/api/reference/
        state = _processing_values['partner_state'].name if _processing_values.get('partner_state') else ''
        if _processing_values.get('partner_country') and _processing_values.get('partner_country') == self.env.ref('base.us', False):
            state = _processing_values['partner_state'].code if _processing_values.get('partner_state') else ''

        billing_state = _processing_values['billing_partner_state'].name if _processing_values.get('billing_partner_state') else ''
        if _processing_values.get('billing_partner_country') and _processing_values.get('billing_partner_country') == self.env.ref(
                'base.us', False):
            billing_state = _processing_values['billing_partner_state'].code if _processing_values.get('billing_partner_state') else ''

        base_url = self.get_base_url()

        values = {
            **_processing_values,
            'x_login': self.authorize_login,
            'x_amount': float_repr(_processing_values['amount'],
                                   _processing_values['currency'].decimal_places if _processing_values['currency'] else 2),
            'x_show_form': 'PAYMENT_FORM',
            'x_type': 'AUTH_CAPTURE' if not self.capture_manually else 'AUTH_ONLY',
            'x_method': 'CC',
            'x_fp_sequence': '%s%s' % (self.id, int(time.time())),
            'x_version': '3.1',
            'x_relay_response': 'TRUE',
            'x_fp_timestamp': str(int(time.time())),
            'x_relay_url': urls.url_join(base_url, AuthorizeController._return_url),
            'x_cancel_url': urls.url_join(base_url, AuthorizeController._cancel_url),
            'x_currency_code': _processing_values['currency'] and _processing_values['currency'].name or '',
            'address': _processing_values.get('partner_address'),
            'city': _processing_values.get('partner_city'),
            'country': _processing_values.get('partner_country') and _processing_values.get('partner_country').name or '',
            'email': _processing_values.get('partner_email'),
            'zip_code': _processing_values.get('partner_zip'),
            'first_name': _processing_values.get('partner_first_name'),
            'last_name': _processing_values.get('partner_last_name'),
            'phone': _processing_values.get('partner_phone'),
            'state': state,
            'billing_address': _processing_values.get('billing_partner_address'),
            'billing_city': _processing_values.get('billing_partner_city'),
            'billing_country': _processing_values.get('billing_partner_country') and _processing_values.get(
                'billing_partner_country').name or '',
            'billing_email': _processing_values.get('billing_partner_email'),
            'billing_zip_code': _processing_values.get('billing_partner_zip'),
            'billing_first_name': _processing_values.get('billing_partner_first_name'),
            'billing_last_name': _processing_values.get('billing_partner_last_name'),
            'billing_phone': _processing_values.get('billing_partner_phone'),
            'billing_state': billing_state,
            'tx_url': self.acquirer_id._authorize_get_redirect_action_url()
        }

        values['returndata'] = values.pop('return_url', '')
        values['x_fp_hash'] = self._authorize_generate_hashing(values)

        return values

    @api.model
    def _get_tx_from_data(self, provider, data):
        """
        override from payment
        """
        if provider != 'authorize':
            return super()._get_tx_from_data(data)

        reference, trans_id, fingerprint = data.get('x_invoice_num'), data.get('x_trans_id'), data.get('x_SHA2_Hash') or data.get('x_MD5_Hash')
        if not reference or not trans_id or not fingerprint:
            error_msg = _('Authorize: received data with missing reference (%s) or trans_id (%s) or fingerprint (%s)') % (reference, trans_id, fingerprint)
            _logger.info(error_msg)
            raise ValidationError(error_msg)
        tx = self.search([('reference', '=', reference)])
        if not tx or len(tx) > 1:
            error_msg = 'Authorize: received data for reference %s' % (reference)
            if not tx:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.info(error_msg)
            raise ValidationError(error_msg)
        return tx[0]

    def _get_invalid_parameters(self, data):
        """
        override from payment

        Note: self.ensure_one()
        """
        self.ensure_one()

        if self.acquirer_id.provider != 'authorize':
            return super()._get_invalid_parameters(data)

        invalid_parameters = []

        if self.acquirer_reference and data.get('x_trans_id') != self.acquirer_reference:
            invalid_parameters.append(('Transaction Id', data.get('x_trans_id'), self.acquirer_reference))
        # check what is buyed
        if float_compare(float(data.get('x_amount', '0.0')), self.amount, 2) != 0:
            invalid_parameters.append(('Amount', data.get('x_amount'), '%.2f' % self.amount))
        return invalid_parameters

    def _process_feedback_data(self, data):
        """
        override from payment

        self.ensure_one()
        """
        self.ensure_one()

        if self.acquirer_id.provider != 'authorize':
            return super()._process_feedback_data(data)

        if self.state == 'done':
            _logger.warning('Authorize: trying to validate an already validated tx (ref %s)' % self.reference)
            return True
        status_code = int(data.get('x_response_code', '0'))
        if status_code == self._authorize_valid_tx_status:
            if data.get('x_type').lower() in ['auth_capture', 'prior_auth_capture']:
                self.write({
                    'acquirer_reference': data.get('x_trans_id'),
                    'date': fields.Datetime.now(),
                })
                self._set_transaction_done()
            elif data.get('x_type').lower() in ['auth_only']:
                self.write({'acquirer_reference': data.get('x_trans_id')})
                self._set_transaction_authorized()
            if self.partner_id and not self.payment_token_id and \
               (self.type == 'form_save' or self.acquirer_id.save_token == 'always'):
                transaction = AuthorizeAPI(self.acquirer_id)
                res = transaction.create_customer_profile_from_tx(self.partner_id, self.acquirer_reference)
                if res:
                    token_id = self.env['payment.token'].create({
                        'authorize_profile': res.get('profile_id'),
                        'name': res.get('name'),
                        'acquirer_ref': res.get('payment_profile_id'),
                        'acquirer_id': self.acquirer_id.id,
                        'partner_id': self.partner_id.id,
                    })
                    self.payment_token_id = token_id
            return True
        elif status_code == self._authorize_pending_tx_status:
            self.write({'acquirer_reference': data.get('x_trans_id')})
            self._set_transaction_pending()
            return True
        else:
            error = data.get('x_response_reason_text')
            _logger.info(error)
            self.write({
                'state_message': error,
                'acquirer_reference': data.get('x_trans_id'),
            })
            self._set_transaction_cancel()
            return False

    ########################
    #  CLEAN DOWN TO HERE  #
    ########################

    def authorize_s2s_do_transaction(self, **data):
        self.ensure_one()
        transaction = AuthorizeAPI(self.acquirer_id)

        if not self.payment_token_id.authorize_profile:
            raise UserError(_('Invalid token found: the Authorize profile is missing.'
                              'Please make sure the token has a valid acquirer reference.'))

        if not self.acquirer_id.capture_manually:
            res = transaction.auth_and_capture(self.payment_token_id, round(self.amount, self.currency_id.decimal_places), self.reference)
        else:
            res = transaction.authorize(self.payment_token_id, round(self.amount, self.currency_id.decimal_places), self.reference)
        return self._authorize_s2s_validate_tree(res)

    def authorize_s2s_capture_transaction(self):
        self.ensure_one()
        transaction = AuthorizeAPI(self.acquirer_id)
        tree = transaction.capture(self.acquirer_reference or '', round(self.amount, self.currency_id.decimal_places))
        return self._authorize_s2s_validate_tree(tree)

    def authorize_s2s_void_transaction(self):
        self.ensure_one()
        transaction = AuthorizeAPI(self.acquirer_id)
        tree = transaction.void(self.acquirer_reference or '')
        return self._authorize_s2s_validate_tree(tree)

    def _authorize_s2s_validate_tree(self, tree):
        return self._authorize_s2s_validate(tree)

    def _authorize_s2s_validate(self, tree):
        if self.state == 'done':
            _logger.warning('Authorize: trying to validate an already validated tx (ref %s)' % self.reference)
            return True
        status_code = int(tree.get('x_response_code', '0'))
        if status_code == self._authorize_valid_tx_status:
            if tree.get('x_type').lower() in ['auth_capture', 'prior_auth_capture']:
                init_state = self.state
                self.write({
                    'acquirer_reference': tree.get('x_trans_id'),
                    'date': fields.Datetime.now(),
                })

                self._set_transaction_done()

                if init_state != 'authorized':
                    self.execute_callback()
            if tree.get('x_type').lower() == 'auth_only':
                self.write({'acquirer_reference': tree.get('x_trans_id')})
                self._set_transaction_authorized()
                self.execute_callback()
            if tree.get('x_type').lower() == 'void':
                self._set_transaction_cancel()
            return True
        elif status_code == self._authorize_pending_tx_status:
            self.write({'acquirer_reference': tree.get('x_trans_id')})
            self._set_transaction_pending()
            return True
        else:
            error = tree.get('x_response_reason_text')
            _logger.info(error)
            self.write({
                'acquirer_reference': tree.get('x_trans_id'),
            })
            self._set_transaction_error(msg=error)
            return False