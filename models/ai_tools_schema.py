from odoo import api, models

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
            },
            {
                "type": "function",
                "function": {
                    "name": "aggregate_records",
                    "description": "Aggregate and summarize records using GROUP BY with SUM, COUNT, AVG. Use for reports, dashboards, and summaries. Returns grouped results with totals.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "model": {"type": "string", "description": "Odoo model name (e.g., 'sale.order')"},
                            "domain": {"type": "array", "description": "Search domain for filtering records before aggregation"},
                            "group_by": {"type": "array", "items": {"type": "string"}, "description": "Fields to group by (e.g., ['partner_id', 'state'])"},
                            "fields": {"type": "array", "items": {"type": "string"}, "description": "Fields to aggregate. Use 'field_name:agg' format: 'amount_total:sum', 'id:count', 'price_unit:avg'"},
                            "limit": {"type": "integer", "description": "Max number of groups to return"}
                        },
                        "required": ["model", "group_by"]
                    }
                }
            }
        ]

    @api.model
    def get_create_tools(self):
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

    @api.model
    def get_update_tools(self):
        return [
            {
                "type": "function",
                "function": {
                    "name": "update_record",
                    "description": "Update an existing record by its ID.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "model": {"type": "string", "description": "Odoo model name"},
                            "record_id": {"type": "integer", "description": "The ID of the record to update"},
                            "values": {"type": "string", "description": "JSON string of dictionary values to update"}
                        },
                        "required": ["model", "record_id", "values"]
                    }
                }
            }
        ]

    @api.model
    def get_delete_tools(self):
        return [
            {
                "type": "function",
                "function": {
                    "name": "delete_record",
                    "description": "Delete an existing record by its ID.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "model": {"type": "string", "description": "Odoo model name"},
                            "record_id": {"type": "integer", "description": "The ID of the record to delete"}
                        },
                        "required": ["model", "record_id"]
                    }
                }
            }
        ]
