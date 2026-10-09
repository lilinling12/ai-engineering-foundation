import unittest
from app.greeting import greet

class IndependentAcceptance(unittest.TestCase):
    def test_greeting(self):
        self.assertEqual(greet("Ada"), "Hello, Ada")
        self.assertEqual(greet("世界"), "Hello, 世界")
