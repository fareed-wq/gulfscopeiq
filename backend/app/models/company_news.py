from pydantic import BaseModel
from typing import Optional

class NewsArticle(BaseModel):
    title: str
    url: str
    publisher: Optional[str] = None
    published_at: Optional[str] = None
    confidence: str
