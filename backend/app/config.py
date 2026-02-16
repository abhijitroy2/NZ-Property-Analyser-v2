from pydantic_settings import BaseSettings
from typing import Optional, List


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./nz_property_finder.db"

    # TradeMe
    trademe_search_urls: str = ""

    # Filters
    max_price: int = 500000
    min_population: int = 50000

    # AI Vision
    vision_provider: str = "mock"  # "openai", "anthropic", "google", "mock"
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_vision_credentials: Optional[str] = None  # Path to Google service account JSON key file

    # Google Maps
    google_maps_api_key: Optional[str] = None

    # Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    email_from: Optional[str] = None
    email_to: Optional[str] = None

    # Insurance
    insurance_provider: str = "mock"

    # Subdivision
    subdivision_use_council_rules: bool = True  # Use council zone APIs and rules when in scope

    # Scheduler
    enable_scheduler: bool = False
    scheduler_hour: int = 7
    scheduler_minute: int = 0

    # CORS
    frontend_url: str = "http://localhost:3000"

    @property
    def search_urls(self) -> List[str]:
        if not self.trademe_search_urls:
            return []
        return [u.strip() for u in self.trademe_search_urls.split(",") if u.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
