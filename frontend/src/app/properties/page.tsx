"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { getListings, getRegions } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  formatCurrency,
  formatPercent,
  verdictColor,
  verdictLabel,
  strategyLabel,
  scoreColor,
  formatDate,
} from "@/lib/utils";
import type { Listing, ListingListResponse } from "@/types";
import {
  Search,
  BedDouble,
  MapPin,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  Filter,
} from "lucide-react";

export default function PropertiesPage() {
  const [data, setData] = useState<ListingListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [regions, setRegions] = useState<{ region: string; count: number }[]>([]);

  // Filters
  const [page, setPage] = useState(1);
  const [filterStatus, setFilterStatus] = useState("passed");
  const [verdict, setVerdict] = useState("");
  const [region, setRegion] = useState("");
  const [sortBy, setSortBy] = useState("composite_score");
  const [maxPrice, setMaxPrice] = useState("");
  const [minBedrooms, setMinBedrooms] = useState("");

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {
        page: String(page),
        page_size: "20",
        filter_status: filterStatus,
        sort_by: sortBy,
        sort_order: "desc",
      };
      if (verdict) params.verdict = verdict;
      if (region) params.region = region;
      if (maxPrice) params.max_price = maxPrice;
      if (minBedrooms) params.min_bedrooms = minBedrooms;

      const result = await getListings(params);
      setData(result);
    } catch (e) {
      console.error("Failed to fetch listings:", e);
    } finally {
      setLoading(false);
    }
  }, [page, filterStatus, verdict, region, sortBy, maxPrice, minBedrooms]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    getRegions().then(setRegions).catch(() => {});
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Properties</h1>
        <p className="text-sm text-[var(--muted-foreground)] mt-1">
          Browse and filter evaluated property listings
        </p>
      </div>

      {/* Filters Bar */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap items-center gap-3">
            <Filter className="h-4 w-4 text-[var(--muted-foreground)]" />

            <select
              value={filterStatus}
              onChange={(e) => { setFilterStatus(e.target.value); setPage(1); }}
              className="h-9 px-3 rounded-lg border border-[var(--border)] bg-[var(--card)] text-sm"
            >
              <option value="">All Statuses</option>
              <option value="passed">Passed Filters</option>
              <option value="rejected">Rejected</option>
              <option value="pending">Pending</option>
            </select>

            <select
              value={verdict}
              onChange={(e) => { setVerdict(e.target.value); setPage(1); }}
              className="h-9 px-3 rounded-lg border border-[var(--border)] bg-[var(--card)] text-sm"
            >
              <option value="">All Verdicts</option>
              <option value="STRONG_BUY">Strong Buy</option>
              <option value="BUY">Buy</option>
              <option value="MAYBE">Maybe</option>
              <option value="PASS">Pass</option>
            </select>

            <select
              value={region}
              onChange={(e) => { setRegion(e.target.value); setPage(1); }}
              className="h-9 px-3 rounded-lg border border-[var(--border)] bg-[var(--card)] text-sm"
            >
              <option value="">All Regions</option>
              {regions.map((r) => (
                <option key={r.region} value={r.region}>
                  {r.region} ({r.count})
                </option>
              ))}
            </select>

            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="h-9 px-3 rounded-lg border border-[var(--border)] bg-[var(--card)] text-sm"
            >
              <option value="composite_score">Sort: Score</option>
              <option value="asking_price">Sort: Price</option>
              <option value="listing_date">Sort: Listing Date</option>
              <option value="created_at">Sort: Added Date</option>
            </select>

            <input
              type="number"
              placeholder="Max Price"
              value={maxPrice}
              onChange={(e) => { setMaxPrice(e.target.value); setPage(1); }}
              className="h-9 w-28 px-3 rounded-lg border border-[var(--border)] bg-[var(--card)] text-sm"
            />

            <input
              type="number"
              placeholder="Min Beds"
              value={minBedrooms}
              onChange={(e) => { setMinBedrooms(e.target.value); setPage(1); }}
              className="h-9 w-20 px-3 rounded-lg border border-[var(--border)] bg-[var(--card)] text-sm"
            />
          </div>
        </CardContent>
      </Card>

      {/* Listings */}
      {loading ? (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--primary)] mx-auto" />
        </div>
      ) : !data || data.items.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <Search className="h-12 w-12 text-[var(--muted-foreground)] mx-auto mb-4" />
            <h3 className="font-semibold text-lg">No properties found</h3>
            <p className="text-sm text-[var(--muted-foreground)] mt-1">
              Try adjusting your filters or run the pipeline to import new listings.
            </p>
          </CardContent>
        </Card>
      ) : (
        <>
          <p className="text-sm text-[var(--muted-foreground)]">
            Showing {data.items.length} of {data.total} properties
          </p>

          <div className="space-y-3">
            {data.items.map((listing) => (
              <PropertyRow key={listing.id} listing={listing} />
            ))}
          </div>

          {/* Pagination */}
          {data.total_pages > 1 && (
            <div className="flex items-center justify-center gap-4">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
              >
                <ChevronLeft className="h-4 w-4" />
                Previous
              </Button>
              <span className="text-sm text-[var(--muted-foreground)]">
                Page {data.page} of {data.total_pages}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => p + 1)}
                disabled={page >= data.total_pages}
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function PropertyRow({ listing }: { listing: Listing }) {
  return (
    <Link href={`/properties/${listing.id}`}>
      <Card className="hover:border-[var(--primary)] hover:shadow-sm transition-all cursor-pointer">
        <CardContent className="p-4">
          <div className="flex items-start justify-between gap-4">
            {/* Left: Property info */}
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <h3 className="font-semibold truncate">{listing.full_address || listing.address || "No address"}</h3>
                {listing.verdict && (
                  <Badge
                    variant={
                      listing.verdict === "STRONG_BUY" || listing.verdict === "BUY"
                        ? "success"
                        : listing.verdict === "MAYBE"
                        ? "warning"
                        : "danger"
                    }
                    className="flex-shrink-0"
                  >
                    {verdictLabel(listing.verdict)}
                  </Badge>
                )}
              </div>

              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-sm text-[var(--muted-foreground)]">
                <span className="font-medium text-[var(--foreground)]">{listing.display_price}</span>
                <span className="flex items-center gap-1">
                  <MapPin className="h-3 w-3" /> {listing.suburb}, {listing.region}
                </span>
                {listing.bedrooms && (
                  <span className="flex items-center gap-1">
                    <BedDouble className="h-3 w-3" /> {listing.bedrooms}br / {listing.bathrooms ?? "?"}ba
                  </span>
                )}
                {listing.land_area && <span>{listing.land_area}m&sup2; land</span>}
                <span>{formatDate(listing.listing_date)}</span>
              </div>

              {listing.recommended_strategy && (
                <div className="mt-2">
                  <span className="text-xs px-2 py-1 rounded bg-[var(--muted)] font-medium">
                    {strategyLabel(listing.recommended_strategy)}
                  </span>
                </div>
              )}
            </div>

            {/* Right: Score */}
            <div className="flex-shrink-0 text-right">
              {listing.composite_score != null ? (
                <div className={`text-2xl font-bold ${scoreColor(listing.composite_score)}`}>
                  {listing.composite_score.toFixed(0)}
                </div>
              ) : (
                <div className="text-2xl font-bold text-gray-300">—</div>
              )}
              <p className="text-xs text-[var(--muted-foreground)]">score</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
