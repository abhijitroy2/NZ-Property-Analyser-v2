"""
Rental Financial Model.
Based on the 14 Ealing Street approach from the algorithm spec.
Calculates rental hold scenario - 1 year cashflow.
"""

from typing import Dict, Any, Optional


def calculate_rental_financials(
    listing: Dict[str, Any],
    analysis: Dict[str, Any],
    interest_rate_override: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Calculate rental hold scenario - 1 year cashflow.
    
    Args:
        listing: Dict with at least 'price_display' (numeric purchase price).
        analysis: Dict with 'renovation', 'arv', 'rental', 'council', 'insurability' sub-dicts.
        interest_rate_override: Optional interest rate override for scenario modeling.
    
    Returns:
        Dict with full rental financial breakdown.
    """
    purchase_price = listing.get("price_display", 0) or 0
    reno_cost = analysis.get("renovation", {}).get("total_estimated", 60000)
    weekly_rent = analysis.get("rental", {}).get("estimated_weekly_rent", 0) or 0
    annual_insurance = analysis.get("insurability", {}).get("annual_insurance", 2000)
    annual_rates = analysis.get("council", {}).get("annual_rates", 3000)
    target_valuation = analysis.get("arv", {}).get("estimated_arv", 0) or 0

    if purchase_price <= 0 or weekly_rent <= 0:
        return _empty_rental_result()

    purchase_costs = 5000
    total_invested = purchase_price + purchase_costs + reno_cost

    # Annual rent (50 weeks to account for vacancy)
    annual_rent = weekly_rent * 50

    # EXPENSES
    accounting = 1100
    bank_fees = 0
    insurance = annual_insurance

    # Interest on 100% debt
    interest_rate = interest_rate_override if interest_rate_override is not None else 0.048  # 4.8%
    annual_interest = total_invested * interest_rate
    tax_deductible_interest = annual_interest * 0.80  # 80% deductibility

    # Property management (10% + $300 letting fee + GST)
    prop_mgmt = (annual_rent * 0.10) + (300 * 1.15)

    # Repairs & maintenance
    repairs = 500

    total_expenses = (
        accounting
        + bank_fees
        + insurance
        + tax_deductible_interest
        + prop_mgmt
        + annual_rates
        + repairs
    )

    # CASHFLOW
    net_cash_surplus = annual_rent - total_expenses

    # DEPRECIATION
    chattels_depreciation = reno_cost * 0.1  # Rough estimate of depreciable chattels

    # TAXABLE INCOME
    taxable_income = net_cash_surplus - chattels_depreciation
    if taxable_income < 0:
        tax_refund = abs(taxable_income) * 0.175
        tax_owed = 0
    else:
        tax_refund = 0
        tax_owed = taxable_income * 0.175

    overall_cash_surplus = net_cash_surplus + tax_refund - tax_owed

    # YIELDS
    gross_yield = annual_rent / total_invested if total_invested > 0 else 0
    net_yield = overall_cash_surplus / total_invested if total_invested > 0 else 0

    return {
        "strategy": "RENTAL",
        "purchase_price": round(purchase_price, 2),
        "renovation_cost": round(reno_cost, 2),
        "purchase_costs": purchase_costs,
        "total_invested": round(total_invested, 2),
        "target_valuation": round(target_valuation, 2),
        "weekly_rent": round(weekly_rent, 2),
        "annual_rent": round(annual_rent, 2),
        "vacancy_weeks": 2,
        "accounting": accounting,
        "bank_fees": bank_fees,
        "insurance": round(insurance, 2),
        "interest_rate": interest_rate,
        "annual_interest": round(annual_interest, 2),
        "tax_deductible_interest": round(tax_deductible_interest, 2),
        "property_management": round(prop_mgmt, 2),
        "annual_rates": round(annual_rates, 2),
        "repairs": repairs,
        "total_expenses": round(total_expenses, 2),
        "net_cash_surplus": round(net_cash_surplus, 2),
        "chattels_depreciation": round(chattels_depreciation, 2),
        "taxable_income": round(taxable_income, 2),
        "tax_refund": round(tax_refund, 2),
        "tax_owed": round(tax_owed, 2),
        "overall_annual_cashflow": round(overall_cash_surplus, 2),
        "gross_yield_percentage": round(gross_yield * 100, 2),
        "net_yield_percentage": round(net_yield * 100, 2),
        "meets_9_yield": gross_yield >= 0.09,
    }


def _empty_rental_result() -> Dict[str, Any]:
    return {
        "strategy": "RENTAL",
        "purchase_price": 0,
        "renovation_cost": 0,
        "purchase_costs": 0,
        "total_invested": 0,
        "target_valuation": 0,
        "weekly_rent": 0,
        "annual_rent": 0,
        "vacancy_weeks": 2,
        "accounting": 0,
        "bank_fees": 0,
        "insurance": 0,
        "interest_rate": 0.048,
        "annual_interest": 0,
        "tax_deductible_interest": 0,
        "property_management": 0,
        "annual_rates": 0,
        "repairs": 0,
        "total_expenses": 0,
        "net_cash_surplus": 0,
        "chattels_depreciation": 0,
        "taxable_income": 0,
        "tax_refund": 0,
        "tax_owed": 0,
        "overall_annual_cashflow": 0,
        "gross_yield_percentage": 0,
        "net_yield_percentage": 0,
        "meets_9_yield": False,
    }
