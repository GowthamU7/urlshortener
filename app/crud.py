from sqlalchemy.orm import Session
from .models import URLMap
from .utils import generate_short_code


def create_short_url(db: Session, original_url: str):
    short_code = generate_short_code()

    while db.query(URLMap).filter(URLMap.short_code == short_code).first():
        short_code = generate_short_code()

    db_url = URLMap(
        original_url=str(original_url),
        short_code=short_code
    )

    db.add(db_url)
    db.commit()
    db.refresh(db_url)

    return db_url


def get_url_by_code(db: Session, short_code: str):
    return (
        db.query(URLMap)
        .filter(URLMap.short_code == short_code, URLMap.is_active == True)
        .first()
    )


def increment_click_count(db: Session, url_obj: URLMap):
    url_obj.click_count += 1
    db.commit()
    db.refresh(url_obj)
    return url_obj