from odoo import models, fields

class AIProvider(models.Model):
    _name = 'ai.provider'
    _description = 'AI Provider Configuration'

    name = fields.Char(string='Provider Name', required=True, help="e.g., Qwen Local, OpenAI GPT-4o")
    protocol_type = fields.Selection([
        ('openai_compatible', 'OpenAI Compatible (Qwen, DeepSeek, GPT, Ollama)'),
        ('gemini_native', 'Google Gemini Native'),
        ('anthropic_native', 'Anthropic Claude Native')
    ], string='Protocol Type', required=True, default='openai_compatible')
    
    api_base_url = fields.Char(string='Base URL', help="Leave empty for default provider URL. Useful for Ollama/vLLM.")
    api_key = fields.Char(string='API Key')
    model_name = fields.Char(string='Model Name', required=True, help="e.g., qwen-max, gpt-4o, gemini-1.5-pro")
    
    is_active = fields.Boolean(string='Active', default=False, help="Only one provider should be active at a time.")
