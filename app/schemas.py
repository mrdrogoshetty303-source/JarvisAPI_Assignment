from pydantic import BaseModel, ConfigDict
from datetime import datetime, date
from typing import Optional


class NewsArticleBase(BaseModel):
    source_name: Optional[str] = None
    author: Optional[str] = None
    title: str
    description: Optional[str] = None
    url: str
    published_at: datetime
    content: Optional[str] = None


class NewsArticleCreate(NewsArticleBase):
    pass


class NewsArticleResponse(NewsArticleBase):
    id: int
    published_date: date
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
