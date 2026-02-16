// ===== Listing Types =====
export interface Listing {
  id: number;
  listing_id: string;
  title: string;
  address: string;
  full_address: string;
  suburb: string;
  district: string;
  region: string;
  geographic_location: string;
  bedrooms: number | null;
  bathrooms: number | null;
  land_area: number | null;
  floor_area: number | null;
  capital_value: string;
  property_type: string;
  title_type: string;
  display_price: string;
  asking_price: number | null;
  estimated_market_price: string;
  estimated_weekly_rent: string;
  description: string;
  property_url: string;
  photos: string[];
  nearby_properties: NearbyProperty[];
  listing_date: string | null;
  filter_status: string;
  filter_rejection_reason: string;
  analysis_status: string;
  created_at: string;
  updated_at: string;
  composite_score: number | null;
  verdict: string | null;
  recommended_strategy: string | null;
}

export interface NearbyProperty {
  address: string;
  date: string;
  price: string;
  price_numeric: number | null;
  url: string;
}

export interface ListingListResponse {
  items: Listing[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ===== Analysis Types =====
export interface Analysis {
  id: number;
  listing_id: number;
  population_data: Record<string, any> | null;
  demand_profile: Record<string, any> | null;
  insurability: InsurabilityData | null;
  image_analysis: ImageAnalysis | null;
  renovation_estimate: RenovationEstimate | null;
  timeline_estimate: TimelineEstimate | null;
  arv_estimate: ARVEstimate | null;
  rental_estimate: RentalEstimate | null;
  council_rates: CouncilRates | null;
  subdivision_analysis: SubdivisionAnalysis | null;
  flip_financials: FlipFinancials | null;
  rental_financials: RentalFinancials | null;
  strategy_decision: StrategyDecision | null;
  composite_score: number | null;
  component_scores: ComponentScores | null;
  verdict: string;
  rank: number | null;
  flags: string[];
  next_steps: string[];
  confidence_level: string;
  created_at: string;
  updated_at: string;
}

export interface InsurabilityData {
  insurable: boolean;
  annual_insurance: number;
  insurer: string;
  source: string;
}

export interface ImageAnalysis {
  roof_condition?: string;
  exterior_condition?: string;
  interior_quality?: string;
  kitchen_age?: string;
  bathroom_age?: string;
  structural_concerns?: string[];
  overall_reno_level?: string;
  key_renovation_items?: string[];
  confidence?: string;
  source?: string;
  note?: string;
  renovation_indicators?: Record<string, boolean>;
}

export interface RenovationEstimate {
  renovation_level: string;
  floor_area_used: number;
  cost_per_sqm: number;
  base_renovation: number;
  additional_items: number;
  contingency: number;
  total_estimated: number;
  key_items: string[];
}

export interface TimelineEstimate {
  estimated_weeks: number;
  within_8_week_target: boolean;
  renovation_level: string;
  notes: string;
}

export interface ARVEstimate {
  estimated_arv: number;
  median_comp_price: number | null;
  comparables_used: number;
  confidence_score: number;
  comparable_sales: NearbyProperty[];
}

export interface RentalEstimate {
  estimated_weekly_rent: number;
  annual_rent: number;
  gross_yield_percentage: number;
  bond_samples: number;
  source: string;
}

export interface CouncilRates {
  annual_rates: number;
  water_charges: number;
  total_council_costs: number;
}

export interface SubdivisionAnalysis {
  subdivision_potential: boolean;
  land_area?: number;
  zoning?: string;
  extra_lots_possible?: number;
  estimated_uplift?: number;
  subdivision_costs?: number;
  net_value_add: number;
  reason: string;
}

export interface FlipFinancials {
  strategy: string;
  purchase_price: number;
  renovation_cost: number;
  gst_refund: number;
  arv: number;
  timeline_weeks: number;
  timeline_months: number;
  interest_rate: number;
  interest_cost: number;
  total_expenses: number;
  gross_profit: number;
  tax: number;
  net_profit: number;
  cash_invested: number;
  roi_percentage: number;
  meets_15_roi: boolean;
}

export interface RentalFinancials {
  strategy: string;
  purchase_price: number;
  renovation_cost: number;
  total_invested: number;
  weekly_rent: number;
  annual_rent: number;
  total_expenses: number;
  net_cash_surplus: number;
  overall_annual_cashflow: number;
  gross_yield_percentage: number;
  net_yield_percentage: number;
  meets_9_yield: boolean;
}

export interface StrategyDecision {
  recommended_strategy: string;
  reason: string;
  flip_roi: number;
  rental_yield: number;
  subdivision_bonus: number;
}

export interface ComponentScores {
  roi_score: number;
  timeline_score: number;
  confidence_score: number;
  subdivision_score: number;
  location_score: number;
  insurability_score: number;
}

// ===== Dashboard Types =====
export interface DashboardSummary {
  total_listings: number;
  passed_filters: number;
  rejected: number;
  pending: number;
  analyzed: number;
  verdicts: Record<string, number>;
  average_score: number;
  vision_counts?: Record<string, number>;
}

export interface TopDeal {
  id: number;
  listing_id: string;
  address: string;
  suburb: string;
  region: string;
  display_price: string;
  asking_price: number | null;
  bedrooms: number | null;
  bathrooms: number | null;
  composite_score: number | null;
  verdict: string;
  recommended_strategy: string;
  flip_roi: number;
  rental_yield: number;
  timeline_weeks: number;
  property_url: string;
  vision_source?: string;
  vision_confidence?: string;
}

// ===== Scenario Types =====
export interface ScenarioRequest {
  purchase_price?: number;
  renovation_budget?: number;
  sale_price?: number;
  weekly_rent?: number;
  interest_rate?: number;
  timeline_weeks?: number;
}

export interface ScenarioResponse {
  flip_financials: FlipFinancials;
  rental_financials: RentalFinancials;
  strategy_decision: StrategyDecision;
}

// ===== Property Report =====
export interface PropertyReport {
  listing_id: string;
  address: string;
  listing_url: string;
  overall_verdict: string;
  composite_score: number;
  rank: number | null;
  recommended_strategy: {
    strategy: string;
    reason: string;
    primary_metrics: {
      flip_roi: number;
      rental_yield: number;
      subdivision_value: number;
    };
  };
  flip_scenario: Record<string, any>;
  rental_scenario: Record<string, any>;
  property: Record<string, any>;
  renovation: Record<string, any>;
  location: Record<string, any>;
  insurability: Record<string, any>;
  subdivision: Record<string, any>;
  comparable_sales: any[];
  rental_comps: any[];
  flags: string[];
  confidence_level: string;
  next_steps: string[];
}

// ===== Portfolio Types =====
export interface PortfolioEntry {
  id: number;
  listing_id: number;
  status: string;
  purchase_price: number | null;
  actual_reno_cost: number | null;
  actual_sale_price: number | null;
  actual_weekly_rent: number | null;
  projected_reno_cost: number | null;
  projected_arv: number | null;
  projected_weekly_rent: number | null;
  projected_roi: number | null;
  notes: string;
  created_at: string;
  updated_at: string;
  reno_cost_variance: number | null;
  roi_variance: number | null;
}

// ===== Watchlist Types =====
export interface WatchlistItem {
  id: number;
  name: string;
  search_criteria: Record<string, any>;
  alert_enabled: boolean;
  last_alerted_at: string | null;
  created_at: string;
  updated_at: string;
  matching_count?: number;
}
