from odoo.tests.common import TransactionCase

class TestAIToolsExecutor(TransactionCase):

    def setUp(self):
        super(TestAIToolsExecutor, self).setUp()
        self.Executor = self.env['ai.tools.executor']

    def test_blacklist_security(self):
        """ Test that AI cannot access blacklisted models. """
        # Try to read res.users
        result = self.Executor.execute_tool('search_records', {'model': 'res.users', 'domain': '[]', 'limit': 1})
        self.assertIn('error', result)
        self.assertIn('Security Policy', result['error'])

    def test_create_record_permission(self):
        """ Test that create_record obeys the ai_enable_create_tools setting. """
        # Disable create tools
        self.env['ir.config_parameter'].sudo().set_param('odoo_ai_assistant.enable_create_tools', 'False')
        
        result = self.Executor.execute_tool('create_record', {'model': 'res.partner.category', 'values': '{"name": "Test Tag"}'})
        self.assertIn('error', result)
        self.assertIn('Create tools are currently disabled', result['error'])

        # Enable create tools
        self.env['ir.config_parameter'].sudo().set_param('odoo_ai_assistant.enable_create_tools', 'True')
        result2 = self.Executor.execute_tool('create_record', {'model': 'res.partner.category', 'values': '{"name": "Test Tag"}'})
        self.assertTrue(result2.get('success'), f"Should succeed when setting is enabled, but got: {result2}")

    def test_data_sanitization(self):
        """ Test that sensitive fields are stripped from the results. """
        # We simulate a dictionary with a sensitive field 'password'
        data = {
            'id': 1,
            'name': 'Test User',
            'password': 'supersecretpassword',
            'api_key': '12345'
        }
        sanitized = self.Executor._strip_sensitive_fields(data)
        
        self.assertEqual(sanitized.get('name'), 'Test User')
        self.assertNotIn('password', sanitized, "Password field should be stripped.")
        self.assertNotIn('api_key', sanitized, "API key field should be stripped.")
