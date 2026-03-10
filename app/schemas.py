from pydantic import BaseModel, HttpUrl
from datetime import datetime


class URLCreate(BaseModel):
    original_url: HttpUrl


class URLResponse(BaseModel):
    original_url: str
    short_code: str
    short_url: str


class URLInfo(BaseModel):
    original_url: str
    short_code: str
    click_count: int
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True