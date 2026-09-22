import requests

from odoo import api, models
from odoo.exceptions import UserError

class AIAdapterOpenAI(models.AbstractModel):
    _name = 'ai.adapter.openai'
    _description = 'OpenAI Compatible Adapter'

    @api.model
    def _convert_messages(self, messages):
        """ Convert internal message format to OpenAI format, handling multimodal content. """
        converted = []
        for msg in messages:
            if msg.get('images') and msg.get('role') == 'user':
                # Build multimodal content array
                content_parts = []
                if msg.get('content'):
                    content_parts.append({"type": "text", "text": msg['content']})
                for img in msg['images']:
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:{img['mime_type']};base64,{img['base64']}"}
                    })
                converted.append({"role": "user", "content": content_parts})
            else:
                converted.append({"role": msg.get('role', 'user'), "content": msg.get('content', '')})
        return converted

    @api.model
    def send_request(self, provider, messages, tools=None):
        """
        Sends a request to an OpenAI-compatible endpoint.
        Works for OpenAI, Qwen (DashScope), DeepSeek, Ollama, vLLM, etc.
        """
        # Default to OpenAI if no base URL is provided
        base_url = provider.api_base_url or 'https://api.openai.com/v1'
        base_url = base_url.rstrip('/')
        endpoint = f"{base_url}/chat/completions"

        headers = {
            'Content-Type': 'application/json',
        }
        if provider.api_key:
            headers['Authorization'] = f'Bearer {provider.api_key}'

        payload = {
            'model': provider.model_name,
            'messages': self._convert_messages(messages),
        }
        
        # Inject tools if available and write access is allowed/configured
        if tools:
            payload['tools'] = tools
            payload['tool_choice'] = 'auto'

        response = None

        try:

            response = requests.post(endpoint, headers=headers, json=payload, timeout=600)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            error_msg = response.text if response is not None else str(e)
            raise UserError(f"AI API Connection Error:\n{error_msg}")

        return response.json()
