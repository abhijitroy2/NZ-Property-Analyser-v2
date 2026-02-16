"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useState, useRef, useEffect } from "react";
import {
  LayoutDashboard,
  Building2,
  Briefcase,
  Bookmark,
  Settings,
  Play,
  Loader2,
} from "lucide-react";
import { getPipelineStatus, type PipelineStatus } from "@/lib/api";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/properties", label: "Properties", icon: Building2 },
  { href: "/portfolio", label: "Portfolio", icon: Briefcase },
  { href: "/watchlist", label: "Watchlist", icon: Bookmark },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Nav() {
  const pathname = usePathname();

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b border-[var(--border)] bg-[var(--card)]">
      <div className="max-w-screen-2xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2">
            <Building2 className="h-7 w-7 text-[var(--primary)]" />
            <span className="text-lg font-bold text-[var(--foreground)]">
              NZ Property Finder
            </span>
          </Link>

          {/* Navigation Links */}
          <div className="flex items-center gap-1">
            {navItems.map((item) => {
              const isActive =
                item.href === "/"
                  ? pathname === "/"
                  : pathname.startsWith(item.href);

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                    isActive
                      ? "bg-[var(--primary)] text-[var(--primary-foreground)]"
                      : "text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--muted)]"
                  )}
                >
                  <item.icon className="h-4 w-4" />
                  <span className="hidden sm:inline">{item.label}</span>
                </Link>
              );
            })}
          </div>

          {/* Run Pipeline Button */}
          <PipelineButton />
        </div>
        <PipelineStatusBar />
      </div>
    </nav>
  );
}

function PipelineStatusBar() {
  const [status, setStatus] = useState<PipelineStatus | null>(null);

  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      try {
        const s = await getPipelineStatus();
        if (!cancelled) setStatus(s);
      } catch {
        if (!cancelled) setStatus(null);
      }
    };

    poll();
    const interval = setInterval(poll, 2000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  if (!status?.running) return null;

  const progress = status.progress;
  const progressPct = progress && progress.total > 0
    ? Math.round((progress.current / progress.total) * 100)
    : null;

  return (
    <div className="flex items-center gap-3 py-1.5 px-4 bg-emerald-50 dark:bg-emerald-950/50 border-t border-emerald-200 dark:border-emerald-800 text-sm">
      <Loader2 className="h-4 w-4 animate-spin text-emerald-600 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <span className="font-medium text-emerald-800 dark:text-emerald-200">
          {status.task === "scrape" && "Scraping TradeMe"}
          {status.task === "analyze" && "Analyzing listings"}
          {status.task === "full" && "Pipeline running"}
        </span>
        {status.message && (
          <span className="text-emerald-700 dark:text-emerald-300 ml-2 truncate">
            — {status.message}
          </span>
        )}
      </div>
      {progressPct !== null && (
        <span className="flex-shrink-0 font-mono text-emerald-700 dark:text-emerald-300">
          {status.progress?.current}/{status.progress?.total} ({progressPct}%)
        </span>
      )}
      {progress && progress.total > 1 && (
        <div className="w-24 h-1.5 rounded-full bg-emerald-200 dark:bg-emerald-800 overflow-hidden flex-shrink-0">
          <div
            className="h-full bg-emerald-600 transition-all duration-300"
            style={{ width: `${progressPct ?? 0}%` }}
          />
        </div>
      )}
    </div>
  );
}

function PipelineButton() {
  const [showTooltip, setShowTooltip] = useState(false);
  const [running, setRunning] = useState(false);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const handleRun = async () => {
    if (running) return;
    setRunning(true);
    setShowTooltip(false);
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"}/pipeline/run`,
        { method: "POST" }
      );
      if (res.ok) {
        alert("Pipeline started! This scrapes TradeMe, filters, analyzes, and scores all properties. Check back in a few minutes for results.");
      } else {
        alert("Failed to start pipeline. Is the backend running?");
      }
    } catch {
      alert("Cannot reach backend. Make sure the API server is running on port 8000.");
    } finally {
      setRunning(false);
    }
  };

  const handleMouseEnter = () => {
    timeoutRef.current = setTimeout(() => setShowTooltip(true), 400);
  };

  const handleMouseLeave = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setShowTooltip(false);
  };

  useEffect(() => {
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  return (
    <div className="relative" onMouseEnter={handleMouseEnter} onMouseLeave={handleMouseLeave}>
      <button
        onClick={handleRun}
        disabled={running}
        className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
      >
        {running ? (
          <div className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
        ) : (
          <Play className="h-4 w-4" />
        )}
        <span className="hidden sm:inline">{running ? "Running..." : "Run Pipeline"}</span>
      </button>

      {showTooltip && !running && (
        <div className="absolute right-0 top-full mt-2 w-72 p-3 rounded-lg border border-[var(--border)] bg-[var(--card)] shadow-lg z-50 text-xs text-[var(--foreground)]">
          <p className="font-semibold mb-2 text-sm">Full Analysis Pipeline</p>
          <ol className="space-y-1.5 list-decimal list-inside text-[var(--muted-foreground)]">
            <li><span className="font-medium text-[var(--foreground)]">Scrape</span> — Fetches listings from TradeMe using configured search URLs</li>
            <li><span className="font-medium text-[var(--foreground)]">Filter</span> — Applies hard filters (price, title type, population, property type)</li>
            <li><span className="font-medium text-[var(--foreground)]">Analyze</span> — Runs deep analysis: renovation cost, ARV, rental income, insurability, subdivision potential</li>
            <li><span className="font-medium text-[var(--foreground)]">Score &amp; Rank</span> — Calculates composite scores &amp; assigns verdicts (BUY / MAYBE / PASS)</li>
          </ol>
          <p className="mt-2 text-[var(--muted-foreground)] italic">Takes a few minutes depending on listing count.</p>
        </div>
      )}
    </div>
  );
}
