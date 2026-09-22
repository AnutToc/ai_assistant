from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ai_enable_create_tools = fields.Boolean(
        string="Enable AI Create Actions",
        config_parameter='odoo_ai_assistant.enable_create_tools',
        help="Allow AI to create new records."
    )
    ai_enable_update_tools = fields.Boolean(
        string="Enable AI Update Actions",
        config_parameter='odoo_ai_assistant.enable_update_tools',
        help="Allow AI to update existing records."
    )
    ai_enable_delete_tools = fields.Boolean(
        string="Enable AI Delete Actions",
        config_parameter='odoo_ai_assistant.enable_delete_tools',
        help="Allow AI to delete existing records."
    )
    
    ai_max_history_messages = fields.Integer(
        string="Max History Messages",
        config_parameter='odoo_ai_assistant.max_history_messages',
        default=15,
        help="Number of previous messages to remember in the conversation context."
    )
    
    ai_max_tool_turns = fields.Integer(
        string="Max Tool Execution Turns",
        config_parameter='odoo_ai_assistant.max_tool_turns',
        default=10,
        help="Maximum number of consecutive tool calls allowed per request to prevent infinite loops."
    )
    
    ai_write_keywords = fields.Char(
        string="Write Action Keywords",
        config_parameter='odoo_ai_assistant.write_keywords',
        default="สร้าง,เพิ่ม,ลบ,แก้ไข,อัพเดท,create,add,update,delete,remove,new",
        help="Comma-separated list of keywords to trigger the Write AI Provider."
    )
    
    ai_custom_system_prompt = fields.Text(
        string="Custom System Prompt",
        help="Additional instructions to append to the system prompt globally."
    )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(
            ai_custom_system_prompt=self.env['ir.config_parameter'].sudo().get_param('odoo_ai_assistant.custom_system_prompt', default='')
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('odoo_ai_assistant.custom_system_prompt', self.ai_custom_system_prompt or '')
