from fastapi import FastAPI, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from datetime import date
import time
from typing import List

from app.database import engine, Base, get_db
from app import models, schemas
from app.logger import setup_logger
import json
from fastapi.responses import Response

logger = setup_logger("fastapi_app")

# Create all database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="News API Application")

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    process_time_ms = round(process_time * 1000, 2)

    logger.info(
        f"Request: {request.method} {request.url.path} - Time: {process_time_ms}ms"
    )

    # this will check if response is in json by cheking its header
    if (
        hasattr(response, "headers")
        and response.headers.get("content-type") == "application/json"
    ):
        # This is needed to be done becasue in fast api server returns data in chunks
        #so we need to read every chunk before modifying
        body = [chunk async for chunk in response.body_iterator]
        body_bytes = b"".join(body)
        try:
            body_json = json.loads(body_bytes)
            if isinstance(body_json, dict):
                body_json["total_time_taken"] = f"{process_time_ms} ms"
            elif isinstance(body_json, list):
                body_json = {"data": body_json, "total_time_taken": f"{process_time_ms} ms"}

            modified_body_bytes = json.dumps(body_json).encode("utf-8")
            response = Response(
                content=modified_body_bytes,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type="application/json",
            )
            response.headers["content-length"] = str(len(modified_body_bytes))
        except Exception:
            logger.error("Failed to modify response JSON", exc_info=True)
            response = Response(
                content=body_bytes,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

    return response


@app.get("/news", response_model=List[schemas.NewsArticleResponse])
def get_news(date: date, db: Session = Depends(get_db)):
    logger.info(f"Fetching news for date: {date}")
    try:
        articles = (
            db.query(models.NewsArticle)
            .filter(models.NewsArticle.published_date == date)
            .all()
        )
        return articles
    except Exception as e:
        logger.error(f"Error fetching news from database: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


        
