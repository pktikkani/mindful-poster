"""Typed content contract shared by generation, image rendering, and publishing."""

import re

from pydantic import BaseModel, Field, field_validator


class PostContent(BaseModel):
    """One concise, visual-first mTeen Instagram post."""

    theme: str = Field(min_length=3, max_length=120)
    hook: str = Field(min_length=8, max_length=110)
    items: list[str] = Field(min_length=4, max_length=7)
    caption: str = Field(min_length=40, max_length=1200)
    hashtags: str = Field(min_length=3, max_length=300)
    alt_text: str = Field(min_length=10, max_length=500)
    image_prompt: str = Field(min_length=10, max_length=700)
    cta: str = Field(min_length=5, max_length=300)

    @field_validator("items")
    @classmethod
    def validate_items(cls, items: list[str]) -> list[str]:
        cleaned = [item.strip() for item in items if item.strip()]
        if len(cleaned) != len(items):
            raise ValueError("items cannot be blank")
        if any(len(item) > 70 for item in cleaned):
            raise ValueError("each item must be 70 characters or fewer")
        return cleaned

    @field_validator("hashtags")
    @classmethod
    def validate_hashtags(cls, hashtags: str) -> str:
        tags = hashtags.split()
        if not 3 <= len(tags) <= 8 or any(not tag.startswith("#") for tag in tags):
            raise ValueError("hashtags must contain 3 to 8 space-separated hashtags")
        return hashtags

    @field_validator("hook", "caption")
    @classmethod
    def reject_treatment_promises(cls, value: str) -> str:
        pattern = r"\b(?:cures?|heals?|fixes?)\s+(?:your|the)\s+(?:nervous system|anxiety|depression|mental health)\b"
        if re.search(pattern, value, flags=re.IGNORECASE):
            raise ValueError("content cannot promise to cure, heal, or fix a health condition")
        return value
