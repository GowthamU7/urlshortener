import time
import os
from fastapi import FastAPI, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine, get_db
from .redis_client import redis_client
from . import schemas, crud, utils

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")

for attempt in range(10):
    try:
        Base.metadata.create_all(bind=engine)
        break
    except OperationalError:
        print(f"Database not ready, retrying... ({attempt + 1}/10)")
        time.sleep(3)
else:
    raise Exception("Could not connect to the database after multiple attempts")

app = FastAPI(title="Scalable URL Shortener API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://urlshortener-7axa.onrender.com/",
        "https://urlshortener-fe-imyv.vercel.app/"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def log_click_event_background(short_code: str, ip_address=None, user_agent=None, referrer=None):
    db_generator = get_db()
    db = next(db_generator)

    try:
        db_url = crud.get_url_by_code(db, short_code)
        if db_url:
            crud.log_click_event(
                db=db,
                url_obj=db_url,
                ip_address=ip_address,
                user_agent=user_agent,
                referrer=referrer
            )
    finally:
        db.close()


@app.get("/")
def root():
    return {"message": "Scalable URL Shortener API is running"}


@app.post("/shorten", response_model=schemas.URLResponse)
def shorten_url(payload: schemas.URLCreate, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_key = f"rate_limit:shorten:{client_ip}"
    utils.check_rate_limit(redis_client, rate_limit_key, limit=5, window_seconds=60)

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


@app.get("/analytics/{short_code}", response_model=schemas.URLAnalyticsResponse)
def get_url_analytics(short_code: str, db: Session = Depends(get_db)):
    db_url = crud.get_url_by_code(db, short_code)

    if not db_url:
        raise HTTPException(status_code=404, detail="Short URL not found or expired")

    events = crud.get_recent_click_events(db, short_code)

    return {
        "short_code": db_url.short_code,
        "original_url": db_url.original_url,
        "total_clicks": db_url.click_count,
        "recent_events": events
    }


@app.get("/{short_code}")
def redirect_to_original(
    short_code: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_key = f"rate_limit:redirect:{client_ip}"
    utils.check_rate_limit(redis_client, rate_limit_key, limit=20, window_seconds=60)

    cached_url = redis_client.get(short_code)

    db_url = crud.get_url_by_code(db, short_code)
    if not db_url:
        raise HTTPException(status_code=404, detail="Short URL not found or expired")

    ip_address = client_ip
    user_agent = request.headers.get("user-agent")
    referrer = request.headers.get("referer")

    crud.increment_click_count(db, db_url)

    background_tasks.add_task(
        log_click_event_background,
        short_code,
        ip_address,
        user_agent,
        referrer
    )

    if cached_url:
        return RedirectResponse(url=cached_url)

    redis_client.setex(short_code, 3600, db_url.original_url)
    return RedirectResponse(url=db_url.original_url)
