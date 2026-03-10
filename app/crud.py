from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timezone
from .models import URLMap
from .utils import generate_short_code


def create_short_url(db: Session, original_url: str, custom_alias: str = None, expires_at=None):
    existing_url = db.query(URLMap).filter(
        and_(
            URLMap.original_url == str(original_url),
            URLMap.is_active == True
        )
    ).first()

    if existing_url and custom_alias is None:
        return existing_url

    if custom_alias:
        existing_alias = db.query(URLMap).filter(URLMap.short_code == custom_alias).first()
        if existing_alias:
            return None

        short_code = custom_alias
    else:
        short_code = generate_short_code()
        while db.query(URLMap).filter(URLMap.short_code == short_code).first():
            short_code = generate_short_code()

    db_url = URLMap(
        original_url=str(original_url),
        short_code=short_code,
        expires_at=expires_at
    )

    db.add(db_url)
    db.commit()
    db.refresh(db_url)

    return db_url


def get_url_by_code(db: Session, short_code: str):
    url = (
        db.query(URLMap)
        .filter(URLMap.short_code == short_code, URLMap.is_active == True)
        .first()
    )

    if not url:
        return None

    if url.expires_at:
        now = datetime.now(timezone.utc)
        expires_at = url.expires_at

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at < now:
            url.is_active = False
            db.commit()
            return None

    return url


def increment_click_count(db: Session, url_obj: URLMap):
    url_obj.click_count += 1
    db.commit()
    db.refresh(url_obj)
    return url_obj