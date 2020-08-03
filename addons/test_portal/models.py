from odoo import models


class NotPortal(models.Model):
    _name = _description = 'test_portal.not_portal'

    def _compute_access_url(self):
        super()._compute_access_url()
        self.access_url = '/my/thing2'

class Portal(models.Model):
    _name = _description = 'test_portal.portal'
    _inherit = 'portal.mixin'

    def _compute_access_url(self):
        super()._compute_access_url()
        self.access_url = '/my/thing'
