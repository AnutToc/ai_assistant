import requests

from odoo import api, models
from odoo.exceptions import UserError

class AIAdapterAnthropic(models.AbstractModel):
    _name = 'ai.adapter.anthropic'
    _description = 'Anthropic Claude Adapter'

    @api.model
    def send_request(self, provider, messages, tools=None):
        base_url = (provider.api_base_url or 'https://api.anthropic.com/v1').rstrip('/')
        endpoint = f"{base_url}/messages"

        headers = {
            'Content-Type': 'application/json',
            'x-api-key': provider.api_key or '',
            'anthropic-version': '2023-06-01',
            'anthropic-beta': 'pdfs-2024-09-25'
        }

        # Convert standard messages to Anthropic format
        anthropic_messages = []
        system_prompt = "You are a helpful Odoo AI assistant."
        for msg in messages:
            if msg.get('role') == 'system':
                system_prompt += "\n" + msg.get('content')
            else:
                role = 'assistant' if msg.get('role') == 'assistant' else 'user'
                
                # Handle multimodal images and documents
                if (msg.get('images') or msg.get('documents')) and role == 'user':
                    content_blocks = []
                    if msg.get('images'):
                        for img in msg['images']:
                            content_blocks.append({
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": img['mime_type'],
                                    "data": img['base64']
                                }
                            })
                    if msg.get('documents'):
                        for doc in msg['documents']:
                            content_blocks.append({
                                "type": "document",
                                "source": {
                                    "type": "base64",
                                    "media_type": doc['mime_type'],
                                    "data": doc['base64']
                                }
                            })
                    if msg.get('content'):
                        content_blocks.append({"type": "text", "text": msg['content']})
                    anthropic_messages.append({'role': role, 'content': content_blocks})
                else:
                    anthropic_messages.append({'role': role, 'content': msg.get('content', '')})

        # Ensure alternating roles if necessary, but basic user-assistant is fine for MVP.
        payload = {
            'model': provider.model_name or 'claude-3-5-sonnet-20240620',
            'max_tokens': 4096,
            'messages': anthropic_messages,
            'system': system_prompt
        }

        # Convert Standard Tools (OpenAI format) to Anthropic format
        if tools:
            anthropic_tools = []
            for t in tools:
                func = t.get('function', {})
                anthropic_tools.append({
                    'name': func.get('name'),
                    'description': func.get('description'),
                    'input_schema': func.get('parameters', {'type': 'object', 'properties': {}})
                })
            payload['tools'] = anthropic_tools

        response = None

        try:

            response = requests.post(endpoint, headers=headers, json=payload, timeout=600)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            error_msg = response.text if response is not None else str(e)
            raise UserError(f"Anthropic API Connection Error:\n{error_msg}")

        return response.json()
