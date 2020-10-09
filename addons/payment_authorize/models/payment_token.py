from odoo import models, fields, api, _
from odoo.addons.payment_authorize.models.authorize_request import AuthorizeAPI
from odoo.exceptions import ValidationError


class AuthorizePaymentToken(models.Model):
    _inherit = 'payment.token'

    authorize_profile = fields.Char(string='Authorize.net Profile ID', help='This contains the unique reference '
                                    'for this partner/payment token combination in the Authorize.net backend')
    provider = fields.Selection(string='Provider', related='acquirer_id.provider', readonly=False)
    # TODO this field doesn't exist on the acquirer anymore
    #  Do I need to migrate or can I get rid of this field ?
    # save_token = fields.Selection(string='Save Cards', related='acquirer_id.save_token', readonly=False)

    @api.model
    def authorize_create(self, values):
        if values.get('opaqueData') and values.get('encryptedCardData'):
            acquirer = self.env['payment.acquirer'].browse(values['acquirer_id'])
            partner = self.env['res.partner'].browse(values['partner_id'])
            transaction = AuthorizeAPI(acquirer)
            res = transaction.create_customer_profile(partner, values['opaqueData'])
            if res.get('profile_id') and res.get('payment_profile_id'):
                return {
                    'authorize_profile': res.get('profile_id'),
                    'name': values['encryptedCardData'].get('cardNumber'),
                    'acquirer_ref': res.get('payment_profile_id'),
                    'verified': True
                }
            else:
                raise ValidationError(_('The Customer Profile creation in Authorize.NET failed.'))
        else:
            return values