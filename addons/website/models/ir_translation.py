# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class IrModule(models.Model):
    _inherit = "ir.module.module"

    def _update_translations(self, filter_lang=None, overwrite=False):
        """ Add missing website specific translation """
        res = super()._update_translations(filter_lang=filter_lang, overwrite=overwrite)

        if not filter_lang or not self:
            return res

        if overwrite:
            conflict_clause = """
                   ON CONFLICT {}
                   DO UPDATE SET (name, lang, res_id, src, type, value, module, state, comments) =
                       (EXCLUDED.name, EXCLUDED.lang, EXCLUDED.res_id, EXCLUDED.src, EXCLUDED.type,
                        EXCLUDED.value, EXCLUDED.module, EXCLUDED.state, EXCLUDED.comments)
                WHERE EXCLUDED.value IS NOT NULL AND EXCLUDED.value != ''
            """;
        else:
            conflict_clause = " ON CONFLICT DO NOTHING"

        # Add specific view translations
        self.env.cr.execute("""
            INSERT INTO ir_translation(name, lang, res_id, src, type, value, module, state, comments)
            SELECT DISTINCT ON (specific.id, t.lang, md5(src)) t.name, t.lang, specific.id, t.src, t.type, t.value, t.module, t.state, t.comments
              FROM ir_translation t
             INNER JOIN ir_ui_view generic
                ON t.type = 'model_terms' AND t.name = 'ir.ui.view,arch_db' AND t.res_id = generic.id
             INNER JOIN ir_ui_view specific
                ON generic.key = specific.key
             WHERE t.lang IN %s and t.module IN %s
               AND generic.website_id IS NULL AND generic.type = 'qweb'
               AND specific.website_id IS NOT NULL""" + conflict_clause.format(
                   "(type, name, lang, res_id, md5(src))"
        ), (tuple(filter_lang), tuple(self.mapped("name"))))

        default_menu = self.env.ref('website.main_menu', raise_if_not_found=False)
        if not default_menu:
            return res

        # Add specific menu translations
        self.env.cr.execute("""
            INSERT INTO ir_translation(name, lang, res_id, src, type, value, module, state, comments)
            SELECT DISTINCT ON (s_menu.id, t.lang) t.name, t.lang, s_menu.id, t.src, t.type, t.value, t.module, t.state, t.comments
              FROM ir_translation t
             INNER JOIN website_menu o_menu
                ON t.type = 'model' AND t.name = 'website.menu,name' AND t.res_id = o_menu.id
             INNER JOIN website_menu s_menu
                ON o_menu.name = s_menu.name AND o_menu.url = s_menu.url
             INNER JOIN website_menu root_menu
                ON s_menu.parent_id = root_menu.id AND root_menu.parent_id IS NULL
             WHERE t.lang IN %s and t.module IN %s
               AND o_menu.website_id IS NULL AND o_menu.parent_id = %s
               AND s_menu.website_id IS NOT NULL""" + conflict_clause.format(
                   "(type, lang, name, res_id) WHERE type = 'model'"
        ), (tuple(filter_lang), tuple(self.mapped("name")), default_menu.id))

        return res
