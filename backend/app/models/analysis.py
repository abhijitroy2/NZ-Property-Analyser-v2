from sqlalchemy import Column, Integer, String, Float, Text, DateTime, JSON, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("listings.id"), unique=True, nullable=False)

    # Stage 1: Filter results
    population_data = Column(JSON, nullable=True)
    demand_profile = Column(JSON, nullable=True)

    # Stage 2: Deep analysis
    insurability = Column(JSON, nullable=True)
    image_analysis = Column(JSON, nullable=True)
    renovation_estimate = Column(JSON, nullable=True)
    timeline_estimate = Column(JSON, nullable=True)
    arv_estimate = Column(JSON, nullable=True)
    rental_estimate = Column(JSON, nullable=True)
    council_rates = Column(JSON, nullable=True)
    subdivision_analysis = Column(JSON, nullable=True)

    # Stage 3: Financial models
    flip_financials = Column(JSON, nullable=True)
    rental_financials = Column(JSON, nullable=True)
    strategy_decision = Column(JSON, nullable=True)

    # Scoring
    composite_score = Column(Float, nullable=True)
    component_scores = Column(JSON, nullable=True)
    verdict = Column(String, default="")  # STRONG_BUY, BUY, MAYBE, PASS
    rank = Column(Integer, nullable=True)

    # Flags and next steps
    flags = Column(JSON, default=list)
    next_steps = Column(JSON, default=list)
    confidence_level = Column(String, default="")  # HIGH, MEDIUM, LOW

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    listing = relationship("Listing", back_populates="analysis")

    def __repr__(self):
        return f"<Analysis listing={self.listing_id} score={self.composite_score} verdict={self.verdict}>"
