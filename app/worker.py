from functools import lru_cache

import redis
from celery import Celery
from celery.schedules import crontab
from datetime import datetime, timezone, timedelta

from app.config import get_settings
from app.logger import setup_logger
from app.database import SessionLocal
from app.models import NewsArticle
from app.services.news_api import fetch_latest_news

logger = setup_logger("celery_worker")
settings = get_settings()

celery_app = Celery(
    "news_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Schedule the task to run every minute using celery beat
celery_app.conf.beat_schedule = {
    "fetch-news-every-minute": {
        "task": "app.worker.task_fetch_and_store_news",
        "schedule": crontab(minute="*"),  # Every minute
    }
}


@lru_cache()
def _redis_state_client():
    try:
        return redis.Redis.from_url(settings.CELERY_BROKER_URL, decode_responses=True)
    except Exception as e:
        logger.warning(f"Failed to initialize Redis state client: {str(e)}")
        return None


def _query_page_key(query_term: str) -> str:
    return f"news_query_page:{query_term.strip().lower()}"


def _get_query_page(query_term: str) -> int:
    client = _redis_state_client()
    if client is None:
        return 1

    try:
        value = client.get(_query_page_key(query_term))
        if value is None:
            return 1

        page = int(value)
        return page if page > 0 else 1
    except Exception as e:
        logger.warning(
            f"Failed to read page state for query '{query_term}', defaulting to page 1: {str(e)}"
        )
        return 1


def _set_next_query_page(query_term: str, current_page: int) -> None:
    client = _redis_state_client()
    if client is None:
        return

    next_page = max(1, current_page) + 1
    try:
        client.set(_query_page_key(query_term), next_page)
    except Exception as e:
        logger.warning(
            f"Failed to update page state for query '{query_term}' to {next_page}: {str(e)}"
        )


def _select_query_term() -> str:
    terms = settings.QUERY_TERMS
    client = _redis_state_client()

    if client is None:
        return terms[0]

    current_count = client.incr("news_topic_counter")
    idx = current_count % len(terms)

    return terms[idx]


# this the the task worker has to do
@celery_app.task
def task_fetch_and_store_news():

    query_term = _select_query_term()
    page = _get_query_page(query_term)

    logger.info(
        f"Starting background task: fetch and store news for query '{query_term}' page {page}."
    )
    articles = fetch_latest_news(query=query_term, page=page)

    # increse the page number
    _set_next_query_page(query_term, page)

    if not articles:
        logger.warning(f"No articles fetched for query '{query_term}' page {page}.")
        return "No articles fetched."

    db = SessionLocal()
    try:
        new_count = 0
        for item in articles:
            exists = (
                db.query(NewsArticle).filter(NewsArticle.url == item.get("url")).first()
            )
            if not exists:

                published_at_str = item.get("publishedAt")
                ist_offset = timedelta(hours=5, minutes=30)
                ist_timezone = timezone(ist_offset)
                published_at = datetime.now(ist_timezone)

                if published_at_str:
                    try:
                        utc_time = datetime.strptime(
                            published_at_str, "%Y-%m-%dT%H:%M:%SZ"
                        ).replace(tzinfo=timezone.utc)
                        published_at = utc_time.astimezone(ist_timezone)
                    except ValueError:
                        pass

                article = NewsArticle(
                    source_name=item.get("source", {}).get("name"),
                    author=item.get("author"),
                    title=item.get("title"),
                    description=item.get("description"),
                    url=item.get("url"),
                    published_at=published_at,
                    published_date=published_at.date(),
                    content=item.get("content"),
                )
                db.add(article)
                new_count += 1

        db.commit()
        logger.info(
            f"Successfully stored {new_count} new articles for query '{query_term}' page {page}."
        )
        return f"Stored {new_count} new articles."
    except Exception as e:
        db.rollback()
        logger.exception(f"Database error while saving articles: {str(e)}")
        raise
    finally:
        db.close()
