"use client";

import { useEffect, useState } from "react";
import {
  getWatchlist,
  createWatchlistItem,
  updateWatchlistItem,
  deleteWatchlistItem,
  getRegions,
} from "@/lib/api";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { formatDate } from "@/lib/utils";
import type { WatchlistItem } from "@/types";
import { Bookmark, Plus, Trash2, Bell, BellOff } from "lucide-react";

export default function WatchlistPage() {
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [regions, setRegions] = useState<{ region: string; count: number }[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);

  // New item form state
  const [newName, setNewName] = useState("");
  const [newMaxPrice, setNewMaxPrice] = useState("");
  const [newMinBeds, setNewMinBeds] = useState("");
  const [newRegions, setNewRegions] = useState<string[]>([]);
  const [newMinScore, setNewMinScore] = useState("");

  useEffect(() => {
    Promise.all([
      getWatchlist().then(setItems).catch(() => {}),
      getRegions().then(setRegions).catch(() => {}),
    ]).finally(() => setLoading(false));
  }, []);

  async function handleCreate() {
    if (!newName.trim()) return;
    try {
      const criteria: Record<string, any> = {};
      if (newMaxPrice) criteria.max_price = parseFloat(newMaxPrice);
      if (newMinBeds) criteria.min_bedrooms = parseInt(newMinBeds);
      if (newRegions.length > 0) criteria.regions = newRegions;
      if (newMinScore) criteria.min_score = parseFloat(newMinScore);

      const item = await createWatchlistItem({
        name: newName.trim(),
        search_criteria: criteria,
        alert_enabled: true,
      });
      setItems((prev) => [item, ...prev]);
      setShowForm(false);
      setNewName("");
      setNewMaxPrice("");
      setNewMinBeds("");
      setNewRegions([]);
      setNewMinScore("");
    } catch (e) {
      console.error("Failed to create:", e);
    }
  }

  async function handleToggleAlert(item: WatchlistItem) {
    try {
      const updated = await updateWatchlistItem(item.id, {
        alert_enabled: !item.alert_enabled,
      });
      setItems((prev) =>
        prev.map((i) => (i.id === item.id ? { ...i, alert_enabled: updated.alert_enabled } : i))
      );
    } catch (e) {
      console.error("Failed to toggle alert:", e);
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Delete this saved search?")) return;
    try {
      await deleteWatchlistItem(id);
      setItems((prev) => prev.filter((i) => i.id !== id));
    } catch (e) {
      console.error("Failed to delete:", e);
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Bookmark className="h-6 w-6 text-[var(--primary)]" />
            Saved Searches
          </h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">
            Set criteria and get email alerts when matching properties are found.
          </p>
        </div>
        <Button onClick={() => setShowForm(!showForm)}>
          <Plus className="h-4 w-4 mr-1" /> New Search
        </Button>
      </div>

      {/* Create Form */}
      {showForm && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Create Saved Search</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium">Name</label>
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="e.g., Waikato Under 400k 3br+"
                className="mt-1 w-full h-9 px-3 rounded-lg border border-[var(--border)] bg-[var(--card)] text-sm"
              />
            </div>
            <div className="grid md:grid-cols-4 gap-4">
              <div>
                <label className="text-sm font-medium">Max Price</label>
                <input
                  type="number"
                  value={newMaxPrice}
                  onChange={(e) => setNewMaxPrice(e.target.value)}
                  placeholder="500000"
                  className="mt-1 w-full h-9 px-3 rounded-lg border border-[var(--border)] bg-[var(--card)] text-sm"
                />
              </div>
              <div>
                <label className="text-sm font-medium">Min Bedrooms</label>
                <input
                  type="number"
                  value={newMinBeds}
                  onChange={(e) => setNewMinBeds(e.target.value)}
                  placeholder="3"
                  className="mt-1 w-full h-9 px-3 rounded-lg border border-[var(--border)] bg-[var(--card)] text-sm"
                />
              </div>
              <div>
                <label className="text-sm font-medium">Min Score</label>
                <input
                  type="number"
                  value={newMinScore}
                  onChange={(e) => setNewMinScore(e.target.value)}
                  placeholder="50"
                  className="mt-1 w-full h-9 px-3 rounded-lg border border-[var(--border)] bg-[var(--card)] text-sm"
                />
              </div>
              <div>
                <label className="text-sm font-medium">Region</label>
                <select
                  value={newRegions[0] || ""}
                  onChange={(e) => setNewRegions(e.target.value ? [e.target.value] : [])}
                  className="mt-1 w-full h-9 px-3 rounded-lg border border-[var(--border)] bg-[var(--card)] text-sm"
                >
                  <option value="">Any Region</option>
                  {regions.map((r) => (
                    <option key={r.region} value={r.region}>{r.region}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="flex gap-3">
              <Button onClick={handleCreate}>Create</Button>
              <Button variant="outline" onClick={() => setShowForm(false)}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Watchlist Items */}
      {items.length === 0 && !showForm ? (
        <Card>
          <CardContent className="p-12 text-center">
            <Bookmark className="h-12 w-12 text-[var(--muted-foreground)] mx-auto mb-4" />
            <h3 className="font-semibold text-lg">No saved searches</h3>
            <p className="text-sm text-[var(--muted-foreground)] mt-1">
              Create a saved search to get alerted when matching properties appear.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <Card key={item.id}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h3 className="font-semibold">{item.name}</h3>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {item.search_criteria.max_price && (
                        <span className="text-xs px-2 py-1 rounded bg-[var(--muted)]">
                          Max: ${(item.search_criteria.max_price / 1000).toFixed(0)}k
                        </span>
                      )}
                      {item.search_criteria.min_bedrooms && (
                        <span className="text-xs px-2 py-1 rounded bg-[var(--muted)]">
                          {item.search_criteria.min_bedrooms}+ beds
                        </span>
                      )}
                      {item.search_criteria.regions?.map((r: string) => (
                        <span key={r} className="text-xs px-2 py-1 rounded bg-[var(--muted)]">{r}</span>
                      ))}
                      {item.search_criteria.min_score && (
                        <span className="text-xs px-2 py-1 rounded bg-[var(--muted)]">
                          Score {item.search_criteria.min_score}+
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-[var(--muted-foreground)] mt-2">
                      Created {formatDate(item.created_at)}
                      {item.last_alerted_at && ` | Last alert: ${formatDate(item.last_alerted_at)}`}
                    </p>
                  </div>

                  <div className="flex items-center gap-2 flex-shrink-0">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleToggleAlert(item)}
                      title={item.alert_enabled ? "Disable alerts" : "Enable alerts"}
                    >
                      {item.alert_enabled ? (
                        <Bell className="h-4 w-4 text-emerald-600" />
                      ) : (
                        <BellOff className="h-4 w-4 text-[var(--muted-foreground)]" />
                      )}
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => handleDelete(item.id)}>
                      <Trash2 className="h-4 w-4 text-red-500" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
