# NZ Property Investment Evaluation Algorithm
## For TradeMe Property Scanning & Analysis

---

## 1. SYSTEM ARCHITECTURE

### 1.1 Data Pipeline
```
TradeMe API → Data Ingestion → Filtering Pipeline → Scoring Engine → Financial Models → Output Dashboard
                    ↓
              External APIs:
              - Tenancy.govt.nz (bond data)
              - Stats NZ (population/growth)
              - Council APIs (rates, zoning)
              - Initio (insurance quotes)
              - OpenAI / Anthropic / Google / Vertex (AI vision for image analysis)
```

### 1.2 Analysis Mode (Fork)

- **`legacy`** (default): Vision returns condition signals (`overall_reno_level`, `key_renovation_items`); `renovation.py` and `timeline.py` compute cost and weeks from rules.
- **`openai_deep`**: Vision prompt returns `estimated_renovation_cost_nzd` and `estimated_timeline_weeks` directly; legacy modules skipped. Single vision call per listing.

### 1.3 Caching (Cost Savings)

- **Vision cache**: When re-analyzing, if `Analysis.vision_photos_hash` matches current photos, reuse cached `image_analysis` (skip OpenAI call).
- **Subdivision cache**: When `Analysis.subdivision_input_hash` matches (address, district, region, land_area), reuse cached subdivision results (skip geocoding/zone API).

### 1.4 Processing Flow
1. **Scrape**: Pull new listings via TradeMe API (URLs from DB or `.env` TRADEME_SEARCH_URLS)
2. **Stage 1 Filter**: Hard dealbreakers (price, title type, population)
3. **Stage 2 Analysis**: Deep dive on survivors (vision, renovation, ARV, rent, rates, subdivision). Vision and subdivision use caches when inputs unchanged.
4. **Stage 3 Financials**: Flip ROI, rental yield, strategy decision
5. **Scoring**: Composite score, verdict, flags
6. **Output**: Interactive dashboard with ranked results. Scheduled job can run daily (ENABLE_SCHEDULER) with rate limiting (VISION_RATE_LIMIT_DELAY_SECONDS) to avoid OpenAI 200k TPM.

---

## 2. STAGE 1: HARD FILTERS (Dealbreakers)

### 2.1 Price Filter
```python
def filter_price(listing):
    """Max budget: $500k"""
    asking_price = listing['price_display']
    
    if asking_price > 500000:
        return REJECT, "Over budget"
    
    return PASS
```

### 2.2 Title Type Filter
```python
def filter_title(listing):
    """Reject: Unit title, Leasehold, Cross-lease"""
    title_type = listing['title_type'].lower()
    
    reject_types = ['unit title', 'leasehold', 'cross lease', 'cross-lease']
    
    if any(reject in title_type for reject in reject_types):
        return REJECT, f"Title type: {title_type}"
    
    return PASS
```

### 2.3 Location Population Filter
```python
def filter_population(listing):
    """Min 50k population + growth trajectory"""
    suburb = listing['suburb']
    territorial_authority = get_territorial_authority(suburb)
    
    # Get Stats NZ data
    current_pop = get_population(territorial_authority, year=2024)
    pop_2020 = get_population(territorial_authority, year=2020)
    pop_2015 = get_population(territorial_authority, year=2015)
    projected_2030 = get_projected_population(territorial_authority, year=2030)
    
    # Calculate growth rates
    historical_growth = (current_pop - pop_2015) / pop_2015
    projected_growth = (projected_2030 - current_pop) / current_pop
    
    if current_pop < 50000:
        return REJECT, f"Population {current_pop} below 50k threshold"
    
    if historical_growth < 0 and projected_growth < 0:
        return REJECT, "Declining population"
    
    return PASS, {
        'current_pop': current_pop,
        'historical_growth': historical_growth,
        'projected_growth': projected_growth
    }
```

