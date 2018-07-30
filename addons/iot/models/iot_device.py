from odoo import api, fields, models, exceptions


# ----------------------------------------------------------
# Models for client
# ----------------------------------------------------------
class IotDevice(models.Model):
    _name = 'iot.device'

    iot_id = fields.Many2one('iot.box', required = True)
    name = fields.Char('Name')
    identifier = fields.Char(string='Serial Number')
    last_message_date = fields.Datetime('Last Message', compute="_compute_last_message")
    device_type = fields.Selection([
        ('device', 'Device'),
        ('printer', 'Printer'),
        ('camera', 'Camera'),
        ('pedal', 'Pedal')
        ], default='device',
        help="Type of device.")
    device_connection = fields.Selection([
        ('network', 'Network'),
        ('direct', 'USB'),
        ('bluetooht', 'Bluetooht')
        ],
        help="Type of connection.")

    def _compute_last_message(self):
        for device in self:
            self.last_message_date = self.env['iot.message'].search([('device_id', '=', device.id)],
                                                                    order='create_date desc', limit=1).create_date

    @api.depends('iot_id.name', 'name')
    def name_get(self):
        return [(i.id, i.iot_id.name + " " + i.name) for i in self]