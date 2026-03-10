from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import os

from .database import Base, engine, get_db
from .redis_client import redis_client
from . import schemas, crud, utils

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Scalable URL Shortener API")


@app.get("/")
def root():
    return {"message": "Scalable URL Shortener API is running"}


@app.post("/shorten", response_model=schemas.URLResponse)
def shorten_url(payload: schemas.URLCreate, db: Session = Depends(get_db)):
    if payload.custom_alias and not utils.is_valid_alias(payload.custom_alias):
        raise HTTPException(
            status_code=400,
            detail="Custom alias can only contain letters, numbers, hyphens, and underscores"
        )

    db_url = crud.create_short_url(
        db=db,
        original_url=payload.original_url,
        custom_alias=payload.custom_alias,
        expires_at=payload.expires_at
    )

    if db_url is None:
        raise HTTPException(status_code=400, detail="Custom alias already exists")

    return {
        "original_url": db_url.original_url,
        "short_code": db_url.short_code,
        "short_url": f"{BASE_URL}/{db_url.short_code}",
        "expires_at": db_url.expires_at
    }


@app.get("/info/{short_code}", response_model=schemas.URLInfo)
def get_url_info(short_code: str, db: Session = Depends(get_db)):
    db_url = crud.get_url_by_code(db, short_code)

    if not db_url:
        raise HTTPException(status_code=404, detail="Short URL not found or expired")

    return db_url


@app.get("/{short_code}")
def redirect_to_original(short_code: str, db: Session = Depends(get_db)):
    cached_url = redis_client.get(short_code)
    if cached_url:
        db_url = crud.get_url_by_code(db, short_code)
        if db_url:
            crud.increment_click_count(db, db_url)
        return RedirectResponse(url=cached_url)

    db_url = crud.get_url_by_code(db, short_code)

    if not db_url:
        raise HTTPException(status_code=404, detail="Short URL not found or expired")

    redis_client.setex(short_code, 3600, db_url.original_url)

    crud.increment_click_count(db, db_url)
    return RedirectResponse(url=db_url.original_url)