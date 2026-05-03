import pytest

from app.services.risk_engine import RiskFactors, calculate_risk_score


def test_calculate_risk_score_low_risk() -> None:
    factors = RiskFactors(
        revenue=950_000.0,
        volatility=0.05,
        industry_risk=0.05,
        liquidity=0.05,
        leverage=0.05,
    )

    profile = calculate_risk_score(factors)

    assert profile.score <= 25.0
    assert profile.category == "low"
    assert profile.details["volatility"] == 0.05


def test_calculate_risk_score_high_risk() -> None:
    factors = RiskFactors(
        revenue=10_000.0,
        volatility=0.9,
        industry_risk=0.8,
        liquidity=0.8,
        leverage=0.9,
    )

    profile = calculate_risk_score(factors)

    assert profile.score >= 75.0
    assert profile.category in {"high", "critical"}
    assert profile.details["leverage"] == 0.9


def test_risk_factors_validation() -> None:
    with pytest.raises(ValueError):
        RiskFactors(
            revenue=-5.0,
            volatility=0.2,
            industry_risk=0.2,
            liquidity=0.2,
            leverage=0.2,
        )
