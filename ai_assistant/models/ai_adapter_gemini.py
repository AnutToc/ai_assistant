import requests
from odoo import models, api
from odoo.exceptions import UserError

class AIAdapterGemini(models.AbstractModel):
    _name = 'ai.adapter.gemini'
    _description = 'Google Gemini Adapter'

    @api.model
    def send_request(self, provider, messages, tools=None):
        base_url = (provider.api_base_url or 'https://generativelanguage.googleapis.com/v1beta').rstrip('/')
        model_name = provider.model_name or 'gemini-1.5-pro'
        api_key = provider.api_key or ''
        
        # Gemini passes API key in the URL
        endpoint = f"{base_url}/models/{model_name}:generateContent?key={api_key}"
        headers = {'Content-Type': 'application/json'}

        # Convert standard messages to Gemini format
        gemini_contents = []
        for msg in messages:
            # Skip system for simple MVP, or could use 'system_instruction' parameter in payload
            if msg.get('role') == 'system':
                continue
            role = 'model' if msg.get('role') == 'assistant' else 'user'
            gemini_contents.append({
                'role': role,
                'parts': [{'text': msg.get('content', '')}]
            })

        payload = {'contents': gemini_contents}

        # Convert Standard Tools (OpenAI format) to Gemini format
        if tools:
            gemini_tools = []
            for t in tools:
                func = t.get('function', {})
                gemini_tools.append({
                    'name': func.get('name'),
                    'description': func.get('description'),
                    'parameters': func.get('parameters', {'type': 'OBJECT', 'properties': {}})
                })
            payload['tools'] = [{'function_declarations': gemini_tools}]

        try:
            response = requests.post(endpoint, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            error_msg = response.text if 'response' in locals() and response is not None else str(e)
            final_error = f"Gemini API Connection Error:\n{error_msg} | {str(e)}"
            # Security: Mask the API key in any error outputs
            if provider.api_key:
                final_error = final_error.replace(provider.api_key, '***MASKED_KEY***')
            raise UserError(final_error)

        return response.json()
