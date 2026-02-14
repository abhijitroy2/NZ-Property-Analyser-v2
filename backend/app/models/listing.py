from sqlalchemy import Column, Integer, String, Float, Text, DateTime, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class Listing(Base):
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(String, unique=True, index=True, nullable=False)

    # Basic info
    title = Column(String, default="")
    address = Column(String, default="")
    full_address = Column(String, default="")
    suburb = Column(String, default="", index=True)
    district = Column(String, default="", index=True)
    region = Column(String, default="", index=True)
    geographic_location = Column(String, default="")

    # Property details
    bedrooms = Column(Integer, nullable=True)
    bathrooms = Column(Integer, nullable=True)
    land_area = Column(Float, nullable=True)
    floor_area = Column(Float, nullable=True)
    capital_value = Column(String, default="")
    property_type = Column(String, default="")  # house, unit, apartment, etc.
    title_type = Column(String, default="")  # freehold, unit title, leasehold, cross-lease

    # Pricing
    display_price = Column(String, default="")
    asking_price = Column(Float, nullable=True)  # Parsed numeric price
    estimated_market_price = Column(String, default="")
    estimated_weekly_rent = Column(String, default="")

    # Content
    description = Column(Text, default="")
    property_url = Column(String, default="")
    photos = Column(JSON, default=list)  # List of photo URLs

    # Nearby / comparable sales
    nearby_properties = Column(JSON, default=list)  # Structured nearby property data

    # Listing metadata
    listing_date = Column(DateTime, nullable=True)
    source_url = Column(String, default="")  # The search URL this came from

    # Pipeline status
    filter_status = Column(String, default="pending", index=True)  # pending, passed, rejected
    filter_rejection_reason = Column(String, default="")
    analysis_status = Column(String, default="pending", index=True)  # pending, in_progress, completed, failed

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    analysis = relationship("Analysis", back_populates="listing", uselist=False, cascade="all, delete-orphan")
    portfolio_entry = relationship("PortfolioEntry", back_populates="listing", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Listing {self.listing_id}: {self.address}>"
