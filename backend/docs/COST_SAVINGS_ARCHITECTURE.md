# Cost-Saving Architecture

Token and API cost minimisation across the NZ Property Finder pipeline.

## Implemented

### 1. Vision / OpenAI Cache

**Impact: High** – OpenAI vision calls are the primary variable cost.

- **Storage**: `Analysis.vision_photos_hash` stores a hash of the photo URLs used.
- **Logic**: Before calling the vision API, the pipeline checks if `image_analysis` exists and `vision_photos_hash` matches the current photos.
- **Effect**: Re-analysis on the same listing with unchanged photos reuses cached vision results and skips the API call.

### 2. Subdivision Analysis Cache

**Impact: Medium** – Subdivision uses Google Maps geocoding and zone API.

- **Storage**: `Analysis.subdivision_input_hash` stores a hash of (address, district, region, land_area).
- **Logic**: Before calling subdivision analysis, the pipeline checks if results exist and the input hash matches.
- **Effect**: Re-analysis with unchanged location/land reuses cached subdivision results and avoids geocoding and zone lookups.

## Future Opportunities

| Component      | Cost Type              | Cache Key                          | Notes                                           |
|----------------|------------------------|------------------------------------|-------------------------------------------------|
| Council rates  | Low (in-memory today)  | address + district                 | Only relevant when real council APIs are used.  |
| Insurance      | Varies (mock default)  | address                            | Cache by address when real Initio API is added. |
| Stats NZ       | Low (fallback to static)| territorial_authority + year       | Optional in-memory cache for population.       |

## Rate Limiting

- **Scheduled job**: Set `ENABLE_SCHEDULER=true` to run the pipeline daily in the background (e.g. 9:30 AM).
- **Vision throttle**: When `VISION_PROVIDER=openai`, `VISION_RATE_LIMIT_DELAY_SECONDS` (default 65) adds a delay between listings that pass filters. Keeps usage under OpenAI's 200k tokens/minute (TPM) limit (~153k tokens per vision call).

## Token Tracking

- Logs are written to `backend/logs/app.log` (and console).
- Each vision call logs: `OpenAI multi-image: prompt_tokens=X completion_tokens=Y total_tokens=Z`.
- Search the log for `prompt_tokens` or `total_tokens` to track usage per run.

## Configuration Tips

- Use `VISION_PROVIDER=openai` with `gpt-4o-mini` for cheaper vision calls.
- Use `ANALYSIS_MODE=openai_deep` to get cost and timeline in a single vision call.
- Re-analyze listings only when inputs change; cached results will be reused where possible.
