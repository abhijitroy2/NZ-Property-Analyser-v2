"use client";

import { useEffect, useState } from "react";
import { StatCard } from "@/components/dashboard/stat-card";
import { TopDeals } from "@/components/dashboard/top-deals";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { getDashboardSummary, getTopDeals, getStatsByRegion } from "@/lib/api";
import type { DashboardSummary, TopDeal } from "@/types";
import {
  Building2,
  CheckCircle2,
  XCircle,
  Clock,
  BarChart3,
  TrendingUp,
  MapPin,
} from "lucide-react";

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [topDeals, setTopDeals] = useState<TopDeal[]>([]);
  const [regionStats, setRegionStats] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [s, d, r] = await Promise.all([
          getDashboardSummary(),
          getTopDeals(5),
          getStatsByRegion(),
        ]);
        setSummary(s);
        setTopDeals(d);
        setRegionStats(r);
      } catch (e: any) {
        setError(e.message || "Failed to load dashboard. Is the backend running?");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center space-y-3">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-[var(--primary)] mx-auto" />
          <p className="text-[var(--muted-foreground)]">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Card className="max-w-md w-full">
          <CardContent className="p-8 text-center space-y-4">
            <XCircle className="h-12 w-12 text-red-500 mx-auto" />
            <h2 className="text-lg font-semibold">Cannot Connect to Backend</h2>
            <p className="text-sm text-[var(--muted-foreground)]">{error}</p>
            <p className="text-xs text-[var(--muted-foreground)]">
              Start the backend with: <code className="bg-[var(--muted)] px-2 py-1 rounded">cd backend &amp;&amp; uvicorn app.main:app --reload</code>
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const s = summary!;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-[var(--foreground)]">Dashboard</h1>
        <p className="text-[var(--muted-foreground)] text-sm mt-1">
          Property investment evaluation overview
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <StatCard
          title="Total Listings"
          value={s.total_listings}
          icon={Building2}
        />
        <StatCard
          title="Passed Filters"
          value={s.passed_filters}
          subtitle={s.total_listings > 0 ? `${((s.passed_filters / s.total_listings) * 100).toFixed(0)}% pass rate` : undefined}
          icon={CheckCircle2}
          trend="up"
        />
        <StatCard
          title="Rejected"
          value={s.rejected}
          icon={XCircle}
        />
        <StatCard
          title="Pending"
          value={s.pending}
          icon={Clock}
        />
        <StatCard
          title="Analyzed"
          value={s.analyzed}
          icon={BarChart3}
        />
        <StatCard
          title="Avg Score"
          value={s.average_score > 0 ? s.average_score.toFixed(1) : "—"}
          icon={TrendingUp}
        />
      </div>

      {/* Verdicts Summary */}
      {Object.keys(s.verdicts).length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {(["STRONG_BUY", "BUY", "MAYBE", "PASS"] as const).map((v) => {
            const count = s.verdicts[v] || 0;
            const colors = {
              STRONG_BUY: "border-emerald-500 bg-emerald-50 dark:bg-emerald-950",
              BUY: "border-green-500 bg-green-50 dark:bg-green-950",
              MAYBE: "border-amber-500 bg-amber-50 dark:bg-amber-950",
              PASS: "border-red-500 bg-red-50 dark:bg-red-950",
            };
            const labels = {
              STRONG_BUY: "Strong Buy",
              BUY: "Buy",
              MAYBE: "Maybe",
              PASS: "Pass",
            };
            return (
              <div
                key={v}
                className={`rounded-lg border-l-4 p-4 ${colors[v]}`}
              >
                <p className="text-xs font-medium text-[var(--muted-foreground)]">{labels[v]}</p>
                <p className="text-2xl font-bold">{count}</p>
              </div>
            );
          })}
        </div>
      )}

      {/* Main Content Grid */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Top Deals - takes 2 columns */}
        <div className="lg:col-span-2">
          <TopDeals deals={topDeals} />
        </div>

        {/* Region Stats */}
        <div>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MapPin className="h-5 w-5 text-[var(--primary)]" />
                Listings by Region
              </CardTitle>
            </CardHeader>
            <CardContent>
              {regionStats.length > 0 ? (
                <div className="space-y-3">
                  {regionStats.map((r: any) => (
                    <div
                      key={r.region}
                      className="flex items-center justify-between py-2 border-b border-[var(--border)] last:border-0"
                    >
                      <div>
                        <p className="text-sm font-medium">{r.region}</p>
                        <p className="text-xs text-[var(--muted-foreground)]">
                          Avg score: {r.avg_score > 0 ? r.avg_score.toFixed(1) : "—"}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-bold">{r.total_listings}</p>
                        <p className="text-xs text-[var(--muted-foreground)]">
                          {r.avg_price > 0 ? `~$${(r.avg_price / 1000).toFixed(0)}k` : ""}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-[var(--muted-foreground)]">
                  No region data yet. Run the pipeline to populate.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
