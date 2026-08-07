"""Production Impact Analysis (module 14): translates a predicted shipment delay into
estimated production-line stoppage days and financial cost."""

DEFAULT_BUFFER_DAYS = 2.0  # typical safety stock buffer before a delay actually halts the line
DEFAULT_DAILY_PRODUCTION_VALUE_USD = 8000.0  # conservative mid-size apparel line output/day


def estimate_production_impact(
    predicted_delay_days: float,
    order_quantity: float,
    buffer_days: float = DEFAULT_BUFFER_DAYS,
    daily_production_value_usd: float = DEFAULT_DAILY_PRODUCTION_VALUE_USD,
) -> dict:
    stoppage_days = max(0.0, predicted_delay_days - buffer_days)
    estimated_cost_usd = stoppage_days * daily_production_value_usd
    severity = "none"
    if stoppage_days > 0:
        severity = "low" if stoppage_days <= 2 else "medium" if stoppage_days <= 5 else "high"

    return {
        "predicted_delay_days": round(predicted_delay_days, 2),
        "buffer_days": buffer_days,
        "estimated_production_stoppage_days": round(stoppage_days, 2),
        "estimated_cost_impact_usd": round(estimated_cost_usd, 2),
        "affected_order_quantity": order_quantity,
        "severity": severity,
        "explanation": (
            f"A predicted delay of {predicted_delay_days:.1f} days exceeds the {buffer_days:.0f}-day safety buffer "
            f"by {stoppage_days:.1f} days, projected to cost approximately USD {estimated_cost_usd:,.0f} in lost "
            f"production output."
            if stoppage_days > 0
            else f"The predicted delay of {predicted_delay_days:.1f} days is within the {buffer_days:.0f}-day safety "
            f"buffer, so no production stoppage is expected."
        ),
    }
