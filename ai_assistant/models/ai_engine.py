import logging
from odoo import models, api
from odoo.exceptions import UserError

class AIEngine(models.AbstractModel):
    _name = 'ai.engine'
    _description = 'AI Core Router and Engine'

    @api.model
    def chat(self, messages):
        """ Main entry point for Chat UI to send messages. Handles tool calling loops automatically. """
        provider = self.env['ai.provider'].search([('is_active', '=', True)], limit=1)
        if not provider:
            raise UserError("No active AI Provider configured.")

        tools = self._get_tools()
        import json

        
        max_turns = 5
        
        # --- INJECT STRICT SYSTEM PROMPT ---
        system_instruction = (
            "You are an expert Odoo ERP AI Assistant. "
            "CRITICAL RULES: "
            "1. NEVER guess field names for Odoo models. Odoo schemas change between versions. "
            "2. ALWAYS use the 'get_fields' tool to inspect a model before using 'search_records'. "
            "3. If a tool execution fails with 'Invalid field', immediately use 'get_fields' to find the correct field name before retrying."
        )
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
                
                if provider.protocol_type == 'openai_compatible':
                    messages.append({'role': 'assistant', 'content': None, 'tool_calls': tool_calls})

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
                    _logger.info("=========================================")
                    _logger.info(f"AI TURN {turn+1}: Calling Tool -> {func_name}")
                    _logger.info(f"ARGS: {func_args}")
                    
                    # Execute Odoo Tool (e.g. search_records)
                    result = self.env['ai.tools.executor'].execute_tool(func_name, func_args)
                    
                    _logger.info(f"RESULT (Snippet): {str(result)[:300]}")
                    _logger.info("=========================================")
                    result_str = json.dumps(result, default=str)

                    # Append result to messages
                    if provider.protocol_type == 'openai_compatible':
                        messages.append({'role': 'tool', 'tool_call_id': tool_id, 'name': func_name, 'content': result_str})
                    else:
                        messages.append({'role': 'user', 'content': f"Tool result for {func_name}: {result_str}"})

        return {'content': "System: Task stopped because it exceeded maximum tool execution turns."}

    @api.model
    def _get_tools(self):
        """ Load standard tools schemas. """
        read_tools = self.env['ai.tools.schema'].get_read_tools()
        enable_write = self.env['ir.config_parameter'].sudo().get_param('odoo_ai_assistant.enable_write_tools')
        if enable_write:
            write_tools = self.env['ai.tools.schema'].get_write_tools()
            read_tools.extend(write_tools)
        return read_tools

    @api.model
    def _process_openai_response(self, response):
        message = response.get('choices', [{}])[0].get('message', {})
        if message.get('tool_calls'):
            return {'type': 'tool_call', 'tool_calls': message.get('tool_calls')}
        return {'type': 'text', 'content': message.get('content', '')}
        
    @api.model
    def _process_gemini_response(self, response):
        parts = response.get('candidates', [{}])[0].get('content', {}).get('parts', [])
        if not parts:
            return {'type': 'text', 'content': "No content returned from Gemini."}
            
        for part in parts:
            if 'functionCall' in part:
                # Format to standard tool call format
                return {
                    'type': 'tool_call', 
                    'tool_calls': [{'name': part['functionCall']['name'], 'args': part['functionCall'].get('args', {})}]
                }
        
        texts = [p.get('text', '') for p in parts if 'text' in p]
        return {'type': 'text', 'content': ''.join(texts)}
        
    @api.model
    def _process_anthropic_response(self, response):
        content_blocks = response.get('content', [])
        for block in content_blocks:
            if block.get('type') == 'tool_use':
                return {
                    'type': 'tool_call', 
                    'tool_calls': [{'name': block['name'], 'args': block['input']}]
                }
                
        texts = [b.get('text', '') for b in content_blocks if b.get('type') == 'text']
        return {'type': 'text', 'content': ''.join(texts)}

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
