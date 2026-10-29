"""Quick API-level smoke tests. Run with: py -m unittest discover -s tests"""
import unittest
from app.assistant import answer_question

class AssistantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.database import initialise_database
        cls.report = initialise_database()

    def test_total_revenue_returns_sql(self):
        result = answer_question("What is the total revenue?")
        self.assertTrue(result["ok"])
        self.assertIn("SELECT", result["sql"].upper())
        self.assertIn("total_revenue", result["data"])

    def test_monthly_trend_returns_rows(self):
        result = answer_question("What is the monthly revenue trend?")
        self.assertTrue(result["ok"])
        self.assertIsInstance(result["data"], list)

    def test_unknown_question_is_rejected(self):
        result = answer_question("Tell me a joke")
        self.assertFalse(result["ok"])

if __name__ == "__main__":
    unittest.main()