### 2.4 Property Type Filter
```python
def filter_property_type(listing):
    """Check if property type matches local demand"""
    bedrooms = listing['bedrooms']
    suburb = listing['suburb']
    
    # Check local demand profile
    demand_profile = get_demand_profile(suburb)
    # e.g., {"student_town": True, "multi_bedroom_demand": True}
    #       {"family_area": True, "3_bedroom_demand": True}
    
    # This is a soft filter - doesn't reject, but adjusts scoring
    return PASS, demand_profile
```

---

## 3. STAGE 2: DEEP ANALYSIS

### 3.1 Insurability Check
```python
def check_insurability(listing):
    """Critical: Must be insurable via Initio or similar"""
    address = listing['address']
    
    # Call Initio API (or similar)
    insurance_quote = get_insurance_quote(address)
    
    if insurance_quote is None or insurance_quote == 'DECLINED':
        return REJECT, "Uninsurable property"
    
    annual_premium = insurance_quote['annual_premium']
    
    return PASS, {
        'annual_insurance': annual_premium,
        'insurer': insurance_quote['provider']
    }
```

### 3.2 Image Analysis for Renovation Complexity
```python
def analyze_renovation_needs(listing):
    """Use CV to estimate renovation scope from photos"""
    photos = listing['photos']
    
    analysis = {
        'roof_condition': None,      # NEW_IRON, OLD_IRON, TILES, NEEDS_REPLACE
        'exterior_condition': None,  # EXCELLENT, GOOD, FAIR, POOR
        'interior_quality': None,    # MODERN, DATED, VERY_DATED, DERELICT
        'kitchen_age': None,         # 0-5yr, 5-10yr, 10-20yr, 20+yr
        'bathroom_age': None,        # 0-5yr, 5-10yr, 10-20yr, 20+yr
        'structural_concerns': [],   # list of visible issues
        'overall_reno_level': None   # COSMETIC, MODERATE, MAJOR, FULL_GUT
    }
    
    # Process images with Google Vision API or custom ML model
    for photo in photos:
        features = analyze_image(photo)
        
        # Roof detection
        if 'roof' in features['labels']:
            roof_condition = classify_roof_condition(features)
            analysis['roof_condition'] = roof_condition
        
        # Exterior cladding
        if 'exterior' in features['labels']:
            exterior = classify_exterior(features)
            analysis['exterior_condition'] = exterior
        
        # Interior spaces
        if 'kitchen' in features['labels']:
            kitchen_age = estimate_kitchen_age(features)
            analysis['kitchen_age'] = kitchen_age
        
        if 'bathroom' in features['labels']:
            bathroom_age = estimate_bathroom_age(features)
            analysis['bathroom_age'] = bathroom_age
        
        # Structural issues
        structural = detect_structural_issues(features)
        analysis['structural_concerns'].extend(structural)
    
    # Classify overall renovation level
    analysis['overall_reno_level'] = classify_renovation_level(analysis)
    
    return analysis
```

### 3.3 Renovation Cost Estimation
```python
def estimate_renovation_cost(listing, image_analysis):
    """Estimate reno costs based on property and image analysis"""
    
    floor_area = listing.get('floor_area', estimate_floor_area(listing))
    reno_level = image_analysis['overall_reno_level']
    
    # Base costs per sqm (NZ 2025 rates)
    costs_per_sqm = {
        'COSMETIC': 500,      # Paint, minor fixes, landscaping
        'MODERATE': 1200,     # Kitchen/bathroom refresh, flooring
        'MAJOR': 2000,        # Full kitchen/bath, rewire, replumb
        'FULL_GUT': 3500      # Strip to frame, full rebuild interior
    }
    
    base_cost = floor_area * costs_per_sqm[reno_level]
    
    # Add specific costs from image analysis
    additional_costs = 0
    
    if image_analysis['roof_condition'] == 'NEEDS_REPLACE':
        roof_area = floor_area * 1.3  # rough estimate
        additional_costs += roof_area * 80  # $80/sqm for new roof
    
    if 'weatherboard_rot' in image_analysis['structural_concerns']:
        additional_costs += 15000  # typical weatherboard repair
    
    if 'foundation_issues' in image_analysis['structural_concerns']:
        additional_costs += 30000  # foundation work
    
    total_estimated_cost = base_cost + additional_costs
    
    # Add contingency
    contingency = total_estimated_cost * 0.15
    
    return {
        'base_renovation': base_cost,
        'additional_items': additional_costs,
        'contingency': contingency,
        'total_estimated': total_estimated_cost + contingency,
        'renovation_level': reno_level
    }
```

