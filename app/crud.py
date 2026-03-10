from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timezone
from .models import URLMap, ClickEvent
from .utils import encode_base62


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

        db_url = URLMap(
            original_url=str(original_url),
            short_code=custom_alias,
            expires_at=expires_at
        )
        db.add(db_url)
        db.commit()
        db.refresh(db_url)
        return db_url

    # Step 1: create row with temporary placeholder
    db_url = URLMap(
        original_url=str(original_url),
        short_code="temp",
        expires_at=expires_at
    )
    db.add(db_url)
    db.commit()
    db.refresh(db_url)

    # Step 2: generate Base62 short code from DB id
    db_url.short_code = encode_base62(db_url.id)
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


def log_click_event(db: Session, url_obj: URLMap, ip_address=None, user_agent=None, referrer=None):
    click_event = ClickEvent(
        url_id=url_obj.id,
        short_code=url_obj.short_code,
        ip_address=ip_address,
        user_agent=user_agent,
        referrer=referrer
    )
    db.add(click_event)
    db.commit()
    db.refresh(click_event)
    return click_event


def get_recent_click_events(db: Session, short_code: str, limit: int = 10):
    return (
        db.query(ClickEvent)
        .filter(ClickEvent.short_code == short_code)
        .order_by(ClickEvent.clicked_at.desc())
        .limit(limit)
        .all()
    )