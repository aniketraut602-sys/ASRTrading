import unittest
from asr_trading.brain.knowledge import knowledge_manager

class TestKnowledgeManager(unittest.TestCase):
    def test_query(self):
        # Query for Hammer
        results = knowledge_manager.query(["CDL_HAMMER"])
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0]["id"], "KNO_002")
        self.assertIn("60% win rate", results[0]["summary"])
    
    def test_multi_tag(self):
        results = knowledge_manager.query(["CDL_DOJI", "NON_EXISTENT"])
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0]["id"], "KNO_001")

if __name__ == "__main__":
    unittest.main()