### 3.4 Timeline Estimation
```python
def estimate_timeline(reno_cost_breakdown):
    """Estimate weeks on tools, excluding consents"""
    
    reno_level = reno_cost_breakdown['renovation_level']
    
    # Typical timelines (weeks on tools)
    timelines = {
        'COSMETIC': 2,       # 2 weeks
        'MODERATE': 6,       # 6 weeks
        'MAJOR': 12,         # 12 weeks
        'FULL_GUT': 20       # 20 weeks
    }
    
    estimated_weeks = timelines[reno_level]
    
    # Check against 8-week target
    within_target = estimated_weeks <= 8
    
    return {
        'estimated_weeks': estimated_weeks,
        'within_8_week_target': within_target
    }
```

### 3.5 ARV (After Repair Value) Estimation
```python
def estimate_arv(listing, reno_analysis):
    """Estimate post-renovation value using comparable sales"""
    
    # Get comparable sales from TradeMe sold listings
    comparables = get_comparable_sales(
        suburb=listing['suburb'],
        bedrooms=listing['bedrooms'],
        land_area_range=(listing['land_area'] * 0.8, listing['land_area'] * 1.2),
        sold_within_months=12,
        condition='GOOD_TO_EXCELLENT'  # Post-reno condition
    )
    
    if len(comparables) < 3:
        # Widen search radius
        comparables = get_comparable_sales(
            region=listing['region'],
            bedrooms=listing['bedrooms'],
            sold_within_months=12,
            condition='GOOD_TO_EXCELLENT'
        )
    
    # Calculate price per sqm
    comp_prices_per_sqm = [c['price'] / c['floor_area'] for c in comparables]
    median_price_per_sqm = median(comp_prices_per_sqm)
    
    # Estimate floor area if not provided
    floor_area = listing.get('floor_area', estimate_floor_area(listing))
    
    # Calculate ARV
    estimated_arv = floor_area * median_price_per_sqm
    
    # Adjust for specific features
    if listing.get('has_garage'):
        estimated_arv += 30000
    
    if listing.get('land_area') > 800:  # Large section
        estimated_arv += 20000
    
    # Confidence score based on number/quality of comps
    confidence = calculate_confidence(comparables, listing)
    
    return {
        'estimated_arv': estimated_arv,
        'price_per_sqm': median_price_per_sqm,
        'comparables_used': len(comparables),
        'confidence_score': confidence,
        'comparable_sales': comparables[:5]  # Top 5 for reference
    }
```

### 3.6 Rental Income Estimation
```python
def estimate_rental_income(listing):
    """Estimate weekly rent using tenancy.govt bond data"""
    
    suburb = listing['suburb']
    bedrooms = listing['bedrooms']
    property_type = listing['property_type']  # house vs unit
    
    # Get bond lodgement data
    bonds = get_bond_data(
        suburb=suburb,
        bedrooms=bedrooms,
        property_type=property_type,
        within_months=12
    )
    
    if len(bonds) < 5:
        # Expand search to wider area
        bonds = get_bond_data(
            region=listing['region'],
            bedrooms=bedrooms,
            property_type=property_type,
            within_months=12
        )
    
    # Calculate median weekly rent
    weekly_rents = [b['weekly_rent'] for b in bonds]
    median_rent = median(weekly_rents)
    
    # Calculate gross yield at this rent
    purchase_price = listing['price_display']
    annual_rent = median_rent * 52
    gross_yield = annual_rent / purchase_price
    
    return {
        'estimated_weekly_rent': median_rent,
        'annual_rent': annual_rent,
        'gross_yield_percentage': gross_yield * 100,
        'bond_samples': len(bonds)
    }
```

