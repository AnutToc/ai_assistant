import json
import logging
import re

from odoo import api, models
from odoo.exceptions import AccessError, ValidationError

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

        method_name = f'_execute_tool_{tool_name}'
        if not hasattr(self, method_name):
            return {"error": f"Tool '{tool_name}' is not implemented."}

        try:
            # 2. Dynamic Dispatch to specific tool execution method
            return getattr(self, method_name)(**kwargs)
        except AccessError as e:
            # Silent security failure for the AI
            return {"error": "Access Denied: The current user does not have permission for this record/model."}
        except Exception as e:
            # 3. Error Sanitization
            return {"error": self._sanitize_error(e)}

    @api.model
    def _execute_tool_search_records(self, **kwargs):
        model_name = kwargs.get('model')
        domain_val = kwargs.get('domain', '[]')
        domain = json.loads(domain_val) if isinstance(domain_val, str) else domain_val
        fields_list = kwargs.get('fields', [])
        limit = kwargs.get('limit', 10)
        records = self.env[model_name].search_read(domain, fields=fields_list, limit=limit)
        return self._strip_sensitive_fields(records)

    @api.model
    def _execute_tool_get_fields(self, **kwargs):
        model_name = kwargs.get('model')
        fields_info = self.env[model_name].fields_get()
        return self._strip_sensitive_fields(fields_info)

    @api.model
    def _execute_tool_aggregate_records(self, **kwargs):
        model_name = kwargs.get('model')
        domain_val = kwargs.get('domain', '[]')
        domain = json.loads(domain_val) if isinstance(domain_val, str) else domain_val
        group_by = kwargs.get('group_by', [])
        fields_list = kwargs.get('fields', [])
        limit = kwargs.get('limit', 20)
        result = self.env[model_name].read_group(
            domain, fields=fields_list, groupby=group_by, limit=limit
        )
        cleaned = []
        for group in result:
            row = {k: v for k, v in group.items() if k != '__domain'}
            cleaned.append(row)
        return self._strip_sensitive_fields(cleaned)

    @api.model
    def _execute_tool_create_record(self, **kwargs):
        model_name = kwargs.get('model')
        if self.env['ir.config_parameter'].sudo().get_param('odoo_ai_assistant.enable_create_tools') != 'True':
            return {"error": "Create tools are currently disabled by the system administrator."}
        val_str = kwargs.get('values', '{}')
        values = json.loads(val_str) if isinstance(val_str, str) else val_str
        new_record = self.env[model_name].create(values)
        return {"success": True, "id": new_record.id}

    @api.model
    def _execute_tool_update_record(self, **kwargs):
        model_name = kwargs.get('model')
        if self.env['ir.config_parameter'].sudo().get_param('odoo_ai_assistant.enable_update_tools') != 'True':
            return {"error": "Update tools are currently disabled by the system administrator."}
        record_id = kwargs.get('record_id')
        val_str = kwargs.get('values', '{}')
        values = json.loads(val_str) if isinstance(val_str, str) else val_str
        record = self.env[model_name].browse(int(record_id))
        if not record.exists():
            return {"error": f"Record with ID {record_id} not found in '{model_name}'."}
        record.write(values)
        return {"success": True, "id": record.id}

    @api.model
    def _execute_tool_delete_record(self, **kwargs):
        model_name = kwargs.get('model')
        if self.env['ir.config_parameter'].sudo().get_param('odoo_ai_assistant.enable_delete_tools') != 'True':
            return {"error": "Delete tools are currently disabled by the system administrator."}
        record_id = kwargs.get('record_id')
        record = self.env[model_name].browse(int(record_id))
        if not record.exists():
            return {"error": f"Record with ID {record_id} not found in '{model_name}'."}
        record.unlink()
        return {"success": True, "deleted_id": record_id}
