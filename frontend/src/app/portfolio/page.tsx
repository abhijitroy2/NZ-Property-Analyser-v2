"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getPortfolio, updatePortfolioEntry, deletePortfolioEntry, getListing } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatCurrency, formatPercent, formatDate } from "@/lib/utils";
import type { PortfolioEntry, Listing } from "@/types";
import { Briefcase, Trash2, Edit3, ExternalLink } from "lucide-react";

const STATUS_OPTIONS = [
  "watching",
  "offered",
  "purchased",
  "renovating",
  "selling",
  "renting",
  "sold",
];

const STATUS_COLORS: Record<string, string> = {
  watching: "bg-blue-100 text-blue-800",
  offered: "bg-purple-100 text-purple-800",
  purchased: "bg-emerald-100 text-emerald-800",
  renovating: "bg-amber-100 text-amber-800",
  selling: "bg-orange-100 text-orange-800",
  renting: "bg-green-100 text-green-800",
  sold: "bg-gray-100 text-gray-800",
};

export default function PortfolioPage() {
  const [entries, setEntries] = useState<(PortfolioEntry & { listing?: Listing })[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<number | null>(null);

  useEffect(() => {
    loadPortfolio();
  }, []);

  async function loadPortfolio() {
    try {
      const data = await getPortfolio();
      // Fetch listing details for each entry
      const enriched = await Promise.all(
        data.map(async (entry) => {
          try {
            const listing = await getListing(entry.listing_id);
            return { ...entry, listing };
          } catch {
            return entry;
          }
        })
      );
      setEntries(enriched);
    } catch (e) {
      console.error("Failed to load portfolio:", e);
    } finally {
      setLoading(false);
    }
  }

  async function handleStatusChange(entryId: number, status: string) {
    try {
      await updatePortfolioEntry(entryId, { status });
      setEntries((prev) =>
        prev.map((e) => (e.id === entryId ? { ...e, status } : e))
      );
    } catch (e) {
      console.error("Failed to update:", e);
    }
  }

  async function handleDelete(entryId: number) {
    if (!confirm("Remove from portfolio?")) return;
    try {
      await deletePortfolioEntry(entryId);
      setEntries((prev) => prev.filter((e) => e.id !== entryId));
    } catch (e) {
      console.error("Failed to delete:", e);
    }
  }

  async function handleUpdateActuals(entryId: number, field: string, value: string) {
    const numValue = parseFloat(value);
    if (isNaN(numValue)) return;
    try {
      await updatePortfolioEntry(entryId, { [field]: numValue });
      setEntries((prev) =>
        prev.map((e) => (e.id === entryId ? { ...e, [field]: numValue } : e))
      );
    } catch (e) {
      console.error("Failed to update:", e);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-[var(--primary)]" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Briefcase className="h-6 w-6 text-[var(--primary)]" />
          Portfolio
        </h1>
        <p className="text-sm text-[var(--muted-foreground)] mt-1">
          Track properties through your investment pipeline. Compare actuals vs projections.
        </p>
      </div>

      {entries.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <Briefcase className="h-12 w-12 text-[var(--muted-foreground)] mx-auto mb-4" />
            <h3 className="font-semibold text-lg">No properties in portfolio</h3>
            <p className="text-sm text-[var(--muted-foreground)] mt-1">
              Add properties from the property detail page to start tracking them.
            </p>
            <Link href="/properties">
              <Button className="mt-4">Browse Properties</Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {entries.map((entry) => (
            <Card key={entry.id} className="hover:shadow-sm transition-shadow">
              <CardContent className="p-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <Link href={`/properties/${entry.listing_id}`} className="font-semibold hover:text-[var(--primary)] truncate">
                        {entry.listing?.full_address || entry.listing?.address || `Listing #${entry.listing_id}`}
                      </Link>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[entry.status] || STATUS_COLORS.watching}`}>
                        {entry.status}
                      </span>
                    </div>

                    {entry.listing && (
                      <p className="text-sm text-[var(--muted-foreground)] mb-3">
                        {entry.listing.display_price} | {entry.listing.bedrooms}br | {entry.listing.suburb}, {entry.listing.region}
                      </p>
                    )}

                    {/* Projected vs Actual comparison */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                      <ComparisonCell
                        label="Reno Cost"
                        projected={entry.projected_reno_cost}
                        actual={entry.actual_reno_cost}
                        editable={editingId === entry.id}
                        onSave={(v) => handleUpdateActuals(entry.id, "actual_reno_cost", v)}
                      />
                      <ComparisonCell
                        label="Sale Price"
                        projected={entry.projected_arv}
                        actual={entry.actual_sale_price}
                        editable={editingId === entry.id}
                        onSave={(v) => handleUpdateActuals(entry.id, "actual_sale_price", v)}
                      />
                      <ComparisonCell
                        label="Weekly Rent"
                        projected={entry.projected_weekly_rent}
                        actual={entry.actual_weekly_rent}
                        editable={editingId === entry.id}
                        onSave={(v) => handleUpdateActuals(entry.id, "actual_weekly_rent", v)}
                        prefix="$"
                        suffix="/wk"
                      />
                      <ComparisonCell
                        label="ROI"
                        projected={entry.projected_roi}
                        actual={null}
                        isPercent
                      />
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex flex-col gap-2 flex-shrink-0">
                    <select
                      value={entry.status}
                      onChange={(e) => handleStatusChange(entry.id, e.target.value)}
                      className="h-8 px-2 text-xs rounded border border-[var(--border)] bg-[var(--card)]"
                    >
                      {STATUS_OPTIONS.map((s) => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setEditingId(editingId === entry.id ? null : entry.id)}
                    >
                      <Edit3 className="h-3 w-3 mr-1" /> Edit
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => handleDelete(entry.id)}>
                      <Trash2 className="h-3 w-3 mr-1 text-red-500" />
                    </Button>
                  </div>
                </div>

                {entry.notes && (
                  <p className="text-xs text-[var(--muted-foreground)] mt-3 border-t pt-3">
                    {entry.notes}
                  </p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function ComparisonCell({
  label,
  projected,
  actual,
  editable,
  onSave,
  isPercent,
  prefix = "",
  suffix = "",
}: {
  label: string;
  projected: number | null | undefined;
  actual: number | null | undefined;
  editable?: boolean;
  onSave?: (value: string) => void;
  isPercent?: boolean;
  prefix?: string;
  suffix?: string;
}) {
  const [inputValue, setInputValue] = useState(actual?.toString() || "");

  const formatVal = (v: number | null | undefined) => {
    if (v == null) return "—";
    if (isPercent) return formatPercent(v);
    return formatCurrency(v);
  };

  return (
    <div className="bg-[var(--muted)] rounded-lg p-2">
      <p className="text-xs text-[var(--muted-foreground)] mb-1">{label}</p>
      <p className="text-xs">
        <span className="text-[var(--muted-foreground)]">Proj:</span>{" "}
        <span className="font-medium">{formatVal(projected)}</span>
      </p>
      {editable && onSave ? (
        <input
          type="number"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onBlur={() => onSave(inputValue)}
          className="mt-1 w-full h-6 px-1 text-xs rounded border border-[var(--border)] bg-[var(--card)]"
          placeholder="Actual"
        />
      ) : (
        <p className="text-xs">
          <span className="text-[var(--muted-foreground)]">Act:</span>{" "}
          <span className="font-medium">{formatVal(actual)}</span>
        </p>
      )}
    </div>
  );
}