### 3.7 Council Rates Check
```python
def get_council_rates(listing):
    """Fetch annual council rates"""
    address = listing['address']
    
    # Call council API or scrape council website
    rates_data = fetch_council_rates(address)
    
    return {
        'annual_rates': rates_data['total_rates'],
        'water_charges': rates_data.get('water_charges', 0),
        'total_council_costs': rates_data['total_rates'] + rates_data.get('water_charges', 0)
    }
```

### 3.8 Subdivision Potential Analysis
```python
def analyze_subdivision_potential(listing):
    """Check if property has subdivision potential - weighted scoring factor"""
    
    land_area = listing['land_area']
    zoning = get_zoning(listing['address'])
    
    # Minimum land areas for subdivision (varies by zone)
    min_areas = {
        'RESIDENTIAL_SINGLE': 600,   # Typical min for subdivision
        'RESIDENTIAL_MIXED': 400,
        'RESIDENTIAL_MEDIUM': 300,
        'RESIDENTIAL_HIGH': 200
    }
    
    min_required = min_areas.get(zoning, 600)
    
    subdivision_possible = land_area >= min_required * 2  # Need land for 2 lots
    
    if not subdivision_possible:
        return {
            'subdivision_potential': False,
            'reason': 'Insufficient land area',
            'value_uplift': 0
        }
    
    # Estimate value uplift from subdivision
    # Rough estimate: extra lot worth 60% of current land value
    land_value = listing['price_display'] * 0.3  # Assume 30% is land
    subdivision_uplift = land_value * 0.6
    
    # Account for subdivision costs
    subdivision_costs = 80000  # Survey, consents, legals, services
    
    net_subdivision_value = subdivision_uplift - subdivision_costs
    
    return {
        'subdivision_potential': True,
        'land_area': land_area,
        'zoning': zoning,
        'estimated_uplift': net_subdivision_value,
        'subdivision_costs': subdivision_costs,
        'net_value_add': net_subdivision_value
    }
```

---

## 4. STAGE 3: FINANCIAL MODELING

### 4.1 Flip Model (Based on 5 Belfield Coombe)
```python
def calculate_flip_financials(listing, analysis):
    """Calculate flip scenario profit & ROI"""
    
    purchase_price = listing['price_display']
    reno_cost = analysis['renovation']['total_estimated']
    arv = analysis['arv']['estimated_arv']
    timeline_weeks = analysis['timeline']['estimated_weeks']
    
    # INCOME
    sale_price = arv
    
    # EXPENSES
    purchase_costs = 5000  # Legal, due diligence
    
    # Renovation (get 15% GST back if registered)
    gst_refund = reno_cost * 0.15
    net_reno_cost = reno_cost - gst_refund
    
    # Holding costs (timeline in months)
    timeline_months = timeline_weeks / 4.33
    interest_rate = 0.054  # 5.4% from your flip
    interest_cost = purchase_price * interest_rate * (timeline_months / 12)
    
    # Insurance during hold
    insurance = 1000 * (timeline_months / 12)
    
    # Rates during hold
    annual_rates = analysis['council']['annual_rates']
    rates_cost = annual_rates * (timeline_months / 12)
    
    # Selling costs
    commission = sale_price * 0.0345  # 3.45% typical
    legal_sell = 2000
    marketing = 8500
    accounting = 2500
    
    total_expenses = (
        purchase_price +
        purchase_costs +
        net_reno_cost +
        interest_cost +
        insurance +
        rates_cost +
        commission +
        legal_sell +
        marketing +
        accounting
    )
    
    # PROFIT
    gross_profit = sale_price - total_expenses
    tax = gross_profit * 0.33  # 33% tax rate
    net_profit = gross_profit - tax
    
    # ROI
    cash_invested = purchase_price + purchase_costs + reno_cost
    roi = net_profit / cash_invested
    
    return {
        'strategy': 'FLIP',
        'purchase_price': purchase_price,
        'renovation_cost': reno_cost,
        'gst_refund': gst_refund,
        'arv': arv,
        'timeline_weeks': timeline_weeks,
        'timeline_months': timeline_months,
        'interest_cost': interest_cost,
        'total_expenses': total_expenses,
        'gross_profit': gross_profit,
        'tax': tax,
        'net_profit': net_profit,
        'cash_invested': cash_invested,
        'roi_percentage': roi * 100,
        'meets_15_roi': roi >= 0.15
    }
```

