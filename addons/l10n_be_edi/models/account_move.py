# -*- coding: utf-8 -*-

from odoo import models
import base64


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_ubl_values(self):
        values = super(AccountMove, self)._get_ubl_values()

        # E-fff uses ubl_version 2.0, account_edi_ubl supports ubl_version 2.1 but generates 2.0 UBL
        # so we only need to override the version to be compatible with E-FFF
        values['ubl_version'] = 2.0

        report = self.env.ref('account.account_invoices_without_payment', False)
        html = report._render_qweb_html(self.ids)[0].decode('utf-8')
        bodies, html_ids, header, footer, specific_paperformat_args = report._prepare_html(html)
        if html_ids:
            pdf_content = report._run_wkhtmltopdf(
                bodies,
                header=header,
                footer=footer,
                specific_paperformat_args=specific_paperformat_args
            )
            values['pdf'] = base64.b64encode(pdf_content)
            values['pdf_name'] = self._get_efff_name('.pdf')

        return values

    def _get_efff_name(self, extension):
        self.ensure_one()
        vat = self.company_id.partner_id.commercial_partner_id.vat
        return 'efff-%s%s%s%s' % (vat or '', '-' if vat else '', self.name.replace('/', '_'), extension)  # official naming convention
