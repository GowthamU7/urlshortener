from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime
from typing import Optional


class URLCreate(BaseModel):
    original_url: HttpUrl
    custom_alias: Optional[str] = Field(default=None, min_length=3, max_length=20)
    expires_at: Optional[datetime] = None


class URLResponse(BaseModel):
    original_url: str
    short_code: str
    short_url: str
    expires_at: Optional[datetime] = None


class URLInfo(BaseModel):
    original_url: str
    short_code: str
    click_count: int
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool

    class Config:
        from_attributes = True