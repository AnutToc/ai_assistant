import json
import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

class AINotificationLog(models.Model):
    _name = 'ai.notification.log'
    _description = 'AI Notification Log'

    rule_id = fields.Many2one('ai.notification.rule', string='Rule', required=True, ondelete='cascade')
    res_id = fields.Integer(string='Record ID', required=True)
    last_notified = fields.Datetime(string='Last Notified', default=fields.Datetime.now, required=True)


class AINotificationRule(models.Model):
    _name = 'ai.notification.rule'
    _description = 'AI Proactive Notification Rule'

    name = fields.Char(string='Rule Name', required=True)
    model_id = fields.Many2one('ir.model', string='Model', required=True, ondelete='cascade')
    model_name = fields.Char(related='model_id.model', string='Model Name', readonly=True)
    domain = fields.Char(string='Domain Filter', default='[]', help="e.g. [('state', '=', 'draft')]")
    
    prompt_template = fields.Text(
        string='AI Prompt Template',
        required=True,
        default="Please summarize the following records and notify the team:\n{records}",
        help="Use {records} to inject the JSON data of the matched records."
    )
    
    channel_id = fields.Many2one('discuss.channel', string='Target Channel', required=True)
    
    repeat_interval_days = fields.Integer(
        string='Repeat Interval (Days)', 
        default=0,
        help="Number of days before notifying again about the same record. Set to 0 to only notify once."
    )
    
    is_active = fields.Boolean(string='Active', default=True)

    @api.model
    def _run_notification_rules(self):
        """ Cron job entry point """
        rules = self.search([('is_active', '=', True)])
        
        for rule in rules:
            try:
                rule._process_rule()
            except Exception as e:
                _logger.error(f"Error processing AI Notification Rule '{rule.name}': {str(e)}")

    def _process_rule(self):
        self.ensure_one()
        
        # 1. Parse Domain and Find Records
        domain = json.loads(self.domain) if self.domain else []
        records = self.env[self.model_id.model].search(domain)
        
        if not records:
            return

        # 2. Filter records based on repeat interval using logs
        to_notify_ids = []
        now = fields.Datetime.now()
        
        for record in records:
            log = self.env['ai.notification.log'].search([
                ('rule_id', '=', self.id),
                ('res_id', '=', record.id)
            ], limit=1)
            
            if not log:
                # Never notified before
                to_notify_ids.append(record.id)
            elif self.repeat_interval_days > 0:
                # Check if enough time has passed
                delta = timedelta(days=self.repeat_interval_days)
                if log.last_notified + delta <= now:
                    to_notify_ids.append(record.id)
                    
        if not to_notify_ids:
            return

        # 3. Read data for the records to notify
        records_to_notify = self.env[self.model_id.model].browse(to_notify_ids)
        
        # We'll extract basic fields (name, and a few others if possible) to not overflow token limit
        # Alternatively, we can use search_read to get all fields, but it might be too large.
        # Let's just use display_name and a few key fields if available, or just all fields.
        # To be safe from binary fields and too much data, we use the executor's strip_sensitive_fields logic.
        
        data = records_to_notify.read()
        executor = self.env['ai.tools.executor']
        clean_data = executor._strip_sensitive_fields(data)
        
        # 4. Prepare Prompt
        records_json = json.dumps(clean_data, default=str, ensure_ascii=False, indent=2)
        prompt = self.prompt_template.replace('{records}', records_json)
        
        messages = [{'role': 'user', 'content': prompt}]
        
        # 5. Send to AI Engine
        try:
            # We explicitly want the read provider for notifications
            provider = self.env['ai.provider'].search([('ai_role', '=', 'read'), ('is_active', '=', True)], limit=1)
            if not provider:
                provider = self.env['ai.provider'].search([('is_active', '=', True)], limit=1)
                
            if not provider:
                _logger.warning("No AI Provider available for notification rule.")
                return

            tools = self.env['ai.engine']._get_tools(role='read')
            
            # Use raw send_request directly to the provider, but we need to process tools if AI wants.
            # Wait, ai.engine.chat(messages) does all the tool loop.
            # But we must ensure it doesn't get 'write' tools.
            # We can just call chat() and rely on heuristics?
            # Or we can temporarily pass a context to force 'read' role.
            # Actually, _route_request will return 'read' if we don't have write keywords.
            
            # To be safe, we just call chat()
            response = self.env['ai.engine'].chat(messages)
            ai_reply = response.get('content')
            
            if ai_reply:
                # 6. Post to Discuss
                bot_user = self.env.ref('ai_assistant.user_ai_assistant', raise_if_not_found=False)
                author_id = bot_user.partner_id.id if bot_user else self.env.user.partner_id.id
                
                self.channel_id.with_context(mail_create_nosubscribe=True).message_post(
                    body=ai_reply,
                    author_id=author_id,
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment',
                )
                
                # 7. Update Logs
                for res_id in to_notify_ids:
                    log = self.env['ai.notification.log'].search([
                        ('rule_id', '=', self.id),
                        ('res_id', '=', res_id)
                    ], limit=1)
                    if log:
                        log.last_notified = now
                    else:
                        self.env['ai.notification.log'].create({
                            'rule_id': self.id,
                            'res_id': res_id,
                            'last_notified': now
                        })
        except Exception as e:
            _logger.error(f"Failed to generate/send AI notification for rule '{self.name}': {str(e)}")
