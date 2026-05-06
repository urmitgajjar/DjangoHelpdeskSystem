from urllib import error
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from myapp.ai.ai_priority import _extract_priority, predict_ticket_priority, predict_ticket_priority_with_meta


class AIPriorityHelperTests(SimpleTestCase):
    def test_extract_priority_from_json(self):
        self.assertEqual(_extract_priority('{"priority":"HIGH"}'), "HIGH")

    def test_extract_priority_from_plain_text(self):
        self.assertEqual(_extract_priority("This looks urgent"), "URGENT")

    @override_settings(GROQ_API_KEY="")
    def test_predict_returns_fallback_when_key_missing(self):
        self.assertEqual(predict_ticket_priority("title", "description"), "MEDIUM")

    @override_settings(GROQ_API_KEY="gsk_dummy-key")
    @patch("myapp.ai.ai_priority.request.urlopen", side_effect=error.URLError("timeout"))
    def test_predict_with_meta_handles_network_errors(self, _mock_urlopen):
        result = predict_ticket_priority_with_meta("Printer down", "Entire office cannot print.")
        self.assertEqual(result["priority"], "URGENT")
        self.assertTrue(result["error"])
