{
    'name': 'AI Assistant',
    'version': '1.0.0',
    'category': 'Productivity',
    'summary': 'Provider-Agnostic AI Assistant integrated into Odoo',
    'description': 'AI Gateway for Odoo supporting OpenAI, Gemini, and Anthropic protocols.',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/ai_provider_views.xml',
        'views/res_config_settings_views.xml',
        'views/menuitems.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ai_assistant/static/src/components/floating_widget/floating_widget.js',
            'ai_assistant/static/src/components/floating_widget/floating_widget.xml',
            'ai_assistant/static/src/components/floating_widget/floating_widget.scss',
        ],
    },
    'installable': True,
    'post_init_hook': 'post_init_hook',
    'application': True,
    'license': 'LGPL-3',
}
