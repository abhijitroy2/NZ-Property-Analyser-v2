from sqlalchemy import Column, Integer, String, Float, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class PortfolioEntry(Base):
    __tablename__ = "portfolio"

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=False)

    # Status tracking
    status = Column(String, default="watching")  # watching, offered, purchased, renovating, selling, renting, sold

    # Actual financials (filled in as deal progresses)
    purchase_price = Column(Float, nullable=True)
    actual_reno_cost = Column(Float, nullable=True)
    actual_sale_price = Column(Float, nullable=True)
    actual_weekly_rent = Column(Float, nullable=True)

    # Comparison with projections
    projected_reno_cost = Column(Float, nullable=True)
    projected_arv = Column(Float, nullable=True)
    projected_weekly_rent = Column(Float, nullable=True)
    projected_roi = Column(Float, nullable=True)

    notes = Column(Text, default="")

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    listing = relationship("Listing", back_populates="portfolio_entry")

    def __repr__(self):
        return f"<PortfolioEntry listing={self.listing_id} status={self.status}>"
