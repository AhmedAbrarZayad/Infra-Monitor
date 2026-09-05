from django.test import SimpleTestCase

from log.views.internal import redact_message, redact_metadata


class LogRedactionTests(SimpleTestCase):
    def test_sensitive_metadata_keys_are_redacted_case_insensitively(self):
        self.assertEqual(
            redact_metadata({"Authorization": "Bearer secret", "request_id": "abc"}),
            {"Authorization": "[REDACTED]", "request_id": "abc"},
        )

    def test_sensitive_message_values_are_redacted(self):
        self.assertEqual(
            redact_message("token=secret-value request completed"),
            "token=[REDACTED] request completed",
        )
