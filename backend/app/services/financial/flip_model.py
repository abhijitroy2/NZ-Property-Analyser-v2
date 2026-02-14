"""
Flip Financial Model.
Based on the 5 Belfield Coombe approach from the algorithm spec.
Calculates profit and ROI for a flip (buy-renovate-sell) scenario.
"""

from typing import Dict, Any, Optional


def calculate_flip_financials(
    listing: Dict[str, Any],
    analysis: Dict[str, Any],
    interest_rate_override: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Calculate flip scenario profit & ROI.
    
    Args:
        listing: Dict with at least 'price_display' (numeric purchase price).
        analysis: Dict with 'renovation', 'arv', 'timeline', 'council', 'insurability' sub-dicts.
        interest_rate_override: Optional interest rate override for scenario modeling.
    
    Returns:
        Dict with full flip financial breakdown.
    """
    purchase_price = listing.get("price_display", 0) or 0
    reno = analysis.get("renovation", {})
    reno_cost = reno.get("total_estimated", 60000)
    arv = analysis.get("arv", {}).get("estimated_arv", 0) or 0
    timeline_weeks = analysis.get("timeline", {}).get("estimated_weeks", 8)
    annual_rates = analysis.get("council", {}).get("annual_rates", 3000)

    if purchase_price <= 0:
        return _empty_flip_result()

    # INCOME
    sale_price = arv if arv > 0 else purchase_price * 1.2  # Default to 20% markup if no ARV

    # EXPENSES
    purchase_costs = 5000  # Legal, due diligence

    # GST refund on renovation (if GST registered)
    gst_refund = reno_cost * 0.15
    net_reno_cost = reno_cost - gst_refund

    # Holding costs
    timeline_months = timeline_weeks / 4.33
    interest_rate = interest_rate_override if interest_rate_override is not None else 0.054  # 5.4%
    interest_cost = purchase_price * interest_rate * (timeline_months / 12)

    # Insurance during hold
    insurance = 1000 * (timeline_months / 12)

    # Rates during hold
    rates_cost = annual_rates * (timeline_months / 12)

    # Selling costs
    commission = sale_price * 0.0345  # 3.45% typical
    legal_sell = 2000
    marketing = 8500
    accounting = 2500

    total_expenses = (
        purchase_price
        + purchase_costs
        + net_reno_cost
        + interest_cost
        + insurance
        + rates_cost
        + commission
        + legal_sell
        + marketing
        + accounting
    )

    # PROFIT
    gross_profit = sale_price - total_expenses
    tax = gross_profit * 0.33 if gross_profit > 0 else 0  # 33% tax rate
    net_profit = gross_profit - tax

    # ROI
    cash_invested = purchase_price + purchase_costs + reno_cost
    roi = net_profit / cash_invested if cash_invested > 0 else 0

    return {
        "strategy": "FLIP",
        "purchase_price": round(purchase_price, 2),
        "renovation_cost": round(reno_cost, 2),
        "gst_refund": round(gst_refund, 2),
        "net_reno_cost": round(net_reno_cost, 2),
        "arv": round(sale_price, 2),
        "timeline_weeks": timeline_weeks,
        "timeline_months": round(timeline_months, 1),
        "interest_rate": interest_rate,
        "interest_cost": round(interest_cost, 2),
        "insurance_cost": round(insurance, 2),
        "rates_cost": round(rates_cost, 2),
        "purchase_costs": purchase_costs,
        "commission": round(commission, 2),
        "legal_sell": legal_sell,
        "marketing": marketing,
        "accounting": accounting,
        "total_expenses": round(total_expenses, 2),
        "gross_profit": round(gross_profit, 2),
        "tax": round(tax, 2),
        "net_profit": round(net_profit, 2),
        "cash_invested": round(cash_invested, 2),
        "roi_percentage": round(roi * 100, 2),
        "meets_15_roi": roi >= 0.15,
    }


def _empty_flip_result() -> Dict[str, Any]:
    return {
        "strategy": "FLIP",
        "purchase_price": 0,
        "renovation_cost": 0,
        "gst_refund": 0,
        "net_reno_cost": 0,
        "arv": 0,
        "timeline_weeks": 0,
        "timeline_months": 0,
        "interest_rate": 0.054,
        "interest_cost": 0,
        "insurance_cost": 0,
        "rates_cost": 0,
        "purchase_costs": 0,
        "commission": 0,
        "legal_sell": 0,
        "marketing": 0,
        "accounting": 0,
        "total_expenses": 0,
        "gross_profit": 0,
        "tax": 0,
        "net_profit": 0,
        "cash_invested": 0,
        "roi_percentage": 0,
        "meets_15_roi": False,
    }
