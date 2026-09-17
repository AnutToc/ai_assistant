import re
import json
import logging
from odoo import models, api
from odoo.exceptions import AccessError, ValidationError

_logger = logging.getLogger(__name__)

# Markers used for In-Flight Sanitization
SENSITIVE_FIELD_MARKERS = ['password', 'secret', 'token', 'api_key', 'otp', 'pin', 'session']

# System Blacklist
SYSTEM_MODELS_BLACKLIST = ['res.users', 'res.groups', 'res.config.settings', 'ir.config_parameter']

class AIToolsExecutor(models.AbstractModel):
    _name = 'ai.tools.executor'
    _description = 'AI Tools Executor and Security Layer'

    @api.model
    def _is_model_allowed(self, model_name):
        """ System Blacklist: Block all ir.* models and specific system models. """
        if not model_name:
            return False
        if model_name.startswith('ir.') or model_name in SYSTEM_MODELS_BLACKLIST:
            return False
        return True

    @api.model
    def _strip_sensitive_fields(self, data):
        """ In-Flight Sanitization: Remove sensitive fields from dictionaries. """
        if isinstance(data, dict):
            return {
                k: self._strip_sensitive_fields(v) 
                for k, v in data.items() 
                if not any(marker in k.lower() for marker in SENSITIVE_FIELD_MARKERS)
            }
        elif isinstance(data, list):
            return [self._strip_sensitive_fields(item) for item in data]
        return data

    @api.model
    def _sanitize_error(self, error):
        """ Error Sanitization: Strip server paths and internal structures from exceptions. """
        error_msg = str(error)
        # Regex to mask file paths (e.g., /opt/odoo/..., C:\Users\...)
        error_msg = re.sub(r'(/[a-zA-Z0-9_.-]+)+/[a-zA-Z0-9_.-]+\.py', '<hidden_path>', error_msg)
        error_msg = re.sub(r'[A-Z]:\\[^\n]+\.py', '<hidden_path>', error_msg)
        return f"Database/Execution Error: {error_msg}"

    @api.model
    def execute_tool(self, tool_name, kwargs):
        model_name = kwargs.get('model')
        
        # 1. System Blacklist Check
        if model_name and not self._is_model_allowed(model_name):
            return {"error": f"Security Policy: AI is not allowed to access the '{model_name}' model."}

        try:
            # 2. Native RBAC Execution (via self.env)
            if tool_name == 'search_records':
                # Safely parse stringified JSON domain if necessary
                domain_val = kwargs.get('domain', '[]')
                domain = json.loads(domain_val) if isinstance(domain_val, str) else domain_val
                
                fields = kwargs.get('fields', [])
                limit = kwargs.get('limit', 10)
                records = self.env[model_name].search_read(domain, fields=fields, limit=limit)
                
                # 3. In-Flight Sanitization
                return self._strip_sensitive_fields(records)

            elif tool_name == 'get_fields':
                fields_info = self.env[model_name].fields_get()
                return self._strip_sensitive_fields(fields_info)

            elif tool_name == 'create_record':
                # Note: Engine should check write privileges before calling this.
                val_str = kwargs.get('values', '{}')
                values = json.loads(val_str) if isinstance(val_str, str) else val_str
                new_record = self.env[model_name].create(values)
                return {"success": True, "id": new_record.id}

            else:
                return {"error": f"Tool '{tool_name}' is not implemented."}

        except AccessError as e:
            # Silent security failure for the AI
            return {"error": "Access Denied: The current user does not have permission for this record/model."}
        except Exception as e:
            # 4. Error Sanitization
            _logger.warning("AI Tool Execution Error: %s", str(e))
            return {"error": self._sanitize_error(e)}