### 4.2 Rental Model (Based on 14 Ealing Street)
```python
def calculate_rental_financials(listing, analysis):
    """Calculate rental hold scenario - 1 year cashflow"""
    
    purchase_price = listing['price_display']
    purchase_costs = 5000
    reno_cost = analysis['renovation']['total_estimated']
    target_valuation = analysis['arv']['estimated_arv']
    
    weekly_rent = analysis['rental']['estimated_weekly_rent']
    annual_rent = weekly_rent * 50  # 50 weeks (vacancy allowance)
    
    # Total invested
    total_invested = purchase_price + purchase_costs + reno_cost
    
    # EXPENSES
    accounting = 1100
    bank_fees = 0
    insurance = analysis['insurability']['annual_insurance']
    
    # Interest on 100% debt
    interest_rate = 0.048  # 4.8% from your rental model
    annual_interest = total_invested * interest_rate
    tax_deductible_interest = annual_interest * 0.80  # 80% deductibility
    
    # Property management (10% + $300 + GST)
    prop_mgmt = (annual_rent * 0.10) + (300 * 1.15)
    
    # Rates
    annual_rates = analysis['council']['annual_rates']
    
    # Repairs & maintenance
    repairs = 500
    
    total_expenses = (
        accounting +
        bank_fees +
        insurance +
        tax_deductible_interest +
        prop_mgmt +
        annual_rates +
        repairs
    )
    
    # CASHFLOW
    net_cash_surplus = annual_rent - total_expenses
    
    # DEPRECIATION
    chattels_depreciation = reno_cost * 0.1  # Rough estimate
    
    # TAXABLE INCOME
    taxable_income = net_cash_surplus - chattels_depreciation
    tax_refund = max(0, abs(taxable_income) * 0.175) if taxable_income < 0 else 0
    tax_owed = taxable_income * 0.175 if taxable_income > 0 else 0
    
    overall_cash_surplus = net_cash_surplus + tax_refund - tax_owed
    
    # GROSS YIELD
    gross_yield = annual_rent / total_invested
    
    # NET YIELD (after all expenses)
    net_yield = overall_cash_surplus / total_invested
    
    return {
        'strategy': 'RENTAL',
        'purchase_price': purchase_price,
        'renovation_cost': reno_cost,
        'total_invested': total_invested,
        'target_valuation': target_valuation,
        'weekly_rent': weekly_rent,
        'annual_rent': annual_rent,
        'gross_yield_percentage': gross_yield * 100,
        'total_expenses': total_expenses,
        'net_cash_surplus': net_cash_surplus,
        'depreciation': chattels_depreciation,
        'tax_adjustment': tax_refund - tax_owed,
        'overall_annual_cashflow': overall_cash_surplus,
        'net_yield_percentage': net_yield * 100,
        'meets_9_yield': gross_yield >= 0.09
    }
```

