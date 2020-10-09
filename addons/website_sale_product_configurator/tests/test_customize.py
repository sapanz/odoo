# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.base.tests.common import HttpCaseWithUserDemo, HttpCaseWithUserPortal
from odoo.addons.sale_product_configurator.tests.common import TestProductConfiguratorCommon
from odoo.tests import tagged

# arj fixme: remove this tag
@tagged('post_install', '-at_install', 'arj')
class TestUi(HttpCaseWithUserDemo, HttpCaseWithUserPortal, TestProductConfiguratorCommon):

    def setUp(self):
        super(TestUi, self).setUp()
        # # create a template
        product_template = self.env['product.template'].create({
            'name': 'Test Product',
            'is_published': True,
            'list_price': 750,
        })

        tax = self.env['account.tax'].create({'name': "Test tax", 'amount': 10})
        product_template.taxes_id = tax

        product_attribute = self.env['product.attribute'].create({
            'name': 'Legs',
            'sequence': 10,
        })
        product_attribute_value_1 = self.env['product.attribute.value'].create({
            'name': 'Steel - Test',
            'attribute_id': product_attribute.id,
            'sequence': 1,
        })
        product_attribute_value_2 = self.env['product.attribute.value'].create({
            'name': 'Aluminium',
            'attribute_id': product_attribute.id,
            'sequence': 2,
        })

        # # set attribute and attribute values on the template
        self.env['product.template.attribute.line'].create([{
            'attribute_id': product_attribute.id,
            'product_tmpl_id': product_template.id,
            'value_ids': [(6, 0, [product_attribute_value_1.id, product_attribute_value_2.id])]
        }])

        # set a different price on the variants to differentiate them
        product_template_attribute_values = self.env['product.template.attribute.value'] \
            .search([('product_tmpl_id', '=', product_template.id)])
        for ptav in product_template_attribute_values:
            if ptav.name == "Steel - Test":
                ptav.price_extra = 0
            else:
                ptav.price_extra = 50.4

    def test_01_admin_shop_custom_attribute_value_tour(self):
        # Make sure pricelist rule exist
        # self.product_attribute_1 = self.env['product.attribute'].create({
        #     'name': 'Legs',
        #     'sequence': 10,
        # })
        # product_attribute_value_1 = self.env['product.attribute.value'].create({
        #     'name': 'Steel',
        #     'attribute_id': self.product_attribute_1.id,
        #     'sequence': 1,
        # })
        # product_attribute_value_2 = self.env['product.attribute.value'].create({
        #     'name': 'Aluminium',
        #     'attribute_id': self.product_attribute_1.id,
        #     'sequence': 2,
        # })
        # product_attribute_2 = self.env['product.attribute'].create({
        #     'name': 'Color',
        #     'sequence': 20,
        # })
        # product_attribute_value_3 = self.env['product.attribute.value'].create({
        #     'name': 'White',
        #     'attribute_id': product_attribute_2.id,
        #     'sequence': 1,
        # })
        # product_attribute_value_4 = self.env['product.attribute.value'].create({
        #     'name': 'Black',
        #     'attribute_id': product_attribute_2.id,
        #     'sequence': 2,
        # })
        #
        # # Create product template
        # self.product_product_4_product_template = self.env['product.template'].create({
        #     'name': 'Customizable Desk (TEST)',
        #     'standard_price': 500.0,
        #     'list_price': 750.0,
        # })
        #
        # # Generate variants
        # self.env['product.template.attribute.line'].create([{
        #     'product_tmpl_id': self.product_product_4_product_template.id,
        #     'attribute_id': self.product_attribute_1.id,
        #     'value_ids': [(4, product_attribute_value_1.id), (4, product_attribute_value_2.id)],
        # }, {
        #     'product_tmpl_id': self.product_product_4_product_template.id,
        #     'attribute_id': product_attribute_2.id,
        #     'value_ids': [(4, product_attribute_value_3.id), (4, product_attribute_value_4.id)],
        #
        # }])

        #
        # # Add Custom Attribute
        # product_attribute_value_7 = self.env['product.attribute.value'].create({
        #     'name': 'Custom TEST',
        #     'attribute_id': self.product_attribute_1.id,
        #     'sequence': 3,
        #     'is_custom': True
        # })
        # self.product_product_4_product_template.attribute_line_ids[0].write({'value_ids': [(4, product_attribute_value_7.id)]})
        #
        # img_path = get_module_resource('product', 'static', 'img', 'product_product_11-image.png')
        # img_content = base64.b64encode(open(img_path, "rb").read())
        # self.product_product_11_product_template = self.env['product.template'].create({
        #     'name': 'Conference Chair (TEST)',
        #     'website_sequence': 9999, # laule
        #     'image_1920': img_content,
        #     'list_price': 16.50,
        # })
        #
        # self.env['product.template.attribute.line'].create({
        #     'product_tmpl_id': self.product_product_11_product_template.id,
        #     'attribute_id': self.product_attribute_1.id,
        #     'value_ids': [(4, product_attribute_value_1.id), (4, product_attribute_value_2.id)],
        # })
        # self.product_product_11_product_template.attribute_line_ids[0].product_template_value_ids[1].price_extra = 6.40
        # self.product_product_4_product_template.optional_product_ids = [(4, self.product_product_11_product_template.id)]
        #
        # # Setup a second optional product
        # self.product_product_1_product_template = self.env['product.template'].create({
        #     'name': 'Chair floor protection',
        #     'list_price': 12.0,
        # })
        # self.product_product_11_product_template.optional_product_ids = [(4, self.product_product_1_product_template.id)]
        #


        a = 0

        self.start_tour("/", 'a_shop_custom_attribute_value', login="admin")
