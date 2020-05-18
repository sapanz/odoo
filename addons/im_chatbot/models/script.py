# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Script(models.Model):
    _name = "im_chatbot.script"
    _description = "Message from the chatbot"
    _order = "sequence, id"

    message_ids = fields.One2many("mail.message", "script_id")

    name = fields.Char(string="Message")
    sequence = fields.Integer(string="Sequence", default=10)
    answer_type = fields.Selection(
        [("selection", "Selection"), ("input", "User input")], required=True
    )
    chatbot_id = fields.Many2one("im_chatbot.chatbot", index=True)
    answer_ids = fields.Many2many("im_chatbot.answer")
