from src.report_helpers import group_elevated_features
from src.report_helpers import format_investigation_brief
from src.report_helpers import analyze_monthly_consistency

def test_group_elevated_features_groups_known_features():
    elevated = [
        {"feature": "log_total_claim_lines", "provider_value": 5.0, "population_p99": 4.0},
        {"feature": "log_total_payment", "provider_value": 8.0, "population_p99": 7.0},
        {"feature": "active_months", "provider_value": 36.0, "population_p99": 30.0},
    ]

    result = group_elevated_features(elevated)

    assert "Utilization and volume" in result
    assert "Payments" in result
    assert "Duration" in result
    assert len(result["Utilization and volume"]) == 1


def test_group_elevated_features_returns_empty_dict_for_no_elevated_features():
    assert group_elevated_features([]) == {}


def test_group_elevated_features_ignores_unknown_features():
    elevated = [
        {"feature": "unknown_feature", "provider_value": 100, "population_p99": 50}
    ]

    assert group_elevated_features(elevated) == {}


def test_group_elevated_features_groups_multiple_features_together():
    elevated = [
        {"feature": "log_total_claim_lines", "provider_value": 5.0, "population_p99": 4.0},
        {"feature": "log_unique_claims", "provider_value": 6.0, "population_p99": 5.0},
    ]

    result = group_elevated_features(elevated)

    assert len(result["Utilization and volume"]) == 2


def test_group_elevated_features_handles_empty_feature_list():
    elevated = [
        {"feature": "unknown_feature", "provider_value": 5.0, "population_p99": 4.0},
    ]

    result = group_elevated_features(elevated)

    assert result == {}


def make_test_report(anomaly_score=0.1234, elevated_features=None):
    if elevated_features is None:
        elevated_features = []

    return {
        "provider_npi": "1234567890",
        "screening": {
            "anomaly_prediction": -1,
            "anomaly_score": anomaly_score,
            "interpretation": (
                "Flagged by the Isolation Forest for further review."
            ),
        },
        "population_context": {
            "features_above_p99": elevated_features,
        },
        "activity_summary": {
            "months_observed": 12,
            "total_claim_lines": 1200,
            "total_payment": 25000.00,
        },
        "monthly_trend_analysis": {
            "average_monthly_payment": 2083.33,
            "average_monthly_claim_lines": 100.0,
            "highest_payment_month": {
                "claim_month": "2020-06",
                "monthly_payment": 4000.00,
            },
            "highest_claim_month": {
                "claim_month": "2020-06",
                "monthly_claim_lines": 150,
            },
            "largest_payment_increase": {
                "payment_change": 1000.00,
                "payment_pct_change": 0.25,
                "from_month": "2020-05",
                "to_month": "2020-06",
            },
            "largest_payment_decrease": {
                "payment_change": -500.00,
                "payment_pct_change": -0.10,
                "from_month": "2020-06",
                "to_month": "2020-07",
            },
        },
        "hcpcs_summary": {
            "top_codes_by_payment": [
                {
                    "hcpcs_code": "99213",
                    "claim_lines": 100,
                    "total_payment": 5000.00,
                    "payment_share": 0.20,
                },
            ],
            "top_codes_payment_share": 0.20,
        },
        "limitations": [
            "An anomaly flag is not evidence of fraud.",
        ],
    }


def test_format_investigation_brief_includes_expected_sections():
    report = make_test_report()

    brief = format_investigation_brief(report)

    assert "# Provider Investigation Brief" in brief
    assert "**Provider NPI:** 1234567890" in brief
    assert "## 1. Screening" in brief
    assert "## 5. HCPCS Activity" in brief
    assert "## 7. Suggested Follow-up" in brief
    assert "An anomaly flag is not evidence of fraud." in brief
    assert "Anomaly score: 0.1234" in brief


def test_format_investigation_brief_handles_no_elevated_features():
    report = make_test_report(elevated_features=[])

    brief = format_investigation_brief(report)

    assert "No features above the population p99 were reported." in brief


def test_format_investigation_brief_handles_missing_anomaly_score():
    report = make_test_report(anomaly_score=None)

    brief = format_investigation_brief(report)

    assert "Anomaly score: Unavailable" in brief


def test_monthly_consistency_calculates_summary():
    state = {
        "monthly_activity": [
            {"claim_month": "2020-01", "monthly_claim_lines": 10, "monthly_payment": 100.0},
            {"claim_month": "2020-02", "monthly_claim_lines": 20, "monthly_payment": 200.0},
            {"claim_month": "2020-03", "monthly_claim_lines": 30, "monthly_payment": 300.0},
        ]
    }

    result = analyze_monthly_consistency(state)

    assert result["months_observed"] == 3
    assert result["total_claim_lines"] == 60
    assert result["average_monthly_claim_lines"] == 20
    assert result["above_average_months"] == 1
    assert result["total_monthly_payment"] == 600
    assert result["top_five_claim_share"] == 1.0


def test_monthly_consistency_handles_empty_activity():
    result = analyze_monthly_consistency({"monthly_activity": []})

    assert result["months_observed"] == 0
    assert result["average_monthly_claim_lines"] == 0.0
    assert result["top_five_claim_share"] == 0.0
    assert result["top_five_months"] == []


def test_monthly_consistency_handles_zero_claims():
    state = {
        "monthly_activity": [
            {"claim_month": "2020-01", "monthly_claim_lines": 0, "monthly_payment": 0.0},
            {"claim_month": "2020-02", "monthly_claim_lines": 0, "monthly_payment": 0.0},
        ]
    }

    result = analyze_monthly_consistency(state)

    assert result["total_claim_lines"] == 0
    assert result["top_five_claim_share"] == 0.0

#checks expected date range
import pandas as pd
def test_monthly_activity_covers_expected_period():
    expected_months = pd.date_range(
        start="2008-01-01",
        end="2010-12-01",
        freq="MS"
    )

    # Confirm the expected monthly range has 36 months.
    assert len(expected_months) == 36
    assert expected_months[0] == pd.Timestamp("2008-01-01")
    assert expected_months[-1] == pd.Timestamp("2010-12-01")



