"use client";

import { useState } from "react";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { runPipeline, runScrapeOnly, runAnalyzeOnly } from "@/lib/api";
import { Settings, Play, Download, BarChart3, RefreshCw } from "lucide-react";

export default function SettingsPage() {
  const [status, setStatus] = useState<string | null>(null);

  async function handleAction(action: () => Promise<any>, label: string) {
    setStatus(`Starting ${label}...`);
    try {
      const result = await action();
      setStatus(`${label}: ${result.message}`);
    } catch (e: any) {
      setStatus(`Failed: ${e.message}. Is the backend running on port 8000?`);
    }
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Settings className="h-6 w-6 text-[var(--primary)]" />
          Settings & Actions
        </h1>
      </div>

      {/* Pipeline Actions */}
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
            <Button onClick={() => handleAction(runPipeline, "Full Pipeline")}>
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
            <Button variant="outline" onClick={() => handleAction(runScrapeOnly, "Scrape")}>
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
            <Button variant="outline" onClick={() => handleAction(runAnalyzeOnly, "Analysis")}>
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

      {/* Configuration Guide */}
      <Card>
        <CardHeader>
          <CardTitle>Configuration</CardTitle>
          <CardDescription>
            Backend settings are managed via the <code className="text-xs bg-[var(--muted)] px-1 rounded">.env</code> file
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <ConfigRow
            label="TradeMe Search URLs"
            envVar="TRADEME_SEARCH_URLS"
            desc="Comma-separated TradeMe search URLs to scrape"
          />
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

      {/* Setup Guide */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Start Guide</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-[var(--muted-foreground)]">
          <p>1. Copy <code className="bg-[var(--muted)] px-1 rounded">backend/.env.example</code> to <code className="bg-[var(--muted)] px-1 rounded">backend/.env</code></p>
          <p>2. Set your <code className="bg-[var(--muted)] px-1 rounded">TRADEME_SEARCH_URLS</code> to the TradeMe search pages you want to monitor</p>
          <p>3. Start the backend: <code className="bg-[var(--muted)] px-1 rounded">cd backend &amp;&amp; uvicorn app.main:app --reload</code></p>
          <p>4. Click &quot;Run Pipeline&quot; above to scrape and analyze properties</p>
          <p>5. Optionally set up API keys for AI vision analysis, email alerts, etc.</p>
        </CardContent>
      </Card>
    </div>
  );
}

function ConfigRow({ label, envVar, desc }: { label: string; envVar: string; desc: string }) {
  return (
    <div className="flex items-start justify-between p-2 rounded border-b border-[var(--border)] last:border-0">
      <div>
        <p className="font-medium text-[var(--foreground)]">{label}</p>
        <p className="text-xs text-[var(--muted-foreground)]">{desc}</p>
      </div>
      <code className="text-xs bg-[var(--muted)] px-2 py-1 rounded flex-shrink-0 ml-4">{envVar}</code>
    </div>
  );
}
