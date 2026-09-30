import logging
import re
import threading
import odoo
from odoo import api, models

SUPPORTED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
SUPPORTED_DOCUMENT_TYPES = ['application/pdf']

def _run_ai_async(db_name, uid, context, channel_id, messages_payload, bot_partner_id):
    import time

    def run_with_retry(func):
        for attempt in range(5):
            try:
                registry = odoo.registry(db_name)
                with registry.cursor() as cr:
                    env = api.Environment(cr, uid, context)
                    return func(env)
            except Exception as e:
                err_msg = str(e)
                if 'concurrent update' in err_msg or 'could not serialize access' in err_msg:
                    if attempt < 4:
                        time.sleep(0.5 + (attempt * 0.5))
                        continue
                raise e

    try:
        # 1. Post Placeholder
        def post_placeholder(env):
            channel = env['mail.channel'].browse(channel_id)
            msg = channel.with_context(mail_create_nosubscribe=True).message_post(
                body="<i>⏳ AI Assistant กำลังประมวลผล...</i>",
                author_id=bot_partner_id,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )
            return msg.id

        placeholder_id = run_with_retry(post_placeholder)
        ai_msg_ids = [placeholder_id]

        # 2. Call AI Engine
        registry = odoo.registry(db_name)
        with registry.cursor() as cr:
            env = api.Environment(cr, uid, context)
            channel = env['mail.channel'].browse(channel_id)
            try:
                response = env['ai.engine'].chat(messages_payload, channel=channel, ai_msg_ids=ai_msg_ids)
                reply_content = response.get('content', "No response generated.")
            except Exception as e:
                reply_content = "System Error: %s" % str(e)

        if len(ai_msg_ids) > 1:
            time.sleep(2)

        # 3. Post Final Reply
        def post_final(env):
            channel = env['mail.channel'].browse(channel_id)
            channel.with_context(mail_create_nosubscribe=True).message_post(
                body=reply_content,
                author_id=bot_partner_id,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )
        run_with_retry(post_final)

        # 4. Delete Placeholder
        def delete_placeholder(env):
            env['mail.message'].sudo().browse(ai_msg_ids).unlink()
        run_with_retry(delete_placeholder)

    except Exception as e:
        logging.getLogger(__name__).error("Async AI Error: %s", str(e))


def _clean_html(html_str):
    if not html_str:
        return ""
    text = re.sub(r'<[^>]+>', ' ', str(html_str))
    return ' '.join(text.split())


class MailChannel(models.Model):
    _inherit = 'mail.channel'

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        message = super(MailChannel, self).message_post(**kwargs)

        try:
            bot_user = self.env.ref('ai_assistant.user_ai_assistant', raise_if_not_found=False)
            if not bot_user:
                bot_user = self.env['res.users'].sudo().search([('login', '=', 'ai_assistant')], limit=1)

            if not bot_user:
                return message

            bot_partner = bot_user.partner_id

            if bot_partner and message.author_id and message.author_id != bot_partner:
                # Odoo 13: ใช้ channel_partner_ids (M2M โดยตรง)
                is_member = bot_partner.id in self.channel_partner_ids.ids

                is_dm = self.channel_type == 'chat' and is_member
                is_mentioned = bot_partner.id in message.partner_ids.ids

                if is_dm or is_mentioned:
                    user_clean_text = _clean_html(message.body).strip()
                    if user_clean_text.lower() in ['/reset', '/clear', '/ล้าง']:
                        domain = [
                            ('model', '=', 'mail.channel'),
                            ('res_id', '=', self.id),
                            ('id', '!=', message.id),
                        ]
                        self.env['mail.message'].sudo().search(domain).unlink()

                        self.with_context(mail_create_nosubscribe=True).message_post(
                            body="🧹 <i>ล้างประวัติการสนทนาเรียบร้อยแล้ว (Session Reset) พร้อมรับคำสั่งใหม่ครับ!</i>",
                            author_id=bot_partner.id,
                            message_type='comment',
                            subtype_xmlid='mail.mt_comment',
                        )
                        return message

                    # MEMORY SYSTEM: Fetch messages from THIS channel
                    domain = [
                        ('model', '=', 'mail.channel'),
                        ('res_id', '=', self.id),
                        ('message_type', '=', 'comment'),
                        ('body', '!=', False)
                    ]

                    icp = self.env['ir.config_parameter'].sudo()
                    max_history = int(icp.get_param('odoo_ai_assistant.max_history_messages', 15))

                    history_msgs = self.env['mail.message'].sudo().search(domain, order='id desc', limit=max_history)
                    history_msgs = history_msgs.sorted(key=lambda m: m.id)

                    messages_payload = []
                    for msg in history_msgs:
                        role = 'assistant' if msg.author_id == bot_partner else 'user'
                        clean_text = _clean_html(msg.body)
                        if not clean_text and not msg.attachment_ids:
                            continue

                        msg_data = {'role': role, 'content': clean_text or ''}

                        if role == 'user' and msg.attachment_ids:
                            images = []
                            for att in msg.attachment_ids:
                                if att.mimetype in SUPPORTED_IMAGE_TYPES and att.datas:
                                    images.append({
                                        'mime_type': att.mimetype,
                                        'base64': att.datas.decode('utf-8') if isinstance(att.datas, bytes) else att.datas,
                                        'name': att.name or 'image',
                                    })
                            if images:
                                msg_data['images'] = images
                                if not msg_data['content']:
                                    msg_data['content'] = 'Please analyze the attached image(s).'

                        if role == 'user' and msg.attachment_ids:
                            documents = []
                            for att in msg.attachment_ids:
                                if att.mimetype in SUPPORTED_DOCUMENT_TYPES and att.datas:
                                    documents.append({
                                        'mime_type': att.mimetype,
                                        'base64': att.datas.decode('utf-8') if isinstance(att.datas, bytes) else att.datas,
                                        'name': att.name or 'document.pdf',
                                    })
                            if documents:
                                msg_data['documents'] = documents
                                if not msg_data['content']:
                                    msg_data['content'] = 'Please analyze the attached document(s).'

                        messages_payload.append(msg_data)

                    if not messages_payload:
                        messages_payload = [{'role': 'user', 'content': _clean_html(message.body)}]

                    def start_ai_thread():
                        t = threading.Thread(
                            target=_run_ai_async,
                            args=(self.env.cr.dbname, self.env.uid, self.env.context, self.id, messages_payload, bot_partner.id)
                        )
                        t.start()

                    self.env.cr.postcommit.add(start_ai_thread)
        except Exception as e:
            pass

        return message
