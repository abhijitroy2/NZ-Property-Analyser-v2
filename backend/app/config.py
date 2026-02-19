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

    # Analysis mode: "legacy" (rule-based reno/timeline) | "openai_deep" (vision returns cost+timetable)
    analysis_mode: str = "legacy"
    openai_decision_reasoning: bool = False  # Optional LLM explanation; keep rule-based decision

    # AI Vision
    vision_provider: str = "mock"  # "openai", "anthropic", "google", "vertex", "mock"
    openai_api_key: Optional[str] = None
    openai_vision_model: str = "gpt-4o-mini"
    openai_summary_model: str = "gpt-4o-mini"
    anthropic_api_key: Optional[str] = None
    google_vision_credentials: Optional[str] = None  # Path to Google service account JSON key file
    # Vertex AI Gemini (for VISION_PROVIDER=vertex)
    google_cloud_project: Optional[str] = None
    google_cloud_location: str = "us-central1"

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
    enable_scheduler: bool = False  # Set true to run pipeline daily in background
    scheduler_hour: int = 7  # Hour (24h) for daily run
    scheduler_minute: int = 0  # Minute for daily run

    # Vision rate limit: seconds to wait between listings when using OpenAI (avoids 200k TPM)
    vision_rate_limit_delay_seconds: int = 65  # ~153k tokens/call; 65s keeps under 200k/min

    # CORS
    frontend_url: str = "http://localhost:3000"

    # Logging
    log_file: str = "logs/app.log"  # Path relative to backend dir; empty to disable file logging

    @property
    def search_urls(self) -> List[str]:
        if not self.trademe_search_urls:
            return []
        return [u.strip() for u in self.trademe_search_urls.split(",") if u.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
