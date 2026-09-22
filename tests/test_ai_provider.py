from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError

class TestAIProvider(TransactionCase):

    def setUp(self):
        super(TestAIProvider, self).setUp()
        self.AIProvider = self.env['ai.provider']
        self.AIProvider.search([]).unlink()

    def test_single_active_role_constraint(self):
        """ Test that we cannot have two active providers with the same role. """
        self.AIProvider.create({
            'name': 'Provider 1',
            'protocol_type': 'openai_compatible',
            'model_name': 'test-model-1',
            'ai_role': 'read',
            'is_active': True
        })
        
        with self.assertRaises(ValidationError):
            self.AIProvider.create({
                'name': 'Provider 2',
                'protocol_type': 'openai_compatible',
                'model_name': 'test-model-2',
                'ai_role': 'read',
                'is_active': True
            })
            
    def test_multiple_inactive_roles_allowed(self):
        """ Test that we can have multiple inactive providers with the same role. """
        self.AIProvider.create({
            'name': 'Provider Inactive 1',
            'protocol_type': 'openai_compatible',
            'model_name': 'test-model-1',
            'ai_role': 'read',
            'is_active': False
        })
        
        provider2 = self.AIProvider.create({
            'name': 'Provider Inactive 2',
            'protocol_type': 'openai_compatible',
            'model_name': 'test-model-2',
            'ai_role': 'read',
            'is_active': False
        })
        self.assertTrue(provider2.id)
