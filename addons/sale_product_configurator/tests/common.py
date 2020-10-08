# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase, SingleTransactionCase


class TestProductConfiguratorCommon(SingleTransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.PLOP = cls.env['product.template'].create({
            'name': 'Test Product',
            'is_published': True,
            'list_price': 750,
        })