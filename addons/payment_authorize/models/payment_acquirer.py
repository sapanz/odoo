from .authorize_request import AuthorizeAPI
import hashlib
import hmac
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AuthorizePaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[
        ('authorize', 'Authorize.Net')
    ], ondelete={'authorize': 'set default'})
    authorize_login = fields.Char(string='API Login Id', required_if_provider='authorize', groups='base.group_user')
    authorize_transaction_key = fields.Char(string='API Transaction Key', required_if_provider='authorize', groups='base.group_user')
    authorize_signature_key = fields.Char(string='API Signature Key', required_if_provider='authorize', groups='base.group_user')
    authorize_client_key = fields.Char(string='API Client Key', groups='base.group_user')

    @api.onchange('provider', 'check_validity')
    def onchange_check_validity(self):
        if self.provider == 'authorize' and self.check_validity:
            self.check_validity = False
            return {'warning': {
                'title': _("Warning"),
                'message': ('This option is not supported for Authorize.net')}}

    def _authorize_action_client_secret(self):
        # TODO check that when I can boot odoo on this branch
        api = AuthorizeAPI(self)
        if not api.test_authenticate():
            raise UserError(_('Unable to fetch Client Key, make sure the API Login and Transaction Key are correct.'))
        self.authorize_client_key = api.get_client_secret()
        return True

    def _authorize_generate_hashing(self, values):
        data = '^'.join([
            values['x_login'],
            values['x_fp_sequence'],
            values['x_fp_timestamp'],
            values['x_amount'],
            values['x_currency_code']]).encode('utf-8')

        return hmac.new(bytes.fromhex(self.authorize_signature_key), data, hashlib.sha512).hexdigest().upper()

    def _authorize_get_redirect_action_url(self):
        """
        Note: self.ensure_one()
        """
        self.ensure_one()

        if self.state == 'enabled':
            return 'https://secure2.authorize.net/gateway/transact.dll'
        else:
            return 'https://test.authorize.net/gateway/transact.dll'

    # TODO the below methods aren't ready yet in payment module (05/10)

    @api.model
    def authorize_s2s_form_process(self, data):
        values = {
            'opaqueData': data.get('opaqueData'),
            'encryptedCardData': data.get('encryptedCardData'),
            'acquirer_id': int(data.get('acquirer_id')),
            'partner_id': int(data.get('partner_id'))
        }
        PaymentMethod = self.env['payment.token'].sudo().create(values)
        return PaymentMethod

    def authorize_s2s_form_validate(self, data):
        error = dict()
        mandatory_fields = ["opaqueData", "encryptedCardData"]
        # Validation
        for field_name in mandatory_fields:
            if not data.get(field_name):
                error[field_name] = 'missing'
        return False if error else True