### 4.3 Strategy Decision Logic
```python
def decide_strategy(flip_analysis, rental_analysis, subdivision_analysis):
    """Determine optimal strategy: FLIP or RENTAL"""
    
    flip_roi = flip_analysis['roi_percentage']
    rental_yield = rental_analysis['gross_yield_percentage']
    
    # Decision tree
    if flip_roi >= 15:
        if rental_yield >= 9:
            # Both viable - compare ROI
            if flip_roi > (rental_yield * 1.5):  # Flip significantly better
                recommended = 'FLIP'
                reason = f'Higher ROI: {flip_roi:.1f}% vs {rental_yield:.1f}% yield'
            else:
                recommended = 'RENTAL'
                reason = f'Good rental yield {rental_yield:.1f}% with long-term appreciation'
        else:
            recommended = 'FLIP'
            reason = f'ROI {flip_roi:.1f}% meets target, yield {rental_yield:.1f}% below 9%'
    
    elif rental_yield >= 9:
        recommended = 'RENTAL'
        reason = f'Rental yield {rental_yield:.1f}% meets target, flip ROI {flip_roi:.1f}% below 15%'
    
    else:
        recommended = 'PASS'
        reason = f'Neither strategy meets targets (Flip: {flip_roi:.1f}%, Rental: {rental_yield:.1f}%)'
    
    # Factor in subdivision potential
    if subdivision_analysis['subdivision_potential']:
        subdivision_value = subdivision_analysis['net_value_add']
        recommended += '_WITH_SUBDIVISION'
        reason += f' | Subdivision adds ~${subdivision_value:,.0f}'
    
    return {
        'recommended_strategy': recommended,
        'reason': reason,
        'flip_roi': flip_roi,
        'rental_yield': rental_yield,
        'subdivision_bonus': subdivision_analysis.get('net_value_add', 0)
    }
```

---

## 5. SCORING & RANKING SYSTEM

### 5.1 Composite Score Calculation
```python
def calculate_composite_score(analysis):
    """Generate weighted score for ranking properties"""
    
    weights = {
        'roi': 0.40,              # 40% - Most important
        'timeline': 0.15,         # 15% - Speed matters
        'confidence': 0.15,       # 15% - Data quality
        'subdivision': 0.15,      # 15% - Upside potential
        'location_growth': 0.10,  # 10% - Future potential
        'insurability': 0.05      # 5% - Risk factor
    }
    
    # ROI Score (0-100)
    strategy = analysis['strategy_decision']['recommended_strategy']
    if 'FLIP' in strategy:
        roi = analysis['flip']['roi_percentage']
        roi_score = min(100, (roi / 30) * 100)  # 30% ROI = perfect score
    elif 'RENTAL' in strategy:
        yield_pct = analysis['rental']['gross_yield_percentage']
        roi_score = min(100, (yield_pct / 15) * 100)  # 15% yield = perfect score
    else:
        roi_score = 0
    
    # Timeline Score (0-100)
    weeks = analysis['timeline']['estimated_weeks']
    if weeks <= 8:
        timeline_score = 100
    elif weeks <= 16:
        timeline_score = 100 - ((weeks - 8) * 5)  # Lose 5 pts per week over 8
    else:
        timeline_score = max(0, 60 - (weeks - 16) * 3)
    
    # Confidence Score (0-100)
    arv_confidence = analysis['arv']['confidence_score']
    rental_samples = analysis['rental']['bond_samples']
    confidence_score = (arv_confidence + min(100, rental_samples * 5)) / 2
    
    # Subdivision Score (0-100)
    if analysis['subdivision']['subdivision_potential']:
        subdivision_value = analysis['subdivision']['net_value_add']
        subdivision_score = min(100, (subdivision_value / 100000) * 100)
    else:
        subdivision_score = 0
    
    # Location Growth Score (0-100)
    pop_growth = analysis['population']['projected_growth']
    location_score = min(100, (pop_growth + 0.05) * 500)  # 5% growth = 50pts
    
    # Insurability Score (0-100)
    # Lower premium = better score
    annual_premium = analysis['insurability']['annual_insurance']
    insurability_score = max(0, 100 - (annual_premium / 30))  # $3k+ = 0 pts
    
    # Calculate composite
    composite = (
        roi_score * weights['roi'] +
        timeline_score * weights['timeline'] +
        confidence_score * weights['confidence'] +
        subdivision_score * weights['subdivision'] +
        location_score * weights['location_growth'] +
        insurability_score * weights['insurability']
    )
    
    return {
        'composite_score': composite,
        'component_scores': {
            'roi_score': roi_score,
            'timeline_score': timeline_score,
            'confidence_score': confidence_score,
            'subdivision_score': subdivision_score,
            'location_score': location_score,
            'insurability_score': insurability_score
        },
        'weights': weights
    }
```

---

