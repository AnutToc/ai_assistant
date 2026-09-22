from odoo import fields, models

class AIPromptTemplate(models.Model):
    _name = 'ai.prompt.template'
    _description = 'AI Prompt Template'
    _order = 'category, sequence, id'

    name = fields.Char(
        string='Template Name',
        required=True,
        help="e.g., Summarize today's sales, Search for customers"
    )
    description = fields.Text(
        string='Description',
        help="Short description of what this template does."
    )
    prompt_text = fields.Text(
        string='Prompt',
        required=True,
        help="The prompt text that will be sent to the AI when this template is used."
    )
    category = fields.Selection([
        ('sales', 'Sales'),
        ('purchase', 'Purchase'),
        ('inventory', 'Inventory'),
        ('accounting', 'Accounting'),
        ('hr', 'Human Resources'),
        ('crm', 'CRM'),
        ('general', 'General'),
    ], string='Category', default='general', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    is_active = fields.Boolean(string='Active', default=True)
