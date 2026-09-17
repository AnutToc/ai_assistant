from odoo import models, api

class AIToolsSchema(models.AbstractModel):
    _name = 'ai.tools.schema'
    _description = 'AI Tools JSON Schemas'

    @api.model
    def get_read_tools(self):
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_records",
                    "description": "Search for records in an Odoo model. Use domain for filtering.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "model": {"type": "string", "description": "Odoo model name (e.g., 'res.partner')"},
                            "domain": {"type": "array", "description": "Odoo search domain as a list. Examples: [['is_company', '=', True]] or ['|', ['name', '=', 'John'], ['name', '=', 'Doe']]"},
                            "fields": {"type": "array", "items": {"type": "string"}, "description": "Specific fields to return"},
                            "limit": {"type": "integer", "description": "Max records to return"}
                        },
                        "required": ["model"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_fields",
                    "description": "Get field definitions of a model.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "model": {"type": "string"}
                        },
                        "required": ["model"]
                    }
                }
            }
        ]

    @api.model
    def get_write_tools(self):
        return [
            {
                "type": "function",
                "function": {
                    "name": "create_record",
                    "description": "Create a new record.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "model": {"type": "string", "description": "Odoo model name"},
                            "values": {"type": "string", "description": "JSON string of dictionary values to insert"}
                        },
                        "required": ["model", "values"]
                    }
                }
            }
        ]