## 6. OUTPUT FORMAT

### 6.1 Property Report Structure
```python
property_report = {
    'listing_id': '...',
    'address': '...',
    'listing_url': '...',
    
    # VERDICT
    'overall_verdict': 'STRONG_BUY' | 'BUY' | 'MAYBE' | 'PASS',
    'composite_score': 87.5,
    'rank': 3,  # Out of all properties evaluated
    
    # RECOMMENDED STRATEGY
    'recommended_strategy': {
        'strategy': 'FLIP_WITH_SUBDIVISION',
        'reason': 'High ROI with subdivision upside',
        'primary_metrics': {
            'flip_roi': 18.5,
            'rental_yield': 8.2,
            'subdivision_value': 120000
        }
    },
    
    # FINANCIAL SUMMARY
    'flip_scenario': {
        'purchase_price': 445000,
        'renovation_cost': 60000,
        'arv': 620000,
        'net_profit': 45000,
        'roi': 18.5,
        'timeline_weeks': 6
    },
    
    'rental_scenario': {
        'gross_yield': 8.2,
        'weekly_rent': 650,
        'annual_cashflow': 5000,
        'net_yield': 4.1
    },
    
    # PROPERTY DETAILS
    'property': {
        'bedrooms': 3,
        'bathrooms': 1,
        'land_area': 650,
        'floor_area': 120,
        'year_built': 1960
    },
    
    # ANALYSIS DETAILS
    'renovation': {
        'level': 'MODERATE',
        'estimated_cost': 60000,
        'timeline_weeks': 6,
        'key_items': ['Kitchen refresh', 'Bathroom upgrade', 'Paint interior/exterior']
    },
    
    'location': {
        'suburb': 'Northcote',
        'population': 78000,
        'growth_rate': 0.08,
        'demand_profile': 'Family area - 3br high demand'
    },
    
    'insurability': {
        'insurable': True,
        'annual_premium': 2200,
        'provider': 'Initio'
    },
    
    'subdivision': {
        'potential': True,
        'estimated_value_add': 120000,
        'costs': 80000,
        'net_value': 40000
    },
    
    # COMPARABLES
    'comparable_sales': [...],
    'rental_comps': [...],
    
    # FLAGS & RISKS
    'flags': [
        'Timeline exceeds 8 week target',
        'Limited comparable sales (only 3 in suburb)',
        'Weatherboard may need attention'
    ],
    
    'confidence_level': 'MEDIUM',
    
    # NEXT ACTIONS
    'next_steps': [
        'Request building report',
        'Get property manager rental appraisal',
        'Check council for subdivision feasibility',
        'View property in person'
    ]
}
```

### 6.2 Interactive Dashboard Features
```
1. Daily digest email/notification
   - New properties that passed filters
   - Ranked by composite score
   - Top 5 "hot deals" highlighted

2. Web dashboard with filters:
   - Strategy: [Flip | Rental | Either]
   - Min ROI: [slider 10-30%]
   - Max timeline: [slider 4-20 weeks]
   - Location: [multi-select regions/suburbs]
   - Score threshold: [slider 0-100]

3. Property detail view:
   - Interactive sliders to adjust:
     * Purchase offer price
     * Renovation budget
     * Sale/rental price assumptions
   - Real-time ROI recalculation
   - Scenario comparison (flip vs rental)
   
4. Saved searches & alerts
   - Set criteria, get email when match found
   - Watch list for specific properties
   
5. Portfolio view
   - Track properties you've actioned
   - Compare against original projections
```

---

## 7. IMPLEMENTATION ROADMAP

### Phase 1: MVP (Weeks 1-2)
- TradeMe API integration
- Hard filters (price, title, population)
- Basic ARV estimation (price/sqm)
- Simple flip/rental calculations
- CSV export of ranked properties

### Phase 2: Core Analysis (Weeks 3-4)
- Image analysis integration
- Renovation cost estimation
- Insurability checks (Initio)
- Rental data (Tenancy.govt)
- Council rates fetching
- Composite scoring

