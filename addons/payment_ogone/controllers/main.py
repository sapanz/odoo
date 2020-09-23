# -*- coding: utf-8 -*-
import logging
import pprint
import werkzeug
from werkzeug import urls

from odoo import http
from odoo.http import request
from odoo.addons.payment.models.payment_acquirer import ValidationError
import odoo.addons.payment.utils as payment_utils
# from odoo.addons.payment.controllers.portal import PaymentProcessing

_logger = logging.getLogger(__name__)


class OgoneController(http.Controller):
    _accept_url = '/payment/ogone/test/accept'
    _decline_url = '/payment/test/ogonedecline'
    _exception_url = '/payment/test/ogone/exception'
    _cancel_url = '/payment/ogone/test/cancel'
    _fleckcheckout_url = '/payment/ogone/flexchekout/feedback'

    @http.route('/payment/ogone/payment_methods', type='json', auth='public')
    def payment_methods(
            self, acquirer_id, amount=None, currency_id=None, partner_id=None, **data
    ):
        """ Query the available payment methods based on the transaction context.

        :param int acquirer_id: The acquirer handling the transaction, as a `payment.acquirer` id
        :param float|None amount: The transaction amount
        :param int|None currency_id: The transaction currency, as a `res.currency` id
        :param int|None partner_id: The partner making the transaction, as a `res.partner` id
        :return: The JSON-formatted content of the response
        :rtype: dict
        """
        acquirer_sudo = request.env['payment.acquirer'].sudo().browse(acquirer_id)
        currency = request.env['res.currency'].browse(currency_id)
        converted_amount = amount
        partner_sudo = partner_id and request.env['res.partner'].browse(partner_id).sudo()
        partner_country_code = partner_sudo and partner_sudo.country_id.code
        lang_code = request.context.get('lang', 'en-US')
        shopper_reference = partner_sudo and f'ODOO_PARTNER_{partner_sudo.id}'
        form_data = {
            'amount': converted_amount,
            'currency': currency,
            'countryCode': partner_country_code,
            'partner_lang': lang_code,  # IETF language tag (e.g.: 'fr-BE')
            'partner_name': partner_sudo.name,
            'reference': shopper_reference,
            'partner_id': partner_sudo.id,
            'currency_id': currency_id,
            'param_plus': data
        }
        return {'ogone_iframe_url': acquirer_sudo._ogone_setup_iframe(form_data), 'acquirer_id': acquirer_id}

    @http.route([
                 '/payment/ogone/flexchekout/feedback'
    ], type='http', auth='public', csrf=False, method=['GET', 'POST'], website=True)
    def ogone_flexcheckout_feedback(self, **data):
        """ Handle both redirection from Ingenico (GET) and s2s notification (POST/GET) """
        _logger.info('Ogone: entering form_feedback with post data %s', pprint.pformat(data))  # debug
        # arj todo: save token accoding to feedback data. Check save permanantly to see if we can process payment with temporary token
        # redirect to a spinner
        # - that page will display some simple html and instanciate a feedbackWidget that will communicate with the
        # parent of the frame (the main page) through events- this is possible since they share the same origin
        # arj fixme: check here what should be in data
        return request.render("payment_ogone.ogone_flexchecout_feedback", {})

    @http.route(['/payment/ogone/payments'], type='json', auth='public', csrf=False)
    def ogone_process_payments(self, **kwargs):
        """ Make a payment request and handle the response.

        :param int acquirer_id: The acquirer handling the transaction, as a `payment.acquirer` id
        :param str reference: The reference of the transaction
        :param int partner_id: The partner making the transaction, as a `res.partner` id
        :param dict ogone_values: ogone specific values used to make the server to server transaction (direct order)
        :return: The JSON-formatted content of the response
        :rtype: dict
        """
        acquirer_id = kwargs.get('acquirer_id')
        reference = kwargs.get('reference')
        ogone_values = kwargs.get('ogone_values')
        partner_id = kwargs.get('partner_id')
        # arj fixme FIRST WE NEED TO CHECK THAT THE ALIAS CREATION WAS CORRECT.
        # todo WE HAVE NO ERROR FOR THE ALIAS CREATION.
        # fixme VERIFY SIGNATURE HERE
        # TODO: check if invalid values (tx, partner currency etc)
        acquirer_sudo = request.env['payment.acquirer'].sudo().browse(acquirer_id)
        tx_sudo = request.env['payment.transaction'].sudo().search([('reference', '=', reference)])
        ogone_values['acquirer_id'] = acquirer_id
        ogone_values['partner_id'] = partner_id
        token_id = acquirer_sudo._ogone_handle_alias_feedback(ogone_values)
        print(ogone_values)
        if not token_id and not ogone_values['AliasId']:
            _logger.error("The Ogone Alias could not be created.")
            # The transaction cannot be completed because we don't have a valid Ogone Alias
            tx_sudo._set_cancelled()
            return {'status': tx_sudo.state}
        if token_id:
            tx_sudo.update({'token_id': token_id.id})
        transaction_result = tx_sudo._send_payment_request()
        print(transaction_result)
        return {'status': tx_sudo.state, 'html_3ds': tx_sudo.ogone_html_3ds, 'state_message': tx_sudo.state_message}

    # @http.route(['/payment/ogone/s2s/create_json'], type='json', auth='public', csrf=False)
    # def ogone_s2s_create_json(self, **kwargs):
    #     if not kwargs.get('partner_id'):
    #         kwargs = dict(kwargs, partner_id=request.env.user.partner_id.id)
    #     new_id = request.env['payment.acquirer'].browse(int(kwargs.get('acquirer_id'))).s2s_process(kwargs)
    #     return new_id.id
    #
    # @http.route(['/payment/ogone/s2s/create_json_3ds'], type='json', auth='public', csrf=False)
    # def ogone_s2s_create_json_3ds(self, verify_validity=False, **kwargs):
    #     if not kwargs.get('partner_id'):
    #         kwargs = dict(kwargs, partner_id=request.env.user.partner_id.id)
    #     token = False
    #     error = None
    #
    #     try:
    #         token = request.env['payment.acquirer'].browse(int(kwargs.get('acquirer_id'))).s2s_process(kwargs)
    #     except Exception as e:
    #         error = str(e)
    #
    #     if not token:
    #         res = {
    #             'result': False,
    #             'error': error,
    #         }
    #         return res
    #
    #     res = {
    #         'result': True,
    #         'id': token.id,
    #         'short_name': token.short_name,
    #         '3d_secure': False,
    #         'verified': False,
    #     }
    #
    #     if verify_validity != False:
    #         baseurl = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
    #         params = {
    #             'accept_url': baseurl + '/payment/ogone/validate/accept',
    #             'decline_url': baseurl + '/payment/ogone/validate/decline',
    #             'exception_url': baseurl + '/payment/ogone/validate/exception',
    #             'return_url': kwargs.get('return_url', baseurl)
    #             }
    #         tx = token.validate(**params)
    #         res['verified'] = token.verified
    #
    #         if tx and tx.html_3ds:
    #             res['3d_secure'] = tx.html_3ds
    #
    #     return res

    # @http.route(['/payment/ogone/s2s/create'], type='http', auth='public', methods=["POST"], csrf=False)
    # def ogone_s2s_create(self, **post):
    #     error = ''
    #     acq = request.env['payment.acquirer'].browse(int(post.get('acquirer_id')))
    #     try:
    #         token = acq.s2s_process(post)
    #     except Exception as e:
    #         # synthax error: 'CHECK ERROR: |Not a valid date\n\n50001111: None'
    #         token = False
    #         error = str(e).splitlines()[0].split('|')[-1] or ''
    #
    #     if token and post.get('verify_validity'):
    #         baseurl = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
    #         params = {
    #             'accept_url': baseurl + '/payment/ogone/validate/accept',
    #             'decline_url': baseurl + '/payment/ogone/validate/decline',
    #             'exception_url': baseurl + '/payment/ogone/validate/exception',
    #             'return_url': post.get('return_url', baseurl)
    #             }
    #         tx = token.validate(**params)
    #         if tx and tx.html_3ds:
    #             return tx.html_3ds
    #         # # add the payment transaction into the session to let the page /payment/process to handle it
    #         PaymentProcessing.add_payment_transaction(tx)
    #     return werkzeug.utils.redirect("/payment/process")
    #
    # @http.route([
    #     '/payment/ogone/validate/accept',
    #     '/payment/ogone/validate/decline',
    #     '/payment/ogone/validate/exception',
    # ], type='http', auth='public')
    # def ogone_validation_form_feedback(self, **post):
    #     """ Feedback from 3d secure for a bank card validation """
    #     request.env['payment.transaction'].sudo().form_feedback(post, 'ogone')
    #     return werkzeug.utils.redirect("/payment/process")
    #
    # @http.route(['/payment/ogone/s2s/feedback'], auth='public', csrf=False)
    # def feedback(self, **kwargs):
    #     try:
    #         tx = request.env['payment.transaction'].sudo()._ogone_form_get_tx_from_data(kwargs)
    #         tx._ogone_s2s_validate_tree(kwargs)
    #     except ValidationError:
    #         return 'ko'
    #     return 'ok'

    @http.route('/payment/ogone/test/<int:debug>', type='http', auth='public', website=True)
    def ogone_test(self, debug):
        import random
        import string
        amount = random.randint(1, 1000)
        letters = string.ascii_lowercase
        reference = 'ARJ' + ''.join(random.choice(letters) for letter in range(10))
        currency_id = 7
        debug_str = '' if not debug else "&debug=assets"
        return werkzeug.utils.redirect(f"/website_payment/pay?amount={amount}&currency_id={currency_id}&reference={reference}{debug_str}")
