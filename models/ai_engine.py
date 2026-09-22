import json
import logging
from markupsafe import Markup

from odoo import api, models
from odoo.exceptions import UserError

class AIEngine(models.AbstractModel):
    _name = 'ai.engine'
    _description = 'AI Core Router and Engine'

    @api.model
    def _route_request(self, messages):
        """ Determine which AI role to use based on message heuristics. """
        # 1. Check for images or documents in any user message
        for msg in messages:
            if msg.get('role') == 'user' and (msg.get('images') or msg.get('documents')):
                return 'vision'
        
        # 2. Check for write keywords in the latest user message
        icp = self.env['ir.config_parameter'].sudo()
        keywords_str = icp.get_param('odoo_ai_assistant.write_keywords', 'create,add,update,delete,remove,new')
        write_keywords = [k.strip().lower() for k in keywords_str.split(',') if k.strip()]
        latest_user_msg = next((m.get('content', '').lower() for m in reversed(messages) if m.get('role') == 'user'), "")
        if any(kw in latest_user_msg for kw in write_keywords):
            return 'write'
            
        # 3. Default to read
        return 'read'

    @api.model
    def chat(self, messages, channel=None, ai_msg_ids=None):
        """ Main entry point for Chat UI to send messages. Handles tool calling loops automatically. """
        role = self._route_request(messages)
        
        # Find provider for this role
        provider = self.env['ai.provider'].search([('ai_role', '=', role), ('is_active', '=', True)], limit=1)
        if not provider:
            # Fallback to read provider, or any active provider
            provider = self.env['ai.provider'].search([('ai_role', '=', 'read'), ('is_active', '=', True)], limit=1)
            if not provider:
                provider = self.env['ai.provider'].search([('is_active', '=', True)], limit=1)
                
        if not provider:
            raise UserError(f"No active AI Provider configured for role '{role}' and no fallback available.")

        tools = self._get_tools(role)

        
        icp = self.env['ir.config_parameter'].sudo()
        max_turns = int(icp.get_param('odoo_ai_assistant.max_tool_turns', 10))
        
        # --- INJECT STRICT SYSTEM PROMPT (Multi-Language) ---
        system_instruction = self._get_system_prompt()
        if messages and messages[0].get('role') != 'system':
            messages.insert(0, {'role': 'system', 'content': system_instruction})
        elif messages and messages[0].get('role') == 'system':
            messages[0]['content'] = system_instruction + "\n\n" + messages[0]['content']
            
        for turn in range(max_turns):
            # 1. Send Request
            if provider.protocol_type == 'openai_compatible':
                raw_response = self.env['ai.adapter.openai'].send_request(provider, messages, tools=tools)
                parsed_res = self._process_openai_response(raw_response)
            elif provider.protocol_type == 'gemini_native':
                raw_response = self.env['ai.adapter.gemini'].send_request(provider, messages, tools=tools)
                parsed_res = self._process_gemini_response(raw_response)
            elif provider.protocol_type == 'anthropic_native':
                raw_response = self.env['ai.adapter.anthropic'].send_request(provider, messages, tools=tools)
                parsed_res = self._process_anthropic_response(raw_response)
            else:
                raise UserError(f"Unknown Protocol Type: {provider.protocol_type}")

            # 2. Handle Text Response
            if parsed_res.get('type') == 'text':
                return {'content': parsed_res.get('content')}

            # 3. Handle Tool Calls
            elif parsed_res.get('type') == 'tool_call':
                tool_calls = parsed_res.get('tool_calls', [])
                thought = parsed_res.get('content', '')
                
                if channel:
                    thought_html = ""
                    if thought:
                        thought_html += f"<div><i>🧠 {thought}</i></div>"
                    for tc in tool_calls:
                        func_name = tc.get('name') if provider.protocol_type != 'openai_compatible' else tc.get('function', {}).get('name')
                        thought_html += f"<div class='text-muted'>🛠️ <i>กำลังใช้งานเครื่องมือ: {func_name}...</i></div>"
                    if thought_html:
                        if channel:
                            with self.env.registry.cursor() as new_cr:
                                env = api.Environment(new_cr, self.env.uid, self.env.context)
                                channel_new_cr = env['discuss.channel'].browse(channel.id)
                                bot_user = env.ref('ai_assistant.user_ai_assistant', raise_if_not_found=False)
                                author_id = bot_user.partner_id.id if bot_user else env.user.partner_id.id
                                
                                msg = channel_new_cr.with_context(mail_create_nosubscribe=True).message_post(
                                    body=Markup(thought_html),
                                    author_id=author_id,
                                    message_type='comment',
                                    subtype_xmlid='mail.mt_comment',
                                )
                                if isinstance(ai_msg_ids, list):
                                    ai_msg_ids.append(msg.id)

                if provider.protocol_type == 'openai_compatible':
                    # OpenAI API requires sending the assistant's content back along with the tool calls
                    messages.append({'role': 'assistant', 'content': thought or None, 'tool_calls': tool_calls})

                for tc in tool_calls:
                    # Extract standard or OpenAI format
                    if provider.protocol_type == 'openai_compatible':
                        func_name = tc.get('function', {}).get('name')
                        try:
                            func_args = json.loads(tc.get('function', {}).get('arguments', '{}'))
                        except:
                            func_args = {}
                        tool_id = tc.get('id')
                    else:
                        func_name = tc.get('name')
                        func_args = tc.get('args', {})
                        tool_id = tc.get('id', 'call_123')

                    # Execute Odoo Tool (e.g. search_records)
                    result = self.env['ai.tools.executor'].execute_tool(func_name, func_args)
                    result_str = json.dumps(result, default=str)

                    # Append result to messages
                    if provider.protocol_type == 'openai_compatible':
                        messages.append({'role': 'tool', 'tool_call_id': tool_id, 'name': func_name, 'content': result_str})
                    else:
                        messages.append({'role': 'user', 'content': f"Tool result for {func_name}: {result_str}"})

        return {'content': "System: Task stopped because it exceeded maximum tool execution turns."}

    @api.model
    def _get_tools(self, role='read'):
        """ Load standard tools schemas. """
        tools = self.env['ai.tools.schema'].get_read_tools()
        
        if role == 'write':
            icp = self.env['ir.config_parameter'].sudo()
            if icp.get_param('odoo_ai_assistant.enable_create_tools') == 'True':
                tools.extend(self.env['ai.tools.schema'].get_create_tools())
            if icp.get_param('odoo_ai_assistant.enable_update_tools') == 'True':
                tools.extend(self.env['ai.tools.schema'].get_update_tools())
            if icp.get_param('odoo_ai_assistant.enable_delete_tools') == 'True':
                tools.extend(self.env['ai.tools.schema'].get_delete_tools())
        return tools

    @api.model
    def _get_system_prompt(self):
        """ Generate system prompt based on the current user's language. """
        lang = self.env.user.lang or 'en_US'
        lang_prefix = lang.split('_')[0]  # e.g., 'th', 'zh', 'ja', 'ko', 'en'

        # Base rules (always in English for AI reliability)
        base_rules = (
            "CRITICAL RULES: "
            "1. NEVER guess field names for Odoo models. Odoo schemas change between versions. "
            "2. ALWAYS use the 'get_fields' tool to inspect a model before using 'search_records'. "
            "3. If a tool execution fails with 'Invalid field', immediately use 'get_fields' to find the correct field name before retrying. "
            "4. When you receive an image (invoice, receipt, purchase order, etc.), extract ALL relevant data "
            "(vendor/customer name, date, line items, amounts, tax, total) and use the appropriate tools "
            "(get_fields then create_record) to create the corresponding record in Odoo. "
            "Always confirm with the user what you extracted before creating records."
        )

        prompts = {
            'th': (
                "คุณคือ AI Assistant ผู้เชี่ยวชาญระบบ Odoo ERP "
                "ตอบคำถามเป็นภาษาไทยเสมอ ยกเว้นชื่อ field และ model ให้ใช้ชื่อจริงในระบบ "
            ),
            'zh': (
                "你是一位专业的 Odoo ERP AI 助手。"
                "请始终使用中文回答问题，但 field 和 model 名称请使用系统原名。"
            ),
            'ja': (
                "あなたはOdoo ERPの専門AIアシスタントです。"
                "常に日本語で回答してください。ただし、フィールド名やモデル名はシステムの原名を使用してください。"
            ),
            'ko': (
                "당신은 Odoo ERP 전문 AI 어시스턴트입니다. "
                "항상 한국어로 답변해 주세요. 단, 필드명과 모델명은 시스템 원래 이름을 사용하세요. "
            ),
        }

        default_prompt = "You are an expert Odoo ERP AI Assistant. "
        persona = prompts.get(lang_prefix, default_prompt)
        
        icp = self.env['ir.config_parameter'].sudo()
        custom_prompt = icp.get_param('odoo_ai_assistant.custom_system_prompt', '')
        
        final_prompt = persona + base_rules
        if custom_prompt:
            final_prompt += f" {custom_prompt}"
            
        return final_prompt

    @api.model
    def _process_openai_response(self, response):
        message = response.get('choices', [{}])[0].get('message', {})
        if message.get('tool_calls'):
            return {
                'type': 'tool_call', 
                'tool_calls': message.get('tool_calls'),
                'content': message.get('content', '')
            }
        return {'type': 'text', 'content': message.get('content', '')}
        
    @api.model
    def _process_gemini_response(self, response):
        parts = response.get('candidates', [{}])[0].get('content', {}).get('parts', [])
        if not parts:
            return {'type': 'text', 'content': "No content returned from Gemini."}
            
        thought_texts = []
        for part in parts:
            if 'text' in part:
                thought_texts.append(part['text'])
            if 'functionCall' in part:
                # Format to standard tool call format
                return {
                    'type': 'tool_call', 
                    'tool_calls': [{'name': part['functionCall']['name'], 'args': part['functionCall'].get('args', {})}],
                    'content': ''.join(thought_texts)
                }
        
        return {'type': 'text', 'content': ''.join(thought_texts)}
        
    @api.model
    def _process_anthropic_response(self, response):
        content_blocks = response.get('content', [])
        thought_texts = []
        for block in content_blocks:
            if block.get('type') == 'text':
                thought_texts.append(block.get('text', ''))
            if block.get('type') == 'tool_use':
                return {
                    'type': 'tool_call', 
                    'tool_calls': [{'name': block['name'], 'args': block['input']}],
                    'content': ''.join(thought_texts)
                }
                
        return {'type': 'text', 'content': ''.join(thought_texts)}

    @api.model
    def _setup_ai_user(self):
        """ Dynamically creates the AI user to avoid XML database constraints on res.partner """
        partner = self.env.ref('ai_assistant.partner_ai_assistant', raise_if_not_found=False)
        if not partner:
            vals = {'name': 'AI Assistant', 'email': 'ai@odoo.local', 'tz': 'UTC', 'active': True}
            
            # Handle strict database constraints from other installed modules dynamically
            if 'autopost_bills' in self.env['res.partner']._fields:
                field_type = self.env['res.partner']._fields['autopost_bills'].type
                if field_type == 'selection':
                    vals['autopost_bills'] = 'never'
                elif field_type == 'boolean':
                    vals['autopost_bills'] = False
                    
            partner = self.env['res.partner'].sudo().create(vals)
            self.env['ir.model.data'].sudo().create({
                'name': 'partner_ai_assistant', 
                'module': 'ai_assistant', 
                'model': 'res.partner', 
                'res_id': partner.id, 
                'noupdate': True
            })
            
        user = self.env.ref('ai_assistant.user_ai_assistant', raise_if_not_found=False)
        if not user:
            user_vals = {
                'partner_id': partner.id,
                'name': 'AI Assistant',
                'login': 'ai_assistant',
                'active': True,
                'groups_id': [(6, 0, [self.env.ref('base.group_user').id])]
            }
            user = self.env['res.users'].sudo().create(user_vals)
            self.env['ir.model.data'].sudo().create({
                'name': 'user_ai_assistant', 
                'module': 'ai_assistant', 
                'model': 'res.users', 
                'res_id': user.id, 
                'noupdate': True
            })
