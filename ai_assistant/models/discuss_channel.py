from odoo import models, api
import logging
import re

# _logger = logging.getLogger(__name__)

def _clean_html(html_str):
    if not html_str:
        return ""
    # Replace HTML tags with space, then clean up extra spaces
    text = re.sub(r'<[^>]+>', ' ', str(html_str))
    return ' '.join(text.split())

class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        # 1. Post the user's message first
        message = super(DiscussChannel, self).message_post(**kwargs)
        
        try:
            # 2. Find Bot Identity
            bot_user = self.env.ref('ai_assistant.user_ai_assistant', raise_if_not_found=False)
            if not bot_user:
                bot_user = self.env['res.users'].sudo().search([('login', '=', 'ai_assistant')], limit=1)
                
            if not bot_user:
                return message
                
            bot_partner = bot_user.partner_id
            
            # 3. Check if bot needs to reply
            if bot_partner and message.author_id and message.author_id != bot_partner:
                
                is_member = False
                if hasattr(self, 'channel_member_ids'):
                    is_member = bot_partner.id in self.channel_member_ids.mapped('partner_id').ids
                elif hasattr(self, 'channel_partner_ids'):
                    is_member = bot_partner.id in self.channel_partner_ids.ids
                    
                is_dm = self.channel_type == 'chat' and is_member
                is_mentioned = bot_partner.id in message.partner_ids.ids
                
                if is_dm or is_mentioned:
                    # _logger.info("AI Assistant: Gathering conversation history...")
                    
                    # 4. MEMORY SYSTEM: Fetch last 15 messages from THIS channel
                    domain = [
                        ('model', '=', 'discuss.channel'),
                        ('res_id', '=', self.id),
                        ('message_type', '=', 'comment'),
                        ('body', '!=', False)
                    ]
                    # Get newest first, limit 15
                    history_msgs = self.env['mail.message'].sudo().search(domain, order='id desc', limit=15)
                    
                    # Reverse so oldest is first, newest is last for the AI prompt
                    history_msgs = history_msgs.sorted(key=lambda m: m.id)
                    
                    messages_payload = []
                    for msg in history_msgs:
                        role = 'assistant' if msg.author_id == bot_partner else 'user'
                        clean_text = _clean_html(msg.body)
                        if clean_text:
                            messages_payload.append({'role': role, 'content': clean_text})
                            
                    # Fallback just in case history fails
                    if not messages_payload:
                        messages_payload = [{'role': 'user', 'content': _clean_html(message.body)}]
                    
                    # 5. Send to AI Engine
                    try:
                        response = self.env['ai.engine'].chat(messages_payload)
                        reply_content = response.get('content', "No response generated.")
                    except Exception as e:
                        reply_content = f"System Error: {str(e)}"
                        # _logger.exception("AI Assistant API Error")
                    
                    # 6. Post AI Reply
                    self.with_context(mail_create_nosubscribe=True).message_post(
                        body=reply_content,
                        author_id=bot_partner.id,
                        message_type='comment',
                        subtype_xmlid='mail.mt_comment',
                    )
        except Exception as e:
            # _logger.exception("AI Assistant Interceptor crashed")
            pass
            
        return message
