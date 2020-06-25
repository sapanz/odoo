# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_event.controllers.main import WebsiteEventController
from odoo.http import request


class WebsiteEventOnlineController(WebsiteEventController):

    def _create_attendees_from_registration_post(self, event, registration_data):
        """ Override registration data to try to set a visitor (from request) and
        a partner (if visitor linked to a user for example). Purpose is to gather
        as much informations as possible, notably to ease future communications. """
        visitor_sudo = request.env['website.visitor']._get_visitor_from_request(force_create=True)
        visitor_sudo._update_visitor_last_visit()

        if visitor_sudo:
            for info in registration_data:
                info['visitor_id'] = visitor_sudo.id
                if not info.get('partner_id') and visitor_sudo.partner_id:
                    info['partner_id'] = visitor_sudo.partner_id.id

        return super(WebsiteEventOnlineController, self)._create_attendees_from_registration_post(event, registration_data)
