from odoo import models, fields, api

class AIChatThread(models.Model):
    _name = 'ai.chat.thread'
    _description = 'AI Chat Thread'
    _order = 'write_date desc'

    name = fields.Char(string='Title', default='New Chat')
    user_id = fields.Many2one('res.users', string='Owner', default=lambda self: self.env.user, required=True, ondelete='cascade')
    message_ids = fields.One2many('ai.chat.message', 'thread_id', string='Messages')
    active = fields.Boolean(default=True)

class AIChatMessage(models.Model):
    _name = 'ai.chat.message'
    _description = 'AI Chat Message'
    _order = 'sequence asc, id asc'

    thread_id = fields.Many2one('ai.chat.thread', string='Thread', required=True, ondelete='cascade')
    role = fields.Selection([
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
        ('tool', 'Tool')
    ], required=True)
    content = fields.Text(string='Content')
    tool_calls = fields.Text(string='Tool Calls (JSON)')
    tool_results = fields.Text(string='Tool Results (JSON)')
    thinking_steps = fields.Text(string='Thinking Steps (JSON)')
    sequence = fields.Integer(default=10)
