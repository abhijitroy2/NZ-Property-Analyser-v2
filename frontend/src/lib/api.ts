const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `API Error: ${res.status}`);
  }
  return res.json();
}

// ===== Listings =====
import type {
  ListingListResponse,
  Listing,
  Analysis,
  PropertyReport,
  ScenarioRequest,
  ScenarioResponse,
  DashboardSummary,
  TopDeal,
  PortfolioEntry,
  WatchlistItem,
} from "@/types";

export async function getListings(params?: Record<string, string>): Promise<ListingListResponse> {
  const qs = params ? "?" + new URLSearchParams(params).toString() : "";
  return fetchAPI<ListingListResponse>(`/listings${qs}`);
}

export async function getListing(id: number): Promise<Listing> {
  return fetchAPI<Listing>(`/listings/${id}`);
}

export async function getRegions(): Promise<{ region: string; count: number }[]> {
  return fetchAPI(`/listings/regions/list`);
}

// ===== Analysis =====
export async function getAnalysis(listingId: number): Promise<Analysis> {
  return fetchAPI<Analysis>(`/analysis/${listingId}`);
}

export async function runScenario(listingId: number, scenario: ScenarioRequest): Promise<ScenarioResponse> {
  return fetchAPI<ScenarioResponse>(`/analysis/${listingId}/scenario`, {
    method: "POST",
    body: JSON.stringify(scenario),
  });
}

export async function getPropertyReport(listingId: number): Promise<PropertyReport> {
  return fetchAPI<PropertyReport>(`/analysis/${listingId}/report`);
}

// ===== Dashboard =====
export async function getDashboardSummary(): Promise<DashboardSummary> {
  return fetchAPI<DashboardSummary>(`/dashboard/summary`);
}

export async function getTopDeals(limit = 5): Promise<TopDeal[]> {
  return fetchAPI<TopDeal[]>(`/dashboard/top-deals?limit=${limit}`);
}

export async function getStatsByRegion(): Promise<any[]> {
  return fetchAPI(`/dashboard/stats-by-region`);
}

// ===== Pipeline =====
export async function runPipeline(): Promise<{ status: string; message: string }> {
  return fetchAPI(`/pipeline/run`, { method: "POST" });
}

export async function runScrapeOnly(): Promise<{ status: string; message: string }> {
  return fetchAPI(`/pipeline/scrape`, { method: "POST" });
}

export async function runAnalyzeOnly(): Promise<{ status: string; message: string }> {
  return fetchAPI(`/pipeline/analyze`, { method: "POST" });
}

export async function analyzeSingleListing(id: number): Promise<{ status: string; message: string }> {
  return fetchAPI(`/pipeline/analyze/${id}`, { method: "POST" });
}

// ===== Portfolio =====
export async function getPortfolio(): Promise<PortfolioEntry[]> {
  return fetchAPI<PortfolioEntry[]>(`/portfolio`);
}

export async function addToPortfolio(listingId: number, status = "watching"): Promise<PortfolioEntry> {
  return fetchAPI<PortfolioEntry>(`/portfolio`, {
    method: "POST",
    body: JSON.stringify({ listing_id: listingId, status }),
  });
}

export async function updatePortfolioEntry(
  entryId: number,
  data: Partial<PortfolioEntry>
): Promise<PortfolioEntry> {
  return fetchAPI<PortfolioEntry>(`/portfolio/${entryId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deletePortfolioEntry(entryId: number): Promise<void> {
  return fetchAPI(`/portfolio/${entryId}`, { method: "DELETE" });
}

// ===== Watchlist =====
export async function getWatchlist(): Promise<WatchlistItem[]> {
  return fetchAPI<WatchlistItem[]>(`/watchlist`);
}

export async function createWatchlistItem(data: {
  name: string;
  search_criteria: Record<string, any>;
  alert_enabled?: boolean;
}): Promise<WatchlistItem> {
  return fetchAPI<WatchlistItem>(`/watchlist`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateWatchlistItem(
  id: number,
  data: Partial<WatchlistItem>
): Promise<WatchlistItem> {
  return fetchAPI<WatchlistItem>(`/watchlist/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteWatchlistItem(id: number): Promise<void> {
  return fetchAPI(`/watchlist/${id}`, { method: "DELETE" });
}
