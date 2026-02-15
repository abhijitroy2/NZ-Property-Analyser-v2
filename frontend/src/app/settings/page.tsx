"use client";

import { useState, useEffect } from "react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  runPipeline,
  runScrapeOnly,
  runAnalyzeOnly,
  getSearchURLs,
  addSearchURL,
  deleteSearchURL,
  toggleSearchURL,
  type SearchURLItem,
} from "@/lib/api";
import {
  Settings,
  Play,
  Download,
  BarChart3,
  Plus,
  Trash2,
  Link2,
  ToggleLeft,
  ToggleRight,
  ExternalLink,
  FolderSync,
  AlertCircle,
} from "lucide-react";

export default function SettingsPage() {
  const [status, setStatus] = useState<string | null>(null);
  const [urls, setUrls] = useState<SearchURLItem[]>([]);
  const [loadingUrls, setLoadingUrls] = useState(true);
  const [newUrl, setNewUrl] = useState("");
  const [newLabel, setNewLabel] = useState("");
  const [addingUrl, setAddingUrl] = useState(false);
  const [urlError, setUrlError] = useState<string | null>(null);

  // Load search URLs on mount
  useEffect(() => {
    loadUrls();
  }, []);

  async function loadUrls() {
    try {
      const data = await getSearchURLs();
      setUrls(data.urls);
    } catch (e: any) {
      setUrlError("Failed to load search URLs. Is the backend running?");
    } finally {
      setLoadingUrls(false);
    }
  }

  async function handleAddUrl() {
    const trimmed = newUrl.trim();
    if (!trimmed) return;

    if (!trimmed.includes("trademe.co.nz")) {
      setUrlError("URL must be a TradeMe search URL");
      return;
    }

    setAddingUrl(true);
    setUrlError(null);
    try {
      const added = await addSearchURL({
        url: trimmed,
        label: newLabel.trim(),
        enabled: true,
      });
      setUrls((prev) => [...prev, added]);
      setNewUrl("");
      setNewLabel("");
      setStatus("URL added and synced to TM-scraper input.txt");
    } catch (e: any) {
      setUrlError(e.message || "Failed to add URL");
    } finally {
      setAddingUrl(false);
    }
  }

  async function handleDelete(id: number) {
    try {
      await deleteSearchURL(id);
      setUrls((prev) => prev.filter((u) => u.id !== id));
      setStatus("URL removed and input.txt updated");
    } catch (e: any) {
      setUrlError(e.message || "Failed to delete URL");
    }
  }

  async function handleToggle(id: number) {
    try {
      const result = await toggleSearchURL(id);
      setUrls((prev) =>
        prev.map((u) => (u.id === id ? { ...u, enabled: result.enabled } : u))
      );
    } catch (e: any) {
      setUrlError(e.message || "Failed to toggle URL");
    }
  }

  async function handleAction(action: () => Promise<any>, label: string) {
    setStatus(`Starting ${label}...`);
    try {
      const result = await action();
      setStatus(`${label}: ${result.message}`);
    } catch (e: any) {
      setStatus(
        `Failed: ${e.message}. Is the backend running on port 8000?`
      );
    }
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Settings className="h-6 w-6 text-[var(--primary)]" />
          Settings & Configuration
        </h1>
      </div>

      {/* ===== Search URLs ===== */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Link2 className="h-5 w-5 text-[var(--primary)]" />
            TradeMe Search URLs
          </CardTitle>
          <CardDescription>
            Configure which TradeMe search pages to scrape. Enabled URLs are
            automatically synced to{" "}
            <code className="text-xs bg-[var(--muted)] px-1 rounded">
              C:\Users\OEM\TM-scraper-1\input.txt
            </code>{" "}
            when saved or when the pipeline runs.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Existing URLs */}
          {loadingUrls ? (
            <div className="flex items-center gap-2 text-sm text-[var(--muted-foreground)] py-4">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-[var(--primary)]" />
              Loading search URLs...
            </div>
          ) : urls.length === 0 ? (
            <div className="text-sm text-[var(--muted-foreground)] py-4 text-center">
              No search URLs configured yet. Add one below.
            </div>
          ) : (
            <div className="space-y-2">
              {urls.map((u) => (
                <div
                  key={u.id}
                  className={`flex items-center gap-3 p-3 rounded-lg border transition-colors ${
                    u.enabled
                      ? "border-[var(--border)] bg-[var(--card)]"
                      : "border-dashed border-[var(--border)] bg-[var(--muted)] opacity-60"
                  }`}
                >
                  {/* Toggle */}
                  <button
                    onClick={() => u.id && handleToggle(u.id)}
                    className="flex-shrink-0 text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors"
                    title={u.enabled ? "Disable this URL" : "Enable this URL"}
                  >
                    {u.enabled ? (
                      <ToggleRight className="h-5 w-5 text-emerald-500" />
                    ) : (
                      <ToggleLeft className="h-5 w-5" />
                    )}
                  </button>

                  {/* URL info */}
                  <div className="min-w-0 flex-1">
                    {u.label && (
                      <p className="text-sm font-medium text-[var(--foreground)] truncate">
                        {u.label}
                      </p>
                    )}
                    <p className="text-xs text-[var(--muted-foreground)] truncate font-mono">
                      {u.url}
                    </p>
                  </div>

                  {/* Open in browser */}
                  <a
                    href={u.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-shrink-0 text-[var(--muted-foreground)] hover:text-[var(--primary)] transition-colors"
                    title="Open in browser"
                  >
                    <ExternalLink className="h-4 w-4" />
                  </a>

                  {/* Delete */}
                  <button
                    onClick={() => u.id && handleDelete(u.id)}
                    className="flex-shrink-0 text-[var(--muted-foreground)] hover:text-red-500 transition-colors"
                    title="Remove this URL"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Add new URL */}
          <div className="border-t border-[var(--border)] pt-4">
            <p className="text-sm font-medium mb-3">Add Search URL</p>
            <div className="space-y-2">
              <input
                type="text"
                placeholder="Optional label (e.g. Waikato under $400k)"
                value={newLabel}
                onChange={(e) => setNewLabel(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--background)] text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]"
              />
              <div className="flex gap-2">
                <input
                  type="url"
                  placeholder="https://www.trademe.co.nz/a/property/residential/sale/..."
                  value={newUrl}
                  onChange={(e) => {
                    setNewUrl(e.target.value);
                    setUrlError(null);
                  }}
                  onKeyDown={(e) => e.key === "Enter" && handleAddUrl()}
                  className="flex-1 px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--background)] text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)] font-mono"
                />
                <Button
                  onClick={handleAddUrl}
                  disabled={addingUrl || !newUrl.trim()}
                >
                  <Plus className="h-4 w-4 mr-1" />
                  {addingUrl ? "Adding..." : "Add"}
                </Button>
              </div>
            </div>
            <p className="text-xs text-[var(--muted-foreground)] mt-2">
              Tip: Go to{" "}
              <a
                href="https://www.trademe.co.nz/a/property/residential/sale"
                target="_blank"
                rel="noopener noreferrer"
                className="text-[var(--primary)] hover:underline"
              >
                TradeMe Property
              </a>
              , set your filters (region, price range, etc.), then copy the URL from your browser.
            </p>
          </div>

          {/* Sync info */}
          <div className="flex items-start gap-2 p-3 rounded-lg bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800">
            <FolderSync className="h-4 w-4 text-blue-500 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-blue-700 dark:text-blue-300">
              Enabled URLs are automatically written to{" "}
              <code className="bg-blue-100 dark:bg-blue-900 px-1 rounded">
                TM-scraper-1\input.txt
              </code>{" "}
              whenever you add, remove, or toggle URLs, and also each time the pipeline runs.
            </p>
          </div>

          {urlError && (
            <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800">
              <AlertCircle className="h-4 w-4 text-red-500 flex-shrink-0" />
              <p className="text-xs text-red-700 dark:text-red-300">
                {urlError}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ===== Pipeline Actions ===== */}
      <Card>
        <CardHeader>
          <CardTitle>Pipeline Actions</CardTitle>
          <CardDescription>
            Manually trigger data processing steps
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between p-3 rounded-lg border border-[var(--border)]">
            <div>
              <p className="font-medium">Full Pipeline</p>
              <p className="text-xs text-[var(--muted-foreground)]">
                Scrape new listings, filter, analyze, and score everything
              </p>
            </div>
            <Button
              onClick={() => handleAction(runPipeline, "Full Pipeline")}
            >
              <Play className="h-4 w-4 mr-1" /> Run
            </Button>
          </div>

          <div className="flex items-center justify-between p-3 rounded-lg border border-[var(--border)]">
            <div>
              <p className="font-medium">Scrape Only</p>
              <p className="text-xs text-[var(--muted-foreground)]">
                Pull new listings from TradeMe without analyzing
              </p>
            </div>
            <Button
              variant="outline"
              onClick={() => handleAction(runScrapeOnly, "Scrape")}
            >
              <Download className="h-4 w-4 mr-1" /> Scrape
            </Button>
          </div>

          <div className="flex items-center justify-between p-3 rounded-lg border border-[var(--border)]">
            <div>
              <p className="font-medium">Analyze Pending</p>
              <p className="text-xs text-[var(--muted-foreground)]">
                Run analysis on all pending listings (skip scraping)
              </p>
            </div>
            <Button
              variant="outline"
              onClick={() => handleAction(runAnalyzeOnly, "Analysis")}
            >
              <BarChart3 className="h-4 w-4 mr-1" /> Analyze
            </Button>
          </div>

          {status && (
            <p className="text-sm p-3 rounded-lg bg-[var(--muted)] text-[var(--muted-foreground)]">
              {status}
            </p>
          )}
        </CardContent>
      </Card>

      {/* ===== Other Configuration ===== */}
      <Card>
        <CardHeader>
          <CardTitle>Other Configuration</CardTitle>
          <CardDescription>
            These settings are managed via the backend{" "}
            <code className="text-xs bg-[var(--muted)] px-1 rounded">
              .env
            </code>{" "}
            file
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <ConfigRow
            label="Max Price Filter"
            envVar="MAX_PRICE"
            desc="Maximum property price (default: $500,000)"
          />
          <ConfigRow
            label="Min Population"
            envVar="MIN_POPULATION"
            desc="Minimum population in territorial authority (default: 50,000)"
          />
          <ConfigRow
            label="AI Vision Provider"
            envVar="VISION_PROVIDER"
            desc="Set to 'openai', 'anthropic', or 'mock' for image analysis"
          />
          <ConfigRow
            label="Email Alerts"
            envVar="SMTP_USERNAME / EMAIL_TO"
            desc="Configure SMTP settings for daily digest emails"
          />
          <ConfigRow
            label="Scheduled Processing"
            envVar="ENABLE_SCHEDULER"
            desc="Set to 'true' for automatic daily pipeline runs"
          />
        </CardContent>
      </Card>
    </div>
  );
}

function ConfigRow({
  label,
  envVar,
  desc,
}: {
  label: string;
  envVar: string;
  desc: string;
}) {
  return (
    <div className="flex items-start justify-between p-2 rounded border-b border-[var(--border)] last:border-0">
      <div>
        <p className="font-medium text-[var(--foreground)]">{label}</p>
        <p className="text-xs text-[var(--muted-foreground)]">{desc}</p>
      </div>
      <code className="text-xs bg-[var(--muted)] px-2 py-1 rounded flex-shrink-0 ml-4">
        {envVar}
      </code>
    </div>
  );
}
