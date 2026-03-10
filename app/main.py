from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import os

from .database import Base, engine, get_db
from . import models, schemas, crud

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")

Base.metadata.create_all(bind=engine)

app = FastAPI(title="URL Shortener API")


@app.get("/")
def root():
    return {"message": "URL Shortener API is running"}


@app.post("/shorten", response_model=schemas.URLResponse)
def shorten_url(payload: schemas.URLCreate, db: Session = Depends(get_db)):
    db_url = crud.create_short_url(db, payload.original_url)

    return {
        "original_url": db_url.original_url,
        "short_code": db_url.short_code,
        "short_url": f"{BASE_URL}/{db_url.short_code}"
    }


@app.get("/info/{short_code}", response_model=schemas.URLInfo)
def get_url_info(short_code: str, db: Session = Depends(get_db)):
    db_url = crud.get_url_by_code(db, short_code)

    if not db_url:
        raise HTTPException(status_code=404, detail="Short URL not found")

    return db_url


@app.get("/{short_code}")
def redirect_to_original(short_code: str, db: Session = Depends(get_db)):
    db_url = crud.get_url_by_code(db, short_code)

    if not db_url:
        raise HTTPException(status_code=404, detail="Short URL not found")

    crud.increment_click_count(db, db_url)

    return RedirectResponse(url=db_url.original_url)