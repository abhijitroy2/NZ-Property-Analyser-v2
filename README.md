# NZ Property Finder

A full-stack NZ property investment evaluation system that automatically scans TradeMe listings, runs a 3-stage analysis pipeline (filters, deep analysis, financial modeling), scores and ranks properties, and presents results in an interactive web dashboard.

## Features

- **Automated TradeMe Scraping** - Pulls property listings from TradeMe search URLs
- **3-Stage Pipeline**:
  - **Stage 1: Hard Filters** - Price, title type, population, property type
  - **Stage 2: Deep Analysis** - Insurance, AI image analysis, renovation costs, ARV, rental income, council rates, subdivision potential
  - **Stage 3: Financial Models** - Flip ROI, rental yield, strategy decision
- **Composite Scoring** - Weighted scoring (ROI 40%, timeline 15%, confidence 15%, subdivision 15%, location 10%, insurance 5%)
- **Interactive Dashboard** - Top deals, stats, filters, property detail with scenario modeling sliders
- **Portfolio Tracking** - Track properties through your pipeline, compare actual vs projected
- **Saved Searches & Alerts** - Email notifications when matching properties appear
- **AI Vision Analysis** - Optional OpenAI/Claude photo analysis for renovation assessment

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, SQLite
- **Frontend**: Next.js 14, TypeScript, Tailwind CSS
- **External APIs**: TradeMe (public), Stats NZ, Tenancy.govt.nz, Council APIs, AI Vision (optional)

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- pip (Python package manager)

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file from template
copy .env.example .env    # Windows
# cp .env.example .env    # macOS/Linux

# Edit .env with your settings (at minimum, set TRADEME_SEARCH_URLS)

# Start the server
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

### 3. Open the Dashboard

Visit **http://localhost:3000** in your browser.

### 4. Run the Pipeline

Either:
- Click the green **"Run Pipeline"** button in the top-right of the dashboard
- Or go to **Settings** page and click individual pipeline steps
- Or call the API directly: `POST http://localhost:8000/api/pipeline/run`

## Configuration

All settings are managed via `backend/.env`. Key settings:

| Variable | Description | Default |
|----------|-------------|---------|
| `TRADEME_SEARCH_URLS` | Comma-separated TradeMe search URLs to scrape | *(empty)* |
| `MAX_PRICE` | Maximum property price filter | `500000` |
| `MIN_POPULATION` | Minimum population in territorial authority | `50000` |
| `ANALYSIS_MODE` | Analysis path: `legacy` (rule-based reno/timeline) or `openai_deep` (vision returns cost+timetable) | `legacy` |
| `VISION_PROVIDER` | AI image analysis: `openai`, `anthropic`, or `mock` | `mock` |
| `OPENAI_API_KEY` | OpenAI API key (for GPT-4V image analysis) | *(empty)* |
| `ANTHROPIC_API_KEY` | Anthropic API key (for Claude Vision) | *(empty)* |
| `ENABLE_SCHEDULER` | Auto-run pipeline daily in background | `false` |
| `SCHEDULER_HOUR` | Hour to run daily pipeline (24h) | `7` |
| `VISION_RATE_LIMIT_DELAY_SECONDS` | Seconds between listings when using OpenAI vision (avoids 200k TPM) | `65` |
| `SMTP_USERNAME` | Email username for alerts | *(empty)* |
| `EMAIL_TO` | Email recipient for daily digests | *(empty)* |
| `INSURANCE_PROVIDER` | Insurance quote provider: real or `mock` | `mock` |
| `LOG_FILE` | Log file path (relative to backend/; empty to disable). Rotating, 5MB×5 backups | `logs/app.log` |

### Scheduled Pipeline

To run the pipeline daily in the background without hitting API rate limits:

1. Set `ENABLE_SCHEDULER=true` in `.env`
2. Set `VISION_RATE_LIMIT_DELAY_SECONDS=65` (or higher) when using `VISION_PROVIDER=openai`
3. Keep the backend server running (e.g. `uvicorn app.main:app` or run as a Windows service)

The scheduler runs at `SCHEDULER_HOUR:SCHEDULER_MINUTE` (default 7:00 AM). The rate-limit delay spaces out vision API calls to stay under OpenAI's 200k tokens/minute limit.

### Example TradeMe Search URLs

```
# Waikato under $400k
https://www.trademe.co.nz/a/property/residential/sale/waikato/search?price_min=250000&price_max=400000

# Multiple URLs (comma-separated)
https://www.trademe.co.nz/a/property/residential/sale/waikato/search?price_min=250000&price_max=400000,https://www.trademe.co.nz/a/property/residential/sale/bay-of-plenty/search?price_min=300000&price_max=500000
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/listings` | List properties (filtered, paginated) |
| `GET` | `/api/listings/{id}` | Single property detail |
| `GET` | `/api/analysis/{id}` | Full analysis for a property |
| `POST` | `/api/analysis/{id}/scenario` | Recalculate with custom inputs |
| `GET` | `/api/analysis/{id}/report` | Full property report |
| `GET` | `/api/dashboard/summary` | Dashboard summary stats |
| `GET` | `/api/dashboard/top-deals` | Top N deals by score |
| `POST` | `/api/pipeline/run` | Run full pipeline |
| `POST` | `/api/pipeline/scrape` | Scrape only |
| `POST` | `/api/pipeline/analyze` | Analyze pending only |
| `CRUD` | `/api/watchlist` | Saved searches |
| `CRUD` | `/api/portfolio` | Portfolio tracking |

## Project Structure

```
NZ Property Finder/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Settings from .env
│   │   ├── database.py          # SQLAlchemy setup
│   │   ├── models/              # DB models
│   │   ├── schemas/             # Pydantic schemas
│   │   ├── api/                 # REST API routes
│   │   ├── services/
│   │   │   ├── scraper/         # TradeMe scraper
│   │   │   ├── filters/         # Stage 1 hard filters
│   │   │   ├── analysis/        # Stage 2 deep analysis
│   │   │   ├── financial/       # Stage 3 financial models
│   │   │   ├── scoring/         # Composite scoring engine
│   │   │   ├── external/        # External API clients
│   │   │   ├── notifications/   # Email service
│   │   │   └── pipeline.py      # Main orchestrator
│   │   └── tasks/               # Scheduled jobs
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js pages
│   │   ├── components/          # UI components
│   │   ├── lib/                 # API client, utilities
│   │   └── types/               # TypeScript types
│   └── package.json
└── README.md
```

## How It Works

1. **Scraper** pulls listings from TradeMe search URLs
2. **Stage 1 Filters** reject listings that fail hard criteria (price, title type, population)
3. **Stage 2 Analysis** runs deep analysis on surviving listings:
   - AI vision analysis of photos (renovation assessment)
   - Renovation cost estimation
   - ARV estimation from comparable sales
   - Rental income estimation
   - Insurance check
   - Council rates lookup
   - Subdivision potential analysis
4. **Stage 3 Financial Models** calculate flip ROI and rental yield
5. **Scoring Engine** generates composite scores and assigns verdicts
6. **Dashboard** presents ranked results with interactive scenario modeling

## Design & Architecture

### Analysis Mode (Fork)

Two analysis paths for renovation and timeline:

- **`legacy`** (default): Vision returns condition signals; `renovation.py` and `timeline.py` compute cost and weeks from rules.
- **`openai_deep`**: Vision prompt returns `estimated_renovation_cost_nzd` and `estimated_timeline_weeks` directly; legacy modules are skipped. Use with `VISION_PROVIDER=openai`.

### Cost-Saving Caches

- **Vision cache**: Cached vision results reused when listing photos are unchanged (`Analysis.vision_photos_hash`).
- **Subdivision cache**: Cached subdivision results reused when address/district/region/land_area are unchanged (`Analysis.subdivision_input_hash`).

See [backend/docs/COST_SAVINGS_ARCHITECTURE.md](backend/docs/COST_SAVINGS_ARCHITECTURE.md) for details and future opportunities.

### Logging & Token Tracking

- Logs go to both console and `backend/logs/app.log` (rotating, 5MB×5 backups).
- OpenAI token usage is logged per vision call: `OpenAI multi-image: prompt_tokens=X completion_tokens=Y total_tokens=Z`.
- Search the log for `prompt_tokens` or `total_tokens` to track usage.

### URL Sources for Scraping

- **Primary**: Database `search_urls` table (managed in Settings).
- **Fallback**: `TRADEME_SEARCH_URLS` in `.env` (comma-separated).
- `input.txt` is written for external TM-scraper; the pipeline does not read from it.

## Notes

- The system works out of the box with mock/estimated data for external APIs
- For more accurate analysis, configure real API keys (AI Vision, Google Maps, etc.)
- Insurance, council rates, and tenancy data use conservative estimates by default
- Image analysis defaults to "MODERATE" renovation when no AI vision is configured
- TradeMe scraping uses public API endpoints (no authentication required)
