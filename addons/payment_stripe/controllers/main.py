# -*- coding: utf-8 -*-
import logging
import pprint
import werkzeug
import requests

from odoo import http
from odoo.http import request
from odoo.addons.payment.controllers.portal import PaymentProcessing

_logger = logging.getLogger(__name__)


class StripeController(http.Controller):

    @http.route(['/payment/stripe/s2s/create_json'], type='json', auth='public')
    def stripe_s2s_create_json(self, **kwargs):
        acquirer_id = int(kwargs.get('acquirer_id'))
        acquirer = request.env['payment.acquirer'].browse(acquirer_id)
        if not kwargs.get('partner_id'):
            kwargs = dict(kwargs, partner_id=request.env.user.partner_id.id)
        return acquirer.s2s_process(kwargs).id

    @http.route(['/payment/stripe/s2s/create'], type='http', auth='public')
    def stripe_s2s_create(self, **post):
        acquirer_id = int(post.get('acquirer_id'))
        acquirer = request.env['payment.acquirer'].browse(acquirer_id)
        error = None
        try:
            acquirer.s2s_process(post)
        except Exception as e:
            error = str(e)

        return_url = post.get('return_url', '/')
        if error:
            separator = '?' if werkzeug.urls.url_parse(return_url).query == '' else '&'
            return_url += '{}{}'.format(separator, werkzeug.urls.url_encode({'error': error}))

        return werkzeug.utils.redirect(return_url)

    @http.route(['/payment/stripe/s2s/create_json_3ds'], type='json', auth='public', csrf=False)
    def stripe_s2s_create_json_3ds(self, verify_validity=False, **kwargs):
        if not kwargs.get('partner_id'):
            kwargs = dict(kwargs, partner_id=request.env.user.partner_id.id)
        token = request.env['payment.acquirer'].browse(int(kwargs.get('acquirer_id'))).s2s_process(kwargs)

        if not token:
            res = {
                'result': False,
            }
            return res

        res = {
            'result': True,
            'id': token.id,
            'short_name': token.short_name,
            '3d_secure': False,
            'verified': False,
        }

        if verify_validity != False:
            token.validate()
            res['verified'] = token.verified

        return res

    @http.route(['/payment/stripe/create_charge'], type='json', auth='public')
    def stripe_create_charge(self, **post):
        """ Create a payment transaction

        Expects the result from the user input from checkout.js popup"""
        TX = request.env['payment.transaction']
        tx = None
        if post.get('tx_ref'):
            tx = TX.sudo().search([('reference', '=', post['tx_ref'])])
        if not tx:
            tx_id = (post.get('tx_id') or request.session.get('sale_transaction_id') or
                     request.session.get('website_payment_tx_id'))
            tx = TX.sudo().browse(int(tx_id))
        if not tx:
            raise werkzeug.exceptions.NotFound()

        stripe_token = post['token']
        response = None
        if tx.type == 'form_save' and tx.partner_id:
            payment_token_id = request.env['payment.token'].sudo().create({
                'acquirer_id': tx.acquirer_id.id,
                'partner_id': tx.partner_id.id,
                'stripe_token': stripe_token
            })
            tx.payment_token_id = payment_token_id
            response = tx._create_stripe_charge(acquirer_ref=payment_token_id.acquirer_ref, email=stripe_token['email'])
        else:
            response = tx._create_stripe_charge(tokenid=stripe_token['id'], email=stripe_token['email'])
        _logger.info('Stripe: entering form_feedback with post data %s', pprint.pformat(response))
        if response:
            request.env['payment.transaction'].sudo().with_context(lang=None).form_feedback(response, 'stripe')
        # add the payment transaction into the session to let the page /payment/process to handle it
        PaymentProcessing.add_payment_transaction(tx)
        return "/payment/process"

    @http.route('/payment/stripe/create_account/<model("payment.acquirer"):acquirer>', auth='user')
    def create_stripe_account(self, acquirer):
        get_param = request.env['ir.config_parameter'].sudo().get_param
        client_id = get_param('payment_stripe_%s_client_id' % acquirer.environment)
        company = request.env.user.company_id
        redirect_uri = get_param('web.base.url') + "/stripe/account_done"
        return werkzeug.utils.redirect('https://connect.stripe.com/oauth/authorize?response_type=code&client_id='+client_id+'&scope=read_write&redirect_uri='+redirect_uri+
            '&stripe_user[country]='+company.country_id.code+'&stripe_user[street_address]='+company.street+'&stripe_user[zip]='+company.zip+'&stripe_user[business_name]='+company.website+
            '&stripe_user[first_name]='+request.env.user.name)

    @http.route('/stripe/account_done', auth='user')
    def stripe_account_done(self, **post):
        acquirer = request.env['payment.acquirer'].search([('provider', '=', 'stripe')], limit=1)
        get_param = request.env['ir.config_parameter'].sudo().get_param
        data = {
            'client_secret': get_param('payment_stripe_%s_client_secret' % acquirer.environment),
            'code': post.get('code'),
            'grant_type': 'authorization_code'
        }
        response = requests.post('https://connect.stripe.com/oauth/token', data)
        response.raise_for_status()
        response = response.json()
        acquirer.write({
            'stripe_secret_key': response['access_token'],
            'stripe_publishable_key': response['stripe_publishable_key'],
            'environment': 'prod',
            'website_published': True,
            'stripe_connect_status_msg': True,
        })
        return werkzeug.utils.redirect('/web#id='+str(acquirer.id)+'&model=payment.acquirer&view_type=form')
