# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
import odoo.tests


@odoo.tests.tagged('-at_install', 'post_install')
class TestUiCustomizeTheme(odoo.tests.HttpCase):
    def test_01_attachment_website_unlink(self):
        ''' Some ir.attachment needs to be unlinked when a website is unlink,
            otherwise some flows will just crash. That's the case when 2 website
            have their theme color customized. Removing a website will make its
            customized attachment generic, thus having 2 attachments with the
            same URL available for other websites, leading to singleton errors
            (among other).

            But no all attachment should be deleted, eg we don't want to delete
            a SO or invoice PDF coming from an ecommerce order.
        '''
        Website = self.env['website']
        Page = self.env['website.page']
        Attachment = self.env['ir.attachment']

        website_default = Website.browse(1)
        website_test = Website.create({'name': 'Website Test'})

        # simulate attachment state when editing 2 theme through customize
        custom_url = '/TEST/website/static/src/scss/options/colors/user_theme_color_palette.custom.web.assets_common.scss'
        scss_attachment = Attachment.create({
            'name': custom_url,
            'type': 'binary',
            'mimetype': 'text/scss',
            'datas': '',
            'url': custom_url,
            'website_id': website_default.id
        })
        scss_attachment.copy({'website_id': website_test.id})

        # simulate PDF from ecommerce order
        # Note: it will only have its website_id flag if the website has a domain
        # equal to the current URL (fallback or get_current_website())
        so_attachment = Attachment.create({
            'name': 'SO036.pdf',
            'type': 'binary',
            'mimetype': 'application/pdf',
            'datas': '',
            'website_id': website_test.id
        })

        # avoid sql error on page website_id restrict
        Page.search([('website_id', '=', website_test.id)]).unlink()
        website_test.unlink()
        self.assertEqual(Attachment.search_count([('url', '=', custom_url)]), 1, 'Should not left duplicates when deleting a website')
        self.assertTrue(so_attachment.exists(), 'Most attachment should not be deleted')
        self.assertFalse(so_attachment.website_id, 'Website should be removed')


@odoo.tests.tagged('-at_install', 'post_install')
class TestUiHtmlEditor(odoo.tests.HttpCase):
    def test_html_editor_multiple_templates(self):
        Website = self.env['website']
        View = self.env['ir.ui.view']
        Page = self.env['website.page']
        
        self.generic_view = View.create({
            'name': 'Generic',
            'type': 'qweb',
            'arch': '''
                <div>content</div>
            ''',
            'key': 'test.generic_view',
        })

        self.generic_page = Page.create({
            'view_id': self.generic_view.id,
            'url': '/generic',
        })

        generic_page = Website.viewref('test.generic_view')
        # Use an empty page layout with oe_structure id for this test
        oe_structure_layout = '''
            <t name="Generic" t-name="test.generic_view">
                <t t-call="website.layout">
                    <div id="oe_structure_test_ui" class="oe_structure oe_empty"/>
                </t>
            </t>
        '''
        generic_page.arch = oe_structure_layout
        with self.assertQueryCount(__system__=3198):
            self.start_tour("/", 'html_editor_multiple_templates', login='admin')
        self.assertEqual(View.search_count([('key', '=', 'test.generic_view')]), 2, "homepage view should have been COW'd")
        self.assertTrue(generic_page.arch == oe_structure_layout, "Generic homepage view should be untouched")
        self.assertEqual(len(generic_page.inherit_children_ids.filtered(lambda v: 'oe_structure' in v.name)), 0, "oe_structure view should have been deleted when aboutus was COW")
        specific_page = Website.with_context(website_id=1).viewref('test.generic_view')
        self.assertTrue(specific_page.arch != oe_structure_layout, "Specific homepage view should have been changed")
        self.assertEqual(len(specific_page.inherit_children_ids.filtered(lambda v: 'oe_structure' in v.name)), 1, "oe_structure view should have been created on the specific tree")

    def test_html_editor_scss(self):
        with self.assertQueryCount(__system__=3447):
            self.start_tour("/", 'test_html_editor_scss', login='admin')

@odoo.tests.tagged('-at_install', 'post_install')
class TestUiTranslate(odoo.tests.HttpCase):
    def test_admin_tour_rte_translator(self):
        fr_BE = self.env.ref('base.lang_fr_BE')
        fr_BE.active = True
        self.env.ref('website.default_website').language_ids |= fr_BE
        with self.assertQueryCount(__system__=7113):
            self.start_tour("/", 'rte_translator', login='admin', timeout=120)


@odoo.tests.common.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):

    def test_01_admin_tour_banner(self):
        with self.assertQueryCount(__system__=4157):
            self.start_tour("/", 'banner', login='admin', step_delay=100)

    def test_02_restricted_editor(self):
        self.restricted_editor = self.env['res.users'].create({
            'name': 'Restricted Editor',
            'login': 'restricted',
            'password': 'restricted',
            'groups_id': [(6, 0, [
                    self.ref('base.group_user'),
                    self.ref('website.group_website_publisher')
                ])]
        })
        with self.assertQueryCount(__system__=2114):
            self.start_tour("/", 'restricted_editor', login='restricted')

    def test_03_backend_dashboard(self):
        with self.assertQueryCount(__system__=3089):
            self.start_tour("/", 'backend_dashboard', login='admin')

    def test_04_website_navbar_menu(self):
        website = self.env['website'].search([], limit=1)
        self.env['website.menu'].create({
            'name': 'Test Tour Menu',
            'url': '/test-tour-menu',
            'parent_id': website.menu_id.id,
            'sequence': 0,
            'website_id': website.id,
        })
        with self.assertQueryCount(__system__=1010):
            self.start_tour("/", 'website_navbar_menu')

    def test_05_specific_website_editor(self):
        website_default = self.env['website'].search([], limit=1)
        new_website = self.env['website'].create({'name': 'New Website'})
        website_editor_assets_view = self.env.ref('website.assets_wysiwyg')
        self.env['ir.ui.view'].create({
            'name': 'Editor Extension',
            'type': 'qweb',
            'inherit_id': website_editor_assets_view.id,
            'website_id': new_website.id,
            'arch': """
                <xpath expr="." position="inside">
                    <script type="text/javascript">document.body.dataset.hello = 'world';</script>
                </xpath>
            """,
        })
        with self.assertQueryCount(__system__=1779):
            self.start_tour("/?fw=%s" % website_default.id, "generic_website_editor", login='admin')
        with self.assertQueryCount(__system__=1673):
            self.start_tour("/?fw=%s" % new_website.id, "specific_website_editor", login='admin')

    def test_06_public_user_editor(self):
        website_default = self.env['website'].search([], limit=1)
        website_default.homepage_id.arch = """
            <t name="Homepage" t-name="website.homepage">
                <t t-call="website.layout">
                    <textarea class="o_public_user_editor_test_textarea o_wysiwyg_loader"/>
                </t>
            </t>
        """
        with self.assertQueryCount(__system__=674):
            self.start_tour("/", "public_user_editor", login=None)

    def test_07_snippet_version(self):
        with self.assertQueryCount(__system__=3055):
            self.start_tour("/", 'snippet_version', login='admin')
