import unittest

from pydantic import ValidationError

from app.schemas.platform_template import (
    PlatformTemplateCreate,
    PlatformTemplateSubmitRequest,
)


class PlatformTemplateSchemaTests(unittest.TestCase):
    def test_accepts_body_only_marketing_and_utility_templates(self):
        template = PlatformTemplateCreate(
            name="order_update",
            label="Order update",
            language="en_US",
            category="utility",
            body_text="Order {{1}} is ready for {{2}}.",
        )
        self.assertEqual(template.category, "utility")

    def test_rejects_authentication_category_and_nonsequential_placeholders(self):
        with self.assertRaises(ValidationError):
            PlatformTemplateCreate(
                name="otp",
                label="OTP",
                language="en_US",
                category="authentication",
                body_text="Code {{1}}",
            )
        with self.assertRaises(ValidationError):
            PlatformTemplateCreate(
                name="order_update",
                label="Order update",
                language="en_US",
                category="utility",
                body_text="Order {{2}} is ready.",
            )

    def test_submit_example_values_are_bounded(self):
        with self.assertRaises(ValidationError):
            PlatformTemplateSubmitRequest(
                channel_connection_id="123e4567-e89b-42d3-a456-426614174000",
                body_text="Hello {{1}}",
                examples=["x" * 1025],
            )
