"""
Mathematical weighting and scoring pipeline.
- Base weight vector (frozen at development time)
- Dynamic multipliers by gender and identity
- Tier 1/2 classification before weighting
"""
from schemas import Property

# Base weight vector (Σ = 1.0)
BASE_WEIGHT_VECTOR = {
    "price_fit_score": 0.30,
    "security_score": 0.25,
    "facilities_score": 0.20,
    "lifestyle_proximity_score": 0.15,
    "maintenance_fee_score": 0.05,  # Negative score: (1 - maintenance)
    "transit_proximity_score": 0.05,
}

# Gender multipliers
GENDER_MULTIPLIERS = {
    "female": {
        "security_score": 1.30,
        "lifestyle_proximity_score": 1.15,
    },
    "male": {},
    "prefer_not_to_say": {},
}

# Identity multipliers
IDENTITY_MULTIPLIERS = {
    "first_time_buyer": {
        "price_fit_score": 1.30,
        "facilities_score": 1.10,
        "maintenance_fee_score": 1.20,
    },
    "investor": {
        "maintenance_fee_score": 1.25,
        "transit_proximity_score": 1.30,
    },
    "upgrader": {
        "facilities_score": 1.20,
        "security_score": 1.15,
    },
}


def apply_dynamic_weights(
    base: dict,
    gender: str,
    identity: str,
) -> dict:
    """
    Apply gender and identity multipliers, then normalize to Σ = 1.0.
    Strict validation: assert final sum = 1.0 (within floating point tolerance).
    """
    adjusted = base.copy()

    # Apply gender multipliers
    for dim, multiplier in GENDER_MULTIPLIERS.get(gender, {}).items():
        adjusted[dim] *= multiplier

    # Apply identity multipliers
    for dim, multiplier in IDENTITY_MULTIPLIERS.get(identity, {}).items():
        adjusted[dim] *= multiplier

    # Normalize
    total = sum(adjusted.values())
    assert total > 0, f"Weight sum is zero, normalization failed: {adjusted}"

    normalized = {k: v / total for k, v in adjusted.items()}

    # Strict validation
    final_sum = sum(normalized.values())
    assert abs(final_sum - 1.0) < 1e-9, (
        f"Normalized weights don't sum to 1.0: {final_sum}. Weights: {normalized}"
    )

    return normalized


def compute_weighted_score(
    property: Property,
    weights: dict,
) -> float:
    """
    Compute weighted score for a single property.
    maintenance_fee_score is inverted: (1 - normalized_maintenance_fee)
    """
    return (
        weights["price_fit_score"] * property.price_fit_score +
        weights["security_score"] * property.security_score +
        weights["facilities_score"] * property.facilities_score +
        weights["lifestyle_proximity_score"] * property.lifestyle_proximity_score +
        weights["maintenance_fee_score"] * (1 - property.normalized_maintenance_fee) +
        weights["transit_proximity_score"] * property.transit_proximity_score
    )


def build_top10(
    tier1_pool: list[Property],
    tier2_pool: list[Property],
    weight_vector: dict,
) -> list[tuple[float, Property, str]]:
    """
    Build Top 10 from Tier 1 and Tier 2 pools.
    Returns: list of (score, property, tier) tuples, sorted descending by score.

    Priority: Tier 1 first (if >= 10), then fill with Tier 2.
    """
    scored_tier1 = [
        (compute_weighted_score(p, weight_vector), p, "tier_1")
        for p in tier1_pool
    ]
    scored_tier1.sort(reverse=True)

    if len(scored_tier1) >= 10:
        return scored_tier1[:10]

    # Need to fill with Tier 2
    needed = 10 - len(scored_tier1)
    scored_tier2 = [
        (compute_weighted_score(p, weight_vector), p, "tier_2")
        for p in tier2_pool
    ]
    scored_tier2.sort(reverse=True)

    return scored_tier1 + scored_tier2[:needed]

