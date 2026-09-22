from odoo.tests.common import TransactionCase

class TestAIEngine(TransactionCase):

    def setUp(self):
        super(TestAIEngine, self).setUp()
        self.AIEngine = self.env['ai.engine']

    def test_route_request_vision(self):
        """ Test that image presence triggers the vision role. """
        messages = [
            {'role': 'user', 'content': 'what is this?', 'images': ['base64string']}
        ]
        role = self.AIEngine._route_request(messages)
        self.assertEqual(role, 'vision', "Routing should select 'vision' when images are present.")

    def test_route_request_write(self):
        """ Test that write keywords trigger the write role. """
        # Using default keywords 'create'
        messages = [
            {'role': 'user', 'content': 'please create a new partner'}
        ]
        role = self.AIEngine._route_request(messages)
        self.assertEqual(role, 'write', "Routing should select 'write' when write keywords are present.")

    def test_route_request_read(self):
        """ Test that normal messages default to read role. """
        messages = [
            {'role': 'user', 'content': 'summarize the sales today'}
        ]
        role = self.AIEngine._route_request(messages)
        self.assertEqual(role, 'read', "Routing should select 'read' for normal queries.")

    def test_custom_system_prompt(self):
        """ Test that custom system prompt from settings is appended to the base prompt. """
        self.env['ir.config_parameter'].sudo().set_param('odoo_ai_assistant.custom_system_prompt', 'BE POLITE.')
        system_prompt = self.AIEngine._get_system_prompt()
        self.assertIn('BE POLITE.', system_prompt, "Custom system prompt should be appended to the final prompt.")
