import io
import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image
from pydantic import ValidationError

os.environ["ENABLE_SCHEDULER"] = "false"

from src.content import PostContent
from src.generator import generate_post
from src.image_generator import compose_post_card
from src.server import app


def sample_content(**overrides) -> PostContent:
    data = {
        "theme": "Small ways to feel calmer",
        "hook": "Free things that can help you feel calmer",
        "items": [
            "Morning sunlight.",
            "Bare feet on grass.",
            "Ten slow breaths.",
            "A quiet walk without your phone.",
        ],
        "caption": (
            "Free things that can help you feel calmer.\n\n"
            "Morning sunlight.\nBare feet on grass.\nTen slow breaths.\n"
            "A quiet walk without your phone.\n\nFollow @mteenmindful for more."
        ),
        "hashtags": "#mTeenMindful #MindfulTeens #StressRelief",
        "alt_text": "A calm mTeen list card with Mitra standing beside four ideas.",
        "image_prompt": "Soft dawn colors with subtle grass and warm natural light.",
        "cta": "Follow @mteenmindful for more simple practices.",
    }
    data.update(overrides)
    return PostContent(**data)


class ContentContractTests(unittest.TestCase):
    def test_rejects_health_treatment_promises(self):
        with self.assertRaises(ValidationError):
            sample_content(hook="Cheap things that heal your nervous system")

    def test_rejects_too_many_list_items(self):
        with self.assertRaises(ValidationError):
            sample_content(items=[f"Item {index}" for index in range(8)])


class PostCardTests(unittest.TestCase):
    def test_composes_instagram_portrait_with_exact_mitra_asset(self):
        background = Image.new("RGB", (1024, 1280), "#30204d")
        source = io.BytesIO()
        background.save(source, format="PNG")

        result = compose_post_card(sample_content(), source.getvalue())
        image = Image.open(io.BytesIO(result))

        self.assertEqual("JPEG", image.format)
        self.assertEqual((1080, 1350), image.size)
        self.assertGreater(len(result), 100_000)


class GenerationPipelineTests(unittest.TestCase):
    def test_generated_content_and_exact_image_are_saved_together(self):
        content = sample_content()
        response = SimpleNamespace(
            content=[SimpleNamespace(text=json.dumps(content.model_dump()))],
            usage=SimpleNamespace(input_tokens=100, output_tokens=80),
        )
        client = SimpleNamespace(
            messages=SimpleNamespace(create=lambda **kwargs: response)
        )
        visual = SimpleNamespace(
            image_bytes=b"generated-jpeg",
            mime_type="image/jpeg",
            metadata={"image_model": "gpt-image-2"},
        )
        settings = SimpleNamespace(
            anthropic_api_key="configured",
            server_base_url="https://mindful.example",
        )

        with (
            patch("src.generator.get_settings", return_value=settings),
            patch("src.generator.anthropic.Anthropic", return_value=client),
            patch("src.generator.generate_post_visual", return_value=visual),
            patch("src.generator.create_post", return_value=123),
            patch("src.generator.save_post_image") as save_image,
        ):
            result = generate_post(theme={"id": "calm", "theme": "Calm", "context": ""})

        self.assertEqual(123, result["post_id"])
        self.assertTrue(result["image_url"].startswith("https://mindful.example/media/"))
        self.assertTrue(result["image_url"].endswith(".jpg"))
        save_image.assert_called_once_with(123, b"generated-jpeg", "image/jpeg")


class MediaEndpointTests(unittest.TestCase):
    def test_serves_the_exact_stored_post_image(self):
        payload = b"test-image-bytes"
        with patch(
            "src.server.get_post_image_by_token",
            return_value={"image_data": payload, "mime_type": "image/jpeg"},
        ) as image_lookup:
            response = TestClient(app).get("/media/safe-token.jpg")

        self.assertEqual(200, response.status_code)
        self.assertEqual("image/jpeg", response.headers["content-type"])
        self.assertEqual(
            'inline; filename="mteen-post.jpg"',
            response.headers["content-disposition"],
        )
        self.assertEqual(payload, response.content)
        image_lookup.assert_called_once_with("safe-token")

    def test_robots_allows_meta_to_fetch_post_media(self):
        response = TestClient(app).get("/robots.txt")

        self.assertEqual(200, response.status_code)
        self.assertEqual("text/plain; charset=utf-8", response.headers["content-type"])
        self.assertIn("Allow: /media/", response.text)

    def test_opening_approval_link_never_publishes(self):
        post = {"id": 42, "status": "pending_approval"}
        with (
            patch("src.server.get_post_by_token", return_value=post),
            patch(
                "src.server.get_post_image_by_token",
                return_value={"image_data": b"jpeg", "mime_type": "image/jpeg"},
            ),
            patch("src.server.publish_post") as publish,
        ):
            response = TestClient(app).get("/approve/safe-token")

        self.assertEqual(200, response.status_code)
        self.assertIn("Publish to Instagram", response.text)
        publish.assert_not_called()

    def test_legacy_post_cannot_publish_without_a_generated_image(self):
        post = {
            "id": 42,
            "status": "pending_approval",
            "theme": "A legacy post",
            "caption": "Legacy caption",
            "hashtags": "#legacy",
        }
        with (
            patch("src.server.get_post_by_token", return_value=post),
            patch("src.server.get_post_image_by_token", return_value=None),
            patch("src.server.publish_post") as publish,
        ):
            response = TestClient(app).post("/approve/legacy-token")

        self.assertEqual(409, response.status_code)
        publish.assert_not_called()


if __name__ == "__main__":
    unittest.main()
