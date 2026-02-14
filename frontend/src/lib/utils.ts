import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(value: number | null | undefined): string {
  if (value == null) return "N/A";
  return new Intl.NumberFormat("en-NZ", {
    style: "currency",
    currency: "NZD",
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatPercent(value: number | null | undefined, decimals = 1): string {
  if (value == null) return "N/A";
  return `${value.toFixed(decimals)}%`;
}

export function formatNumber(value: number | null | undefined): string {
  if (value == null) return "N/A";
  return new Intl.NumberFormat("en-NZ").format(value);
}

export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "N/A";
  return new Date(dateStr).toLocaleDateString("en-NZ", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function verdictColor(verdict: string | null | undefined): string {
  switch (verdict) {
    case "STRONG_BUY": return "text-emerald-600 bg-emerald-50 border-emerald-200";
    case "BUY": return "text-green-600 bg-green-50 border-green-200";
    case "MAYBE": return "text-amber-600 bg-amber-50 border-amber-200";
    case "PASS": return "text-red-600 bg-red-50 border-red-200";
    default: return "text-gray-500 bg-gray-50 border-gray-200";
  }
}

export function verdictLabel(verdict: string | null | undefined): string {
  switch (verdict) {
    case "STRONG_BUY": return "Strong Buy";
    case "BUY": return "Buy";
    case "MAYBE": return "Maybe";
    case "PASS": return "Pass";
    default: return "Pending";
  }
}

export function scoreColor(score: number | null | undefined): string {
  if (score == null) return "text-gray-400";
  if (score >= 75) return "text-emerald-600";
  if (score >= 55) return "text-green-600";
  if (score >= 35) return "text-amber-600";
  return "text-red-600";
}

export function strategyLabel(strategy: string | null | undefined): string {
  if (!strategy) return "N/A";
  return strategy
    .replace(/_/g, " ")
    .replace("WITH SUBDIVISION", "+ Subdivision")
    .replace("FLIP", "Flip")
    .replace("RENTAL", "Rental")
    .replace("PASS", "Pass");
}
