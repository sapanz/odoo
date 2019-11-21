# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from odoo.fields import Datetime
from odoo import tests
from odoo.addons.website_slides.tests.test_ui_wslides import TestUICommon

@tests.common.tagged('post_install', '-at_install')
class TestUi(TestUICommon):

    def test_course_certification_employee(self):
        user_demo = self.user_demo
        user_demo.flush()
        # Avoid Billing/Shipping address page
        user_demo.write({
            'groups_id': [(5, 0), (4, self.env.ref('base.group_user').id)],
            'street': '215 Vine St',
            'city': 'Scranton',
            'zip': '18503',
            'country_id': self.env.ref('base.us').id,
            'state_id': self.env.ref('base.state_us_39').id,
            'phone': '+1 555-555-5555',
            'email': 'admin@yourcompany.example.com',
        })

        # Specify Accounting Data 
        cash_journal = self.env['account.journal'].create({'name': 'Cash - Test', 'type': 'cash', 'code': 'CASH - Test'})
        self.env['payment.acquirer'].search([('journal_id', '=', False)]).journal_id = cash_journal
        a_recv = self.env['account.account'].create({
            'code': 'X1012',
            'name': 'Debtors - (test)',
            'reconcile': True,
            'user_type_id': self.env.ref('account.data_account_type_receivable').id,
        })
        a_pay = self.env['account.account'].create({
            'code': 'X1111',
            'name': 'Creditors - (test)',
            'user_type_id': self.env.ref('account.data_account_type_payable').id,
            'reconcile': True,
        })
        self.env['ir.property'].create([{
            'name': 'property_account_receivable_id',
            'fields_id': self.env['ir.model.fields'].search([('model', '=', 'res.partner'), ('name', '=', 'property_account_receivable_id')], limit=1).id,
            'value': 'account.account,%s' % (a_recv.id),
            'company_id': self.env.company.id,
        }, {
            'name': 'property_account_payable_id',
            'fields_id': self.env['ir.model.fields'].search([('model', '=', 'res.partner'), ('name', '=', 'property_account_payable_id')], limit=1).id,
            'value': 'account.account,%s' % (a_pay.id),
            'company_id': self.env.company.id,
        }])

        product_course_channel_6 = self.env['product.product'].create({
            'name': 'DIY Furniture Course',
            'list_price': 100.0,
            'type': 'service',
            'is_published': True,
        })

        furniture_survey = self.env['survey.survey'].create({
            'title': 'Furniture Creation Certification',
            'access_token': '5632a4d7-48cf-aaaa-8c52-2174d58cf50b',
            'state': 'open',
            'access_mode': 'public',
            'users_can_go_back': True,
            'users_login_required': True,
            'scoring_type': 'scoring_with_answers',
            'certificate': True,
            'certification_mail_template_id': self.env.ref('survey.mail_template_certification').id,
            'is_attempts_limited': True,
            'attempts_limit': 3,
            'description': "<p>Test your furniture knowledge!</p>",
            'question_and_page_ids': [
                (0, 0, {
                    'title': 'Furniture',
                    'sequence': 1,
                    'is_page': True,
                    'description': "&lt;p&gt;Test your furniture knowledge!&lt;/p&gt",
                }), (0, 0, {
                    'title': 'What type of wood is the best for furniture?',
                    'sequence': 2,
                    'question_type': 'simple_choice',
                    'display_mode': 'dropdown',
                    'constr_mandatory': True,
                    'labels_ids': [
                        (0, 0, {
                            'value': 'Fir',
                            'sequence': 1,
                        }), (0, 0, {
                            'value': 'Oak',
                            'sequence': 2,
                            'is_correct': True,
                            'answer_score': 2.0,
                        }), (0, 0, {
                            'value': 'Ash',
                            'sequence': 3,
                        }), (0, 0, {
                            'value': 'Beech',
                            'sequence': 4,
                        })
                    ]
                }), (0, 0, {
                    'title': 'Select all the furniture shown in the video',
                    'sequence': 3,
                    'question_type': 'multiple_choice',
                    'column_nb': '4',
                    'labels_ids': [
                        (0, 0, {
                            'value': 'Chair',
                            'sequence': 1,
                            'is_correct': True,
                            'answer_score': 1.0,
                        }), (0, 0, {
                            'value': 'Table',
                            'sequence': 2,
                            'answer_score': -1.0,
                        }), (0, 0, {
                            'value': 'Desk',
                            'sequence': 3,
                            'is_correct': True,
                            'answer_score': 1.0,
                        }), (0, 0, {
                            'value': 'Shelve',
                            'sequence': 4,
                            'is_correct': True,
                            'answer_score': 1.0,
                        }), (0, 0, {
                            'value': 'Bed',
                            'sequence': 5,
                            'answer_score': -1.0,
                        })
                    ]
                }), (0, 0, {
                    'title': 'What do you think about the content of the course? (not rated)',
                    'sequence': 4,
                    'question_type': 'free_text',
                })
            ]
        })

        slide_channel_demo_6_furn3 = self.env['slide.channel'].create({
            'name': 'DIY Furniture - TEST',
            'user_id': self.env.ref('base.user_admin').id,
            'enroll': 'payment',
            'product_id': product_course_channel_6.id,
            'channel_type': 'training',
            'allow_comment': True,
            'promote_strategy': 'most_voted',
            'is_published': True,
            'description': 'So much amazing certification.',
            'create_date': Datetime.now() - relativedelta(days=2),
            'slide_ids': [
                (0, 0, {
                    'name': 'DIY Furniture Certification',
                    'sequence': 1,
                    'slide_type': 'certification',
                    'category_id': False,
                    'is_published': True,
                    'is_preview': False,
                    'description': "It's time to test your knowledge!",
                    'survey_id': furniture_survey.id,
                })
            ]
        })

        self.browser_js(
            '/slides',
            'odoo.__DEBUG__.services["web_tour.tour"].run("certification_member")',
            'odoo.__DEBUG__.services["web_tour.tour"].tours.certification_member.ready',
            login=user_demo.login)
