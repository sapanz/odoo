# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class PartnerAutocompleteCase(common.SavepointCase):

    def test_extract_company_domain(self):
        company_1 = self.env['res.company'].create({'name': "Test Company 1"})
        company_1.email = 'info@waterlink.be'
        self.assertEqual(company_1._get_company_domain(), "waterlink.be")

        company_1.website = 'http://www.info.proximus.be/faq/test'
        self.assertEqual(company_1._get_company_domain(), "proximus.be")

        company_1.website = False
        company_1.email = False
        self.assertEqual(company_1._get_company_domain(), False)

        company_1.email = "at@"
        self.assertEqual(company_1._get_company_domain(), False)

        company_1.website = "http://superFalsyWebsiteName"
        self.assertEqual(company_1._get_company_domain(), False)
