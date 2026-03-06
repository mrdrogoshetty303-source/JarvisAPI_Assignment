from sqlalchemy import Column, Integer, String, Text, DateTime, Date
from sqlalchemy.sql import func
from app.database import Base

class NewsArticle(Base):
    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True, index=True)
    source_name = Column(String(255), nullable=True)
    author = Column(String(255), nullable=True)
    title = Column(String(255), index=True)
    description = Column(Text, nullable=True)
    url = Column(String(700), unique=True, index=True)
    published_at = Column(DateTime, index=True)
    content = Column(Text, nullable=True)
    
    # Store date component separately for easy querying
    published_date = Column(Date, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
