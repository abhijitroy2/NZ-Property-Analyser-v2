"""
Insurability Check.
Verifies property can be insured and estimates annual premium.
"""

from typing import Dict, Any

from app.services.external.insurance_api import InsuranceAPIClient


def check_insurability(listing_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if property is insurable and get estimated annual premium.
    
    Args:
        listing_data: Dict with address, floor_area, bedrooms etc.
    
    Returns:
        Dict with insurability status and premium.
    """
    address = listing_data.get("address", "")
    
    property_details = {
        "bedrooms": listing_data.get("bedrooms", 3),
        "bathrooms": listing_data.get("bathrooms", 1),
        "floor_area": listing_data.get("floor_area"),
        "land_area": listing_data.get("land_area"),
        "property_type": listing_data.get("property_type", "house"),
    }

    client = InsuranceAPIClient()
    quote = client.get_insurance_quote(address, property_details)

    insurable = quote.get("insurable", True)
    annual_premium = quote.get("annual_insurance", 2000)

    return {
        "insurable": insurable,
        "annual_insurance": annual_premium,
        "insurer": quote.get("insurer", ""),
        "source": quote.get("source", "estimate"),
        "note": quote.get("note", ""),
    }
