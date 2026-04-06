from pydantic import BaseModel, Field, field_validator, EmailStr
from typing import List, Optional
import re


class Post(BaseModel):
    title: str = Field(..., min_length=3, max_length=200, description="Post title")
    content: str = Field(..., min_length=10, description="Post body text")
    tags: List[str] = Field(..., min_length=1, max_length=10, description="1–10 tags")

    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, tags):
        if not tags:
            raise ValueError("A post must have at least one tag.")
        if len(tags) > 10:
            raise ValueError("A post cannot have more than 10 tags.")
        cleaned = []
        for tag in tags:
            tag = tag.strip().lower()
            if not tag:
                continue
            if not re.match(r'^[a-z0-9_-]+$', tag):
                raise ValueError(
                    f"Tag '{tag}' is invalid. Tags may only contain lowercase letters, "
                    "digits, hyphens, and underscores."
                )
            if len(tag) > 30:
                raise ValueError(f"Tag '{tag}' exceeds the 30-character limit.")
            cleaned.append(tag)
        if not cleaned:
            raise ValueError("Tags list must not be empty after cleaning.")
        return list(dict.fromkeys(cleaned))  # deduplicate while preserving order

    @field_validator("title", mode="before")
    @classmethod
    def strip_title(cls, v):
        return v.strip() if isinstance(v, str) else v

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "title": "Learning FastAPI",
                "content": "FastAPI is a modern, fast web framework…",
                "tags": ["python", "fastapi"]
            }
        }


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=32, pattern=r'^[a-zA-Z0-9_]+$')
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")

    @field_validator("username", mode="before")
    @classmethod
    def strip_username(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter.")
        return v


class UserInDB(BaseModel):
    username: str
    email: str
    hashed_password: str


class UserResponse(BaseModel):
    username: str
    email: str


class Token(BaseModel):
    access_token: str
    token_type: str


class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None
