from odoo import api, SUPERUSER_ID

def post_init_hook(cr, registry):
    """
    Runs automatically after the module is installed.
    Safely creates the AI Assistant user and partner.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})

    partner = env.ref('ai_assistant.partner_ai_assistant', raise_if_not_found=False)
    if not partner:
        vals = {'name': 'AI Assistant', 'email': 'ai@odoo.local', 'tz': 'UTC', 'active': True}
        partner = env['res.partner'].sudo().create(vals)
        env['ir.model.data'].sudo().create({
            'name': 'partner_ai_assistant',
            'module': 'ai_assistant',
            'model': 'res.partner',
            'res_id': partner.id,
            'noupdate': True
        })

    user = env.ref('ai_assistant.user_ai_assistant', raise_if_not_found=False)
    if not user:
        user_vals = {
            'partner_id': partner.id,
            'name': 'AI Assistant',
            'login': 'ai_assistant',
            'active': True,
            'groups_id': [(6, 0, [env.ref('base.group_user').id])]
        }
        user = env['res.users'].sudo().create(user_vals)
        env['ir.model.data'].sudo().create({
            'name': 'user_ai_assistant',
            'module': 'ai_assistant',
            'model': 'res.users',
            'res_id': user.id,
            'noupdate': True
        })
