# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import tests

from odoo import api, SUPERUSER_ID

def _clean_sponsor_image_attachments(cr, registry):
    """ Delete old attachment from image_128 on event.sponsor. The image_128 is, since this module
    is installed, a related non stored field, and should not have attachment anymore. """

    env = api.Environment(cr, SUPERUSER_ID, {})

    sponsor_attachments = env['ir.attachment'].sudo().search([
        ('res_model', '=', 'event.sponsor'), ('res_field', '=', 'image_128')
    ])

    sponsor_attachments.unlink()
