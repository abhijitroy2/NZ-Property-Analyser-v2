"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { getListing, getAnalysis, runScenario, addToPortfolio } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import {
  formatCurrency,
  formatPercent,
  verdictColor,
  verdictLabel,
  strategyLabel,
  scoreColor,
  formatDate,
} from "@/lib/utils";
import type { Listing, Analysis, ScenarioResponse } from "@/types";
import {
  ArrowLeft,
  ExternalLink,
  MapPin,
  BedDouble,
  Ruler,
  Shield,
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
  Home,
  DollarSign,
  Clock,
  Bookmark,
  BarChart3,
  Camera,
} from "lucide-react";

export default function PropertyDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = Number(params.id);

  const [listing, setListing] = useState<Listing | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Scenario modeling state
  const [scenarioPurchase, setScenarioPurchase] = useState(0);
  const [scenarioReno, setScenarioReno] = useState(0);
  const [scenarioSale, setScenarioSale] = useState(0);
  const [scenarioRent, setScenarioRent] = useState(0);
  const [scenarioResult, setScenarioResult] = useState<ScenarioResponse | null>(null);
  const [scenarioLoading, setScenarioLoading] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const l = await getListing(id);
        setListing(l);
        setScenarioPurchase(l.asking_price || 350000);

        try {
          const a = await getAnalysis(id);
          setAnalysis(a);
          setScenarioReno(a.renovation_estimate?.total_estimated || 60000);
          setScenarioSale(a.arv_estimate?.estimated_arv || (l.asking_price || 350000) * 1.2);
          setScenarioRent(a.rental_estimate?.estimated_weekly_rent || 500);
        } catch {
          // Analysis may not exist yet
        }
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  const runCustomScenario = useCallback(async () => {
    setScenarioLoading(true);
    try {
      const result = await runScenario(id, {
        purchase_price: scenarioPurchase,
        renovation_budget: scenarioReno,
        sale_price: scenarioSale,
        weekly_rent: scenarioRent,
      });
      setScenarioResult(result);
    } catch (e) {
      console.error("Scenario failed:", e);
    } finally {
      setScenarioLoading(false);
    }
  }, [id, scenarioPurchase, scenarioReno, scenarioSale, scenarioRent]);

  const handleAddToPortfolio = async () => {
    try {
      await addToPortfolio(id);
      alert("Added to portfolio!");
    } catch (e: any) {
      alert(e.message || "Failed to add to portfolio");
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-[var(--primary)]" />
      </div>
    );
  }

  if (error || !listing) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600">{error || "Property not found"}</p>
        <Button variant="outline" onClick={() => router.back()} className="mt-4">
          Go Back
        </Button>
      </div>
    );
  }

  const flip = analysis?.flip_financials;
  const rental = analysis?.rental_financials;
  const strategy = analysis?.strategy_decision;
  const reno = analysis?.renovation_estimate;
  const timeline = analysis?.timeline_estimate;
  const arv = analysis?.arv_estimate;
  const rentalEst = analysis?.rental_estimate;
  const insurance = analysis?.insurability;
  const subdiv = analysis?.subdivision_analysis;
  const scores = analysis?.component_scores;
  const imageAnalysis = analysis?.image_analysis;

  // For scenario display, use scenario result if available, else analysis
  const displayFlip = scenarioResult?.flip_financials || flip;
  const displayRental = scenarioResult?.rental_financials || rental;
  const displayStrategy = scenarioResult?.strategy_decision || strategy;

  return (
    <div className="space-y-6">
      {/* Back button + header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <button onClick={() => router.back()} className="flex items-center gap-1 text-sm text-[var(--muted-foreground)] hover:text-[var(--foreground)] mb-2">
            <ArrowLeft className="h-4 w-4" /> Back
          </button>
          <h1 className="text-2xl font-bold">{listing.full_address || listing.address}</h1>
          <div className="flex flex-wrap items-center gap-3 mt-2 text-sm text-[var(--muted-foreground)]">
            <span className="flex items-center gap-1"><MapPin className="h-4 w-4" /> {listing.suburb}, {listing.district}, {listing.region}</span>
            {listing.bedrooms && <span className="flex items-center gap-1"><BedDouble className="h-4 w-4" /> {listing.bedrooms}br / {listing.bathrooms ?? "?"}ba</span>}
            {listing.land_area && <span className="flex items-center gap-1"><Ruler className="h-4 w-4" /> {listing.land_area}m&sup2;</span>}
            <span>{formatDate(listing.listing_date)}</span>
          </div>
        </div>

        <div className="flex items-center gap-3 flex-shrink-0">
          {analysis && (
            <div className="text-right">
              <div className={`text-3xl font-bold ${scoreColor(analysis.composite_score)}`}>
                {analysis.composite_score?.toFixed(0) ?? "—"}
              </div>
              <Badge variant={analysis.verdict === "STRONG_BUY" || analysis.verdict === "BUY" ? "success" : analysis.verdict === "MAYBE" ? "warning" : "danger"}>
                {verdictLabel(analysis.verdict)}
              </Badge>
            </div>
          )}
          <div className="flex flex-col gap-2">
            <Button variant="outline" size="sm" onClick={handleAddToPortfolio}>
              <Bookmark className="h-4 w-4 mr-1" /> Portfolio
            </Button>
            <a href={listing.property_url} target="_blank" rel="noopener noreferrer">
              <Button variant="outline" size="sm" className="w-full">
                TradeMe <ExternalLink className="h-3 w-3 ml-1" />
              </Button>
            </a>
          </div>
        </div>
      </div>

      {/* Price + Strategy summary */}
      <div className="grid md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-5 text-center">
            <p className="text-sm text-[var(--muted-foreground)]">Asking Price</p>
            <p className="text-2xl font-bold">{listing.display_price}</p>
            {listing.estimated_market_price && (
              <p className="text-xs text-[var(--muted-foreground)]">Est: {listing.estimated_market_price}</p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5 text-center">
            <p className="text-sm text-[var(--muted-foreground)]">Strategy</p>
            <p className="text-xl font-bold">{strategyLabel(displayStrategy?.recommended_strategy)}</p>
            <p className="text-xs text-[var(--muted-foreground)] mt-1">{displayStrategy?.reason}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5 text-center">
            <p className="text-sm text-[var(--muted-foreground)]">Est. Weekly Rent</p>
            <p className="text-2xl font-bold">
              {rentalEst?.estimated_weekly_rent != null
                ? formatCurrency(rentalEst.estimated_weekly_rent)
                : listing.estimated_weekly_rent || "N/A"}
            </p>
            {rentalEst && (
              <p className="text-xs text-[var(--muted-foreground)]">Source: {rentalEst.source}</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Flip vs Rental Comparison */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Flip Scenario */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" /> Flip Scenario
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {displayFlip ? (
              <>
                <Row label="Purchase" value={formatCurrency(displayFlip.purchase_price)} />
                <Row label="Renovation" value={formatCurrency(displayFlip.renovation_cost)} />
                <Row label="GST Refund" value={formatCurrency(displayFlip.gst_refund)} sub="credit" />
                <Row label="ARV (Sale)" value={formatCurrency(displayFlip.arv)} />
                <Row label="Timeline" value={`${displayFlip.timeline_weeks} weeks`} />
                <Row label="Interest Cost" value={formatCurrency(displayFlip.interest_cost)} />
                <Row label="Total Expenses" value={formatCurrency(displayFlip.total_expenses)} />
                <div className="border-t pt-3 mt-3">
                  <Row label="Gross Profit" value={formatCurrency(displayFlip.gross_profit)} bold />
                  <Row label="Tax (33%)" value={formatCurrency(displayFlip.tax)} />
                  <Row label="Net Profit" value={formatCurrency(displayFlip.net_profit)} bold highlight />
                  <Row label="ROI" value={formatPercent(displayFlip.roi_percentage)} bold highlight={displayFlip.meets_15_roi} />
                </div>
              </>
            ) : (
              <p className="text-sm text-[var(--muted-foreground)]">No flip analysis available</p>
            )}
          </CardContent>
        </Card>

        {/* Rental Scenario */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Home className="h-5 w-5" /> Rental Scenario
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {displayRental ? (
              <>
                <Row label="Total Invested" value={formatCurrency(displayRental.total_invested)} />
                <Row label="Weekly Rent" value={formatCurrency(displayRental.weekly_rent)} sub="/week" />
                <Row label="Annual Rent" value={formatCurrency(displayRental.annual_rent)} sub="(50 weeks)" />
                <Row label="Total Expenses" value={formatCurrency(displayRental.total_expenses)} />
                <Row label="Net Cash Surplus" value={formatCurrency(displayRental.net_cash_surplus)} />
                <div className="border-t pt-3 mt-3">
                  <Row label="Annual Cashflow" value={formatCurrency(displayRental.overall_annual_cashflow)} bold highlight />
                  <Row label="Gross Yield" value={formatPercent(displayRental.gross_yield_percentage)} bold highlight={displayRental.meets_9_yield} />
                  <Row label="Net Yield" value={formatPercent(displayRental.net_yield_percentage)} bold />
                </div>
              </>
            ) : (
              <p className="text-sm text-[var(--muted-foreground)]">No rental analysis available</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Interactive Scenario Modeling */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" /> Scenario Modeling
          </CardTitle>
          <CardDescription>Adjust inputs to recalculate ROI in real time</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-2 gap-6">
            <Slider
              label="Purchase Price"
              value={scenarioPurchase}
              min={100000}
              max={800000}
              step={5000}
              onChange={setScenarioPurchase}
              formatValue={formatCurrency}
            />
            <Slider
              label="Renovation Budget"
              value={scenarioReno}
              min={5000}
              max={200000}
              step={5000}
              onChange={setScenarioReno}
              formatValue={formatCurrency}
            />
            <Slider
              label="Sale Price (ARV)"
              value={scenarioSale}
              min={200000}
              max={1000000}
              step={5000}
              onChange={setScenarioSale}
              formatValue={formatCurrency}
            />
            <Slider
              label="Weekly Rent"
              value={scenarioRent}
              min={200}
              max={1200}
              step={10}
              onChange={setScenarioRent}
              formatValue={(v) => `$${v}/wk`}
            />
          </div>
          <div className="mt-6 flex justify-center">
            <Button onClick={runCustomScenario} disabled={scenarioLoading} size="lg">
              {scenarioLoading ? "Calculating..." : "Recalculate Scenario"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Analysis Details Grid */}
      {analysis && (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* Renovation */}
          {reno && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Renovation Estimate</CardTitle>
              </CardHeader>
              <CardContent className="text-sm space-y-2">
                <Row label="Level" value={reno.renovation_level} />
                <Row label="Floor Area" value={`${reno.floor_area_used}m\u00B2`} />
                <Row label="Base Cost" value={formatCurrency(reno.base_renovation)} />
                <Row label="Additional" value={formatCurrency(reno.additional_items)} />
                <Row label="Contingency" value={formatCurrency(reno.contingency)} />
                <Row label="Total" value={formatCurrency(reno.total_estimated)} bold />
                {reno.key_items.length > 0 && (
                  <div className="pt-2">
                    <p className="font-medium mb-1">Key Items:</p>
                    <ul className="list-disc list-inside text-xs text-[var(--muted-foreground)]">
                      {reno.key_items.map((item, i) => <li key={i}>{item}</li>)}
                    </ul>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Timeline */}
          {timeline && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <Clock className="h-4 w-4" /> Timeline
                </CardTitle>
              </CardHeader>
              <CardContent className="text-sm space-y-2">
                <Row label="Weeks" value={`${timeline.estimated_weeks} weeks`} bold />
                <Row label="Within Target" value={timeline.within_8_week_target ? "Yes" : "No"} highlight={timeline.within_8_week_target} />
                <p className="text-xs text-[var(--muted-foreground)] mt-2">{timeline.notes}</p>
              </CardContent>
            </Card>
          )}

          {/* Insurance */}
          {insurance && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <Shield className="h-4 w-4" /> Insurance
                </CardTitle>
              </CardHeader>
              <CardContent className="text-sm space-y-2">
                <Row label="Insurable" value={insurance.insurable ? "Yes" : "No"} highlight={insurance.insurable} />
                <Row label="Annual Premium" value={formatCurrency(insurance.annual_insurance)} />
                <Row label="Provider" value={insurance.insurer || "N/A"} />
              </CardContent>
            </Card>
          )}

          {/* AI Vision Analysis */}
          {imageAnalysis && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <Camera className="h-4 w-4" /> AI Vision Analysis
                </CardTitle>
              </CardHeader>
              <CardContent className="text-sm space-y-3">
                <div className="flex flex-wrap gap-2 mb-2">
                  <span className="px-2 py-0.5 rounded bg-[var(--muted)] text-xs font-medium">
                    Source: {(() => {
                      const s = imageAnalysis.source || "";
                      const labels: Record<string, string> = {
                        mock_default: "Mock (default)",
                        no_photos: "No photos",
                        google_vision: "Google Vision",
                        openai: "OpenAI GPT-4V",
                        anthropic: "Anthropic Claude",
                      };
                      return labels[s] || s || "Unknown";
                    })()}
                  </span>
                  {imageAnalysis.confidence && (
                    <span className="px-2 py-0.5 rounded bg-[var(--muted)] text-xs">
                      Confidence: {imageAnalysis.confidence}
                    </span>
                  )}
                </div>
                <Row label="Overall reno level" value={imageAnalysis.overall_reno_level || "—"} />
                <Row label="Roof condition" value={imageAnalysis.roof_condition || "—"} />
                <Row label="Exterior" value={imageAnalysis.exterior_condition || "—"} />
                <Row label="Interior quality" value={imageAnalysis.interior_quality || "—"} />
                <Row label="Kitchen age" value={imageAnalysis.kitchen_age || "—"} />
                <Row label="Bathroom age" value={imageAnalysis.bathroom_age || "—"} />
                {imageAnalysis.structural_concerns && imageAnalysis.structural_concerns.length > 0 && (
                  <div>
                    <p className="font-medium text-[var(--muted-foreground)] mb-1">Structural concerns</p>
                    <ul className="list-disc list-inside text-xs">
                      {imageAnalysis.structural_concerns.map((c: string, i: number) => (
                        <li key={i}>{c}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {imageAnalysis.key_renovation_items && imageAnalysis.key_renovation_items.length > 0 && (
                  <div>
                    <p className="font-medium text-[var(--muted-foreground)] mb-1">Key renovation items</p>
                    <ul className="list-disc list-inside text-xs">
                      {imageAnalysis.key_renovation_items.map((item: string, i: number) => (
                        <li key={i}>{item}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {imageAnalysis.note && (
                  <p className="text-xs text-amber-600 dark:text-amber-400 italic">{imageAnalysis.note}</p>
                )}
              </CardContent>
            </Card>
          )}

          {/* Subdivision */}
          {subdiv && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Subdivision Potential</CardTitle>
              </CardHeader>
              <CardContent className="text-sm space-y-2">
                <Row label="Potential" value={subdiv.subdivision_potential ? "Yes" : "No"} highlight={subdiv.subdivision_potential} />
                {subdiv.subdivision_potential && (
                  <>
                    <Row label="Net Value Add" value={formatCurrency(subdiv.net_value_add)} bold />
                    <Row label="Costs" value={formatCurrency(subdiv.subdivision_costs || 0)} />
                  </>
                )}
                <p className="text-xs text-[var(--muted-foreground)]">{subdiv.reason}</p>
              </CardContent>
            </Card>
          )}

          {/* Score Breakdown */}
          {scores && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Score Breakdown</CardTitle>
              </CardHeader>
              <CardContent className="text-sm space-y-2">
                <ScoreBar label="ROI" score={scores.roi_score} weight={40} />
                <ScoreBar label="Timeline" score={scores.timeline_score} weight={15} />
                <ScoreBar label="Confidence" score={scores.confidence_score} weight={15} />
                <ScoreBar label="Subdivision" score={scores.subdivision_score} weight={15} />
                <ScoreBar label="Location" score={scores.location_score} weight={10} />
                <ScoreBar label="Insurability" score={scores.insurability_score} weight={5} />
              </CardContent>
            </Card>
          )}

          {/* Flags & Next Steps */}
          {(analysis.flags.length > 0 || analysis.next_steps.length > 0) && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Flags & Next Steps</CardTitle>
              </CardHeader>
              <CardContent className="text-sm space-y-3">
                {analysis.flags.length > 0 && (
                  <div>
                    <p className="font-medium flex items-center gap-1 mb-1"><AlertTriangle className="h-4 w-4 text-amber-500" /> Flags</p>
                    <ul className="space-y-1">
                      {analysis.flags.map((f, i) => (
                        <li key={i} className="text-xs text-amber-700 dark:text-amber-400 flex items-start gap-1">
                          <span className="mt-0.5">&#8226;</span> {f}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {analysis.next_steps.length > 0 && (
                  <div>
                    <p className="font-medium flex items-center gap-1 mb-1"><CheckCircle2 className="h-4 w-4 text-emerald-500" /> Next Steps</p>
                    <ul className="space-y-1">
                      {analysis.next_steps.map((s, i) => (
                        <li key={i} className="text-xs text-[var(--muted-foreground)] flex items-start gap-1">
                          <span className="mt-0.5">{i + 1}.</span> {s}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Description */}
      {listing.description && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Listing Description</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-[var(--muted-foreground)] whitespace-pre-wrap leading-relaxed">
              {listing.description}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ===== Helper components =====

function Row({ label, value, bold, sub, highlight }: {
  label: string;
  value: string;
  bold?: boolean;
  sub?: string;
  highlight?: boolean;
}) {
  return (
    <div className="flex justify-between items-center">
      <span className="text-[var(--muted-foreground)]">{label}</span>
      <span className={`${bold ? "font-semibold" : ""} ${highlight ? "text-emerald-600" : ""}`}>
        {value}
        {sub && <span className="text-xs text-[var(--muted-foreground)] ml-1">{sub}</span>}
      </span>
    </div>
  );
}

function ScoreBar({ label, score, weight }: { label: string; score: number; weight: number }) {
  const width = Math.max(0, Math.min(100, score));
  const color = score >= 70 ? "bg-emerald-500" : score >= 40 ? "bg-amber-500" : "bg-red-500";
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span>{label} ({weight}%)</span>
        <span className="font-medium">{score.toFixed(0)}</span>
      </div>
      <div className="h-2 rounded-full bg-[var(--muted)] overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${width}%` }} />
      </div>
    </div>
  );
}
