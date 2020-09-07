import json
import logging
import dateutil.parser
import pytz
from werkzeug import urls

from odoo import api, fields, models, _
from odoo.addons.payment_paypal.controllers.main import PaypalController
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.tools.float_utils import float_compare


_logger = logging.getLogger(__name__)


class PaypalPaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    paypal_txn_type = fields.Char('Transaction type')

    def _get_specific_rendering_values(self, _processing_values):
        """
        override from payment
        """
        base_url = self.acquirer_id._get_base_url()

        return {
            **_processing_values,
            'cmd': '_xclick',
            'business': self.acquirer_id.paypal_email_account,
            'item_name': '%s: %s' % (self.acquirer_id.company_id.name, _processing_values['reference']),
            'item_number': _processing_values['reference'],
            'currency_code': self.currency_id.name or '',
            'address1': self.partner_address,
            'city': self.partner_city,
            'country': self.partner_country_id.code or '',
            # TODO see if state comes from a l10n module or what
            'state': self.partner_state if hasattr(self, 'partner_state') else '',
            'email': self.partner_email,
            'zip_code': self.partner_zip,
            'first_name': self.partner_name,  # TODO do I split or something ?
            'last_name': self.partner_name,
            'tx_url': self.acquirer_id._get_redirect_action_url(),
            'paypal_return': urls.url_join(base_url, PaypalController._return_url),
            'notify_url': urls.url_join(base_url, PaypalController._notify_url),
            'cancel_return': urls.url_join(base_url, PaypalController._cancel_url),
            'paypal_use_ipn': self.acquirer_id.paypal_use_ipn,
            'handling': self.fees if self.acquirer_id.fees_active else False,
            'custom': json.dumps({'return_url': '%s' % _processing_values.pop('return_url')}) if _processing_values.get('return_url') else False,
        }

    @api.model
    def _get_tx_from_data(self, provider, data):
        """
        override from payment
        """
        if provider != 'paypal':
            return super()._get_tx_from_data(data)

        reference = data.get('item_number')
        txn_id = data.get('txn_id')

        if not reference or not txn_id:
            error_msg = _('Paypal: received data with missing reference (%s) or txn_id (%s)') % (reference, txn_id)
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        # find tx -> @TDENOTE use txn_id ?
        txs = self.env['payment.transaction'].search([('reference', '=', reference)])
        if not txs or len(txs) > 1:
            error_msg = 'Paypal: received data for reference %s' % (reference)
            if not txs:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.info(error_msg)
            raise ValidationError(error_msg)
        return txs[0]

    def _get_invalid_parameters(self, data):
        """
        override from payment
        """
        if self.acquirer_id.provider != 'paypal':
            return super()._get_invalid_parameters(data)
        self.ensure_one()

        invalid_parameters = []
        _logger.info('Received a notification from Paypal with IPN version %s', data.get('notify_version'))
        if data.get('test_ipn'):
            _logger.warning(
                'Received a notification from Paypal using sandbox'
            ),

        # TODO: txn_id: shoudl be false at draft, set afterwards, and verified with txn details
        if self.acquirer_reference and data.get('txn_id') != self.acquirer_reference:
            invalid_parameters.append(('txn_id', data.get('txn_id'), self.acquirer_reference))
        # check what is buyed
        if float_compare(float(data.get('mc_gross', '0.0')), (self.amount + self.fees), 2) != 0:
            invalid_parameters.append(
                ('mc_gross', data.get('mc_gross'), '%.2f' % (self.amount + self.fees)))  # mc_gross is amount + fees
        if data.get('mc_currency') != self.currency_id.name:
            invalid_parameters.append(('mc_currency', data.get('mc_currency'), self.currency_id.name))
        if 'handling_amount' in data and float_compare(float(data.get('handling_amount')), self.fees, 2) != 0:
            invalid_parameters.append(('handling_amount', data.get('handling_amount'), self.fees))
        # check buyer
        if self.payment_token_id and data.get('payer_id') != self.payment_token_id.acquirer_ref:
            invalid_parameters.append(('payer_id', data.get('payer_id'), self.payment_token_id.acquirer_ref))
        # check seller
        if data.get('receiver_id') and self.acquirer_id.paypal_seller_account and data[
            'receiver_id'] != self.acquirer_id.paypal_seller_account:
            invalid_parameters.append(('receiver_id', data.get('receiver_id'), self.acquirer_id.paypal_seller_account))
        if not data.get('receiver_id') or not self.acquirer_id.paypal_seller_account:
            # Check receiver_email only if receiver_id was not checked.
            # In Paypal, this is possible to configure as receiver_email a different email than the business email (the login email)
            # In Odoo, there is only one field for the Paypal email: the business email. This isn't possible to set a receiver_email
            # different than the business email. Therefore, if you want such a configuration in your Paypal, you are then obliged to fill
            # the Merchant ID in the Paypal payment acquirer in Odoo, so the check is performed on this variable instead of the receiver_email.
            # At least one of the two checks must be done, to avoid fraudsters.
            if data.get('receiver_email') and data.get('receiver_email') != self.acquirer_id.paypal_email_account:
                invalid_parameters.append(
                    ('receiver_email', data.get('receiver_email'), self.acquirer_id.paypal_email_account))
            if data.get('business') and data.get('business') != self.acquirer_id.paypal_email_account:
                invalid_parameters.append(('business', data.get('business'), self.acquirer_id.paypal_email_account))

        return invalid_parameters

    def _process_feedback_data(self, data):
        """
        override from payment

        Note: self.ensure_one()
        """
        self.ensure_one()

        if self.acquirer_id.provider != 'paypal':
            return super()._process_feedback_data(data)
        self.ensure_one()

        status = data.get('payment_status')
        former_tx_state = self.state
        res = {
            'acquirer_reference': data.get('txn_id'),
            'paypal_txn_type': data.get('payment_type'),
        }
        if not self.acquirer_id.paypal_pdt_token and not self.acquirer_id.paypal_seller_account and status in [
            'Completed', 'Processed', 'Pending']:
            template = self.env.ref('payment_paypal.mail_template_paypal_invite_user_to_configure', False)
            if template:
                render_template = template._render({
                    'acquirer': self.acquirer_id,
                }, engine='ir.qweb')
                mail_body = self.env['mail.render.mixin']._replace_local_links(render_template)
                mail_values = {
                    'body_html': mail_body,
                    'subject': _('Add your Paypal account to Odoo'),
                    'email_to': self.acquirer_id.paypal_email_account,
                    'email_from': self.acquirer_id.create_uid.email_formatted,
                    'author_id': self.acquirer_id.create_uid.partner_id.id,
                }
                self.env['mail.mail'].sudo().create(mail_values).send()

        if status in ['Completed', 'Processed']:
            try:
                # dateutil and pytz don't recognize abbreviations PDT/PST
                tzinfos = {
                    'PST': -8 * 3600,
                    'PDT': -7 * 3600,
                }
                date = dateutil.parser.parse(data.get('payment_date'), tzinfos=tzinfos).astimezone(pytz.utc).replace(
                    tzinfo=None)
            except:
                date = fields.Datetime.now()
            res.update(last_state_change=date)
            self._set_done()
            if self.state == 'done' and self.state != former_tx_state:
                _logger.info('Validated Paypal payment for tx %s: set as done' % (self.reference))
                return self.write(res)
            return True
        elif status in ['Pending', 'Expired']:
            res.update(state_message=data.get('pending_reason', ''))
            self._set_pending()
            if self.state == 'pending' and self.state != former_tx_state:
                _logger.info('Received notification for Paypal payment %s: set as pending' % (self.reference))
                return self.write(res)
            return True
        else:
            error = 'Received unrecognized status for Paypal payment %s: %s, set as error' % (self.reference, status)
            res.update(state_message=error)
            self._set_cancel()
            if self.state == 'cancel' and self.state != former_tx_state:
                _logger.info(error)
                return self.write(res)
            return True
