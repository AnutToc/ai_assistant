from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ai_enable_write_tools = fields.Boolean(
        string="Enable AI Write Actions",
        config_parameter='odoo_ai_assistant.enable_write_tools',
        help="Allow AI to create, update, delete records. Requires Developer Mode."
    )
