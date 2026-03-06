import requests

from app.config import get_settings
from app.logger import setup_logger

logger = setup_logger("news_api_service")
settings = get_settings()

BASE_URL = "https://newsapi.org/v2/everything"


def fetch_latest_news(query: str, page: int = 1):
    """
    Fetches articles from News API /v2/everything using query text and page.
    """
    if not settings.NEWS_API_KEY:
        logger.error("NEWS_API_KEY is not set in environment or config.")
        return []

    if not query:
        logger.error("Query term is empty; cannot fetch from News API.")
        return []

    page = max(1, int(page))
    params = {"q": query, "page": page, "apiKey": settings.NEWS_API_KEY}

    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        if data.get("status") == "ok":
            articles = data.get("articles", [])
            logger.info(
                f"Fetched {len(articles)} articles (totalResults={data.get('totalResults', 0)}) for query '{query}' page {page}."
            )
            return articles

        logger.error(f"News API returned error for query '{query}' page {page}: {data}")
        return []

    except requests.exceptions.RequestException as e:
        logger.error(
            f"Failed to fetch news from API for query '{query}' page {page}: {str(e)}"
        )
        return []