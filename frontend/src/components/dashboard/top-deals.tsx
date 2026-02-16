"use client";

import Link from "next/link";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  formatCurrency,
  formatPercent,
  verdictColor,
  verdictLabel,
  strategyLabel,
} from "@/lib/utils";
import type { TopDeal } from "@/types";
import { TrendingUp, Clock, MapPin, BedDouble, ExternalLink } from "lucide-react";

interface TopDealsProps {
  deals: TopDeal[];
}

export function TopDeals({ deals }: TopDealsProps) {
  if (deals.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-[var(--primary)]" />
            Top Deals
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-[var(--muted-foreground)] text-sm">
            No deals found yet. Run the pipeline to analyze properties.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-[var(--primary)]" />
          Top {deals.length} Deals
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {deals.map((deal, index) => (
          <Link
            key={deal.id}
            href={`/properties/${deal.id}`}
            className="block p-4 rounded-lg border border-[var(--border)] hover:border-[var(--primary)] hover:shadow-sm transition-all"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-start gap-3 min-w-0">
                {/* Rank */}
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-[var(--primary)] text-[var(--primary-foreground)] flex items-center justify-center text-sm font-bold">
                  {index + 1}
                </div>

                <div className="min-w-0">
                  <p className="font-semibold text-[var(--foreground)] truncate">
                    {deal.address}
                  </p>
                  <div className="flex items-center gap-3 mt-1 text-sm text-[var(--muted-foreground)]">
                    <span className="flex items-center gap-1">
                      <MapPin className="h-3 w-3" />
                      {deal.suburb}
                    </span>
                    {deal.bedrooms && (
                      <span className="flex items-center gap-1">
                        <BedDouble className="h-3 w-3" />
                        {deal.bedrooms}br
                      </span>
                    )}
                    <span>{deal.display_price}</span>
                  </div>
                </div>
              </div>

              {/* Score & Verdict */}
              <div className="flex-shrink-0 text-right">
                <div className="text-lg font-bold text-[var(--primary)]">
                  {deal.composite_score?.toFixed(0) ?? "—"}
                </div>
                <Badge
                  variant={
                    deal.verdict === "STRONG_BUY" || deal.verdict === "BUY"
                      ? "success"
                      : deal.verdict === "MAYBE"
                      ? "warning"
                      : "danger"
                  }
                  className="text-[10px]"
                >
                  {verdictLabel(deal.verdict)}
                </Badge>
              </div>
            </div>

            {/* Metrics row */}
            <div className="flex items-center gap-4 mt-3 text-xs flex-wrap">
              <span className="px-2 py-1 rounded bg-[var(--muted)] font-medium">
                {strategyLabel(deal.recommended_strategy)}
              </span>
              {deal.vision_source && (
                <span
                  className={`px-2 py-1 rounded font-medium ${
                    deal.vision_source.startsWith("Mock") || deal.vision_source === "No photos"
                      ? "bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-200"
                      : "bg-emerald-100 dark:bg-emerald-900/40 text-emerald-800 dark:text-emerald-200"
                  }`}
                  title={deal.vision_confidence ? `Confidence: ${deal.vision_confidence}` : undefined}
                >
                  Vision: {deal.vision_source}
                </span>
              )}
              <span>
                Flip ROI: <strong>{formatPercent(deal.flip_roi)}</strong>
              </span>
              <span>
                Yield: <strong>{formatPercent(deal.rental_yield)}</strong>
              </span>
              {deal.timeline_weeks > 0 && (
                <span className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {deal.timeline_weeks}w
                </span>
              )}
              <span
                role="link"
                tabIndex={0}
                className="ml-auto text-[var(--primary)] hover:underline flex items-center gap-1 cursor-pointer"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  window.open(deal.property_url, "_blank", "noopener,noreferrer");
                }}
              >
                TradeMe <ExternalLink className="h-3 w-3" />
              </span>
            </div>
          </Link>
        ))}
      </CardContent>
    </Card>
  );
}
