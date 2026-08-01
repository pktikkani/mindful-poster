"""Generate a themed background and compose an exact Mitra-branded post card."""

import base64
import io
import textwrap
from dataclasses import dataclass
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from .config import get_settings
from .content import PostContent

OPENAI_IMAGES_URL = "https://api.openai.com/v1/images/generations"
ROOT = Path(__file__).parent.parent
MASCOT_PATH = ROOT / "assets" / "mitra.png"
CANVAS_SIZE = (1080, 1350)
API_IMAGE_SIZE = "1024x1280"


class ImageGenerationError(RuntimeError):
    """Raised when a branded post image cannot be generated."""


@dataclass(frozen=True)
class GeneratedVisual:
    image_bytes: bytes
    mime_type: str
    metadata: dict


def generate_post_visual(content: PostContent) -> GeneratedVisual:
    """Generate a background with OpenAI and compose the final 4:5 post image."""
    settings = get_settings()
    if not settings.openai_api_key:
        raise ImageGenerationError("OPENAI_API_KEY is not configured")

    prompt = _background_prompt(content)
    payload = {
        "model": settings.openai_image_model,
        "prompt": prompt,
        "size": API_IMAGE_SIZE,
        "quality": settings.openai_image_quality,
        "output_format": "png",
        "n": 1,
    }

    try:
        with httpx.Client(timeout=240) as client:
            response = client.post(
                OPENAI_IMAGES_URL,
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        detail = _safe_error_detail(exc)
        raise ImageGenerationError(f"OpenAI image generation failed: {detail}") from exc

    try:
        background_bytes = base64.b64decode(result["data"][0]["b64_json"], validate=True)
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ImageGenerationError("OpenAI returned no decodable image") from exc

    image_bytes = compose_post_card(content, background_bytes)
    metadata = {
        "image_model": settings.openai_image_model,
        "image_quality": settings.openai_image_quality,
        "image_size": API_IMAGE_SIZE,
        "image_usage": result.get("usage", {}),
    }
    return GeneratedVisual(image_bytes=image_bytes, mime_type="image/jpeg", metadata=metadata)


def compose_post_card(content: PostContent, background_bytes: bytes) -> bytes:
    """Compose exact typography and the original Mitra asset over a background."""
    try:
        background = Image.open(io.BytesIO(background_bytes)).convert("RGB")
    except Exception as exc:
        raise ImageGenerationError("Generated background is not a valid image") from exc

    canvas = _cover(background, CANVAS_SIZE).convert("RGBA")
    canvas = ImageEnhance.Color(canvas).enhance(0.86)
    canvas = ImageEnhance.Brightness(canvas).enhance(0.72)

    overlay = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    panel = (48, 48, 758, 1195)
    draw.rounded_rectangle(
        panel,
        radius=54,
        fill=(255, 247, 232, 242),
        outline=(232, 152, 62, 210),
        width=3,
    )
    canvas = Image.alpha_composite(canvas, overlay)
    draw = ImageDraw.Draw(canvas)

    dark = (45, 32, 72, 255)
    orange = (211, 96, 30, 255)
    muted = (87, 75, 101, 255)
    brand_font = _font(27, bold=True)
    headline_font = _font(60, bold=True)
    item_font = _font(35)
    footer_font = _font(25, bold=True)

    draw.text((86, 88), "@mteenmindful  •  MINDFUL MOMENT", font=brand_font, fill=muted)
    y = 160
    headline_lines = _wrap_text(draw, content.hook.upper(), headline_font, 600)
    for line in headline_lines[:4]:
        draw.text((84, y), line, font=headline_font, fill=dark)
        y += 68

    y += 28
    draw.line((84, y, 650, y), fill=(224, 156, 82, 255), width=3)
    y += 34

    for item in content.items:
        lines = _wrap_text(draw, item, item_font, 520)
        draw.ellipse((86, y + 13, 101, y + 28), fill=orange)
        for line_index, line in enumerate(lines[:2]):
            draw.text((120, y), line, font=item_font, fill=dark)
            y += 44
        y += 16 if len(lines) == 1 else 10

    footer_y = min(max(y + 22, 1085), 1135)
    draw.text((84, footer_y), "SAVE THIS FOR A HEAVY DAY.", font=footer_font, fill=orange)

    mascot = Image.open(MASCOT_PATH).convert("RGBA")
    bbox = mascot.getbbox()
    if not bbox:
        raise ImageGenerationError("Mitra mascot asset is empty")
    mascot = mascot.crop(bbox)
    target_height = 990
    target_width = round(mascot.width * target_height / mascot.height)
    mascot = mascot.resize((target_width, target_height), Image.Resampling.LANCZOS)
    mascot_x = CANVAS_SIZE[0] - target_width - 18
    mascot_y = CANVAS_SIZE[1] - target_height - 4
    canvas.alpha_composite(mascot, (mascot_x, mascot_y))

    output = io.BytesIO()
    canvas.convert("RGB").save(output, format="JPEG", quality=92, optimize=True)
    return output.getvalue()


def _background_prompt(content: PostContent) -> str:
    return textwrap.dedent(
        f"""
        Create a premium 4:5 Instagram wellness-card background for Indian teenagers.
        Theme: {content.theme}
        Art direction: {content.image_prompt}
        Use a calm editorial palette of midnight indigo, muted plum, warm cream,
        saffron orange, and sage green. Keep the center-left visually quiet for a
        large cream copy panel and keep the lower-right uncluttered for a mascot
        overlay. Subtle abstract breath rings, natural texture, and soft cinematic
        light are welcome.
        Background only. No people, characters, mascots, faces, hands, text, letters,
        numbers, logos, icons, UI, frames, borders, signatures, or watermark.
        """
    ).strip()


def _cover(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    scale = max(size[0] / image.width, size[1] / image.height)
    resized = image.resize(
        (round(image.width * scale), round(image.height * scale)),
        Image.Resampling.LANCZOS,
    )
    left = (resized.width - size[0]) // 2
    top = (resized.height - size[1]) // 2
    return resized.crop((left, top, left + size[0], top + size[1]))


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    raise ImageGenerationError("No supported TrueType font is installed")


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str]:
    words = text.split()
    if not words:
        return []
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _safe_error_detail(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        try:
            payload = exc.response.json()
            return payload.get("error", {}).get("message", f"HTTP {exc.response.status_code}")
        except ValueError:
            return f"HTTP {exc.response.status_code}"
    return str(exc)
