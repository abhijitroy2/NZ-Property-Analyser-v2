from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean
from datetime import datetime, timezone
from app.database import Base


class WatchlistItem(Base):
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    search_criteria = Column(JSON, default=dict)  # Saved filter criteria
    alert_enabled = Column(Boolean, default=True)
    last_alerted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<WatchlistItem {self.name}>"
