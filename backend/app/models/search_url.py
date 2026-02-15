from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from datetime import datetime, timezone
from app.database import Base


class SearchURL(Base):
    __tablename__ = "search_urls"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(Text, nullable=False)
    label = Column(String, default="")  # Optional friendly name
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<SearchURL {self.id}: {self.label or self.url[:60]}>"
