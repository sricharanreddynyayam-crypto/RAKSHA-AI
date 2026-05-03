from dataclasses import dataclass
from datetime import datetime


@dataclass
class LocationPoint:
    lat: float
    lng: float
    timestamp: datetime
    speed_kmh: float = 0.0


@dataclass
class RiskInput:
    user_id: str
    current_location: LocationPoint
    previous_location: LocationPoint
    battery_percent: int
    sos_triggers_last_30min: int
    known_safe_locations: list
    usual_routes: list


@dataclass
class RiskResult:
    total_score: int
    band: str
    factors: dict
    explanation: str
    should_alert_contacts: bool


def compute_risk_score(risk_input: RiskInput, stationary_minutes: int = 0):

    score = 0
    factors = {}

    # Rule 1: Low battery
    if risk_input.battery_percent < 15:
        score += 20
        factors["low_battery"] = 20

    # Rule 2: Multiple SOS
    if risk_input.sos_triggers_last_30min >= 2:
        score += 40
        factors["sos_triggers"] = 40

    # Rule 3: No movement
    if stationary_minutes > 10:
        score += 20
        factors["no_movement"] = 20

    # Rule 4: Sudden stop
    if risk_input.previous_location.speed_kmh > 20 and risk_input.current_location.speed_kmh < 2:
        score += 20
        factors["sudden_stop"] = 20

    # Decide band
    if score >= 80:
        band = "DANGER"
        alert = True
    elif score >= 50:
        band = "ALERT"
        alert = True
    elif score >= 20:
        band = "WATCH"
        alert = False
    else:
        band = "SAFE"
        alert = False

    explanation = f"Risk score is {score} due to factors: {list(factors.keys())}"

    return RiskResult(
        total_score=score,
        band=band,
        factors=factors,
        explanation=explanation,
        should_alert_contacts=alert
    )