### Phase 3: Advanced Features (Weeks 5-6)
- Subdivision analysis
- Timeline estimation
- Confidence scoring
- Interactive dashboard
- Scenario modeling (adjustable inputs)

### Phase 4: Optimization (Weeks 7-8)
- ML model refinement (image analysis)
- Historical accuracy tracking
- Auto-learning from your actual deals
- Alert system & daily digests
- Mobile app/notifications

---

## 8. DATA SOURCES & APIS

### Required Integrations:
1. **TradeMe API** (Property listings)
   - Free tier: 1000 calls/hour authenticated
   - Catalogue methods: Unlimited unauthenticated

2. **Tenancy Services** (Bond data)
   - tenancy.govt.nz bond lodgement data
   - Public data - web scraping acceptable

3. **Stats NZ** (Population & demographics)
   - infoshare.stats.govt.nz
   - Free API access

4. **Council APIs** (Rates & zoning)
   - Most councils have open data portals
   - May require council-specific scrapers

5. **Initio** (Insurance quotes)
   - API access required
   - Alternative: Other insurers' APIs

6. **Google Vision API** (Image analysis)
   - Pay-per-call pricing
   - Consider: OpenAI GPT-4V or Anthropic Claude for vision

7. **Google Maps/Places API** (Location data)
   - For geocoding addresses
   - Radius searches

---

## 9. EXAMPLE WORKFLOW

```
Day 1 Morning:
- System pulls 50 new listings from TradeMe
- Stage 1 filters reject 35 (price, title, location)
- 15 properties move to deep analysis

Day 1 Afternoon:
- System analyzes 15 properties:
  * Fetches insurance quotes
  * Analyzes photos
  * Estimates reno costs
  * Pulls rental comps
  * Calculates ROI for both strategies
  * Generates composite scores

Evening:
- You receive email digest:
  "5 Strong Opportunities Today"
  
  #1: 24 Smith St, Hamilton (Score: 92/100)
      Strategy: FLIP | ROI: 22% | Timeline: 4 weeks
      
  #2: 16 Park Rd, Tauranga (Score: 88/100)
      Strategy: RENTAL | Yield: 10.2% | Subdivision potential
      
  ... etc

You click through to dashboard:
- Review #1 in detail
- Adjust offer price slider: $420k → $400k
- See ROI increase to 25%
- Add to watchlist
- Schedule viewing

Next day:
- Property manager confirms $680/week rent
- You update dashboard
- Rental yield now 10.5%
- System recommends: "Consider rental strategy"
- You make offer at $405k
```

---

## 10. SUCCESS METRICS

Track algorithm performance:
1. **Precision**: % of "BUY" recommendations that you actually pursue
2. **Recall**: % of your actual purchases that system flagged as "BUY"
3. **Accuracy**: ROI projections vs actual results
4. **Speed**: Time from listing to evaluation

Target metrics after 6 months:
- Precision: >70% (most recommendations are good)
- Recall: >90% (catches almost all good deals)
- ROI accuracy: ±3% of projection
- Evaluation time: <2 minutes per property

---

## NOTES & CONSIDERATIONS

1. **Aggressive false positive tolerance**: System is tuned to OVER-recommend (you'll manually filter), rather than miss opportunities

2. **Image analysis training**: Start with rule-based heuristics, then train ML model on your feedback over time

3. **Market timing**: Consider adding seasonal adjustments (summer = higher prices, winter = slower market)

4. **Lending changes**: Monitor for CCCFA updates, LVR changes that affect 100% lending assumption

5. **Regional variations**: Cost estimates may need region-specific calibration (Auckland vs provinces)

6. **Data quality**: Some listings have poor photos or incomplete info - flag these for manual review

7. **Off-market deals**: System only works for listed properties - supplement with agent relationships

8. **Competition tracking**: Consider monitoring "watchlist" counts or bidding activity if TradeMe provides

---

This algorithm gives you a systematic, data-driven approach to property evaluation while maintaining the flexibility to override with your expertise and gut feel. The interactive dashboard lets you test assumptions and learn what works in your specific market.
