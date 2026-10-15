# Healthcare Provider Investigation Backend

import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from typing import TypedDict
from langgraph.graph import StateGraph, START, END


#1) Load data
anomaly_results = pd.read_parquet(
    "data/processed/provider_anomaly_results.parquet"
)

spark = (
    SparkSession.builder
    .appName("HealthcareInvestigationAgents")
    .getOrCreate()
)

monthly_provider_activity = spark.read.parquet(
    "data/processed/monthly_provider_activity"
)

provider_hcpcs_summary = spark.read.parquet(
    "data/processed/provider_hcpcs_summary"
)


#2) Tool 1: provider profile

def get_provider_profile(provider_npi):
    provider = anomaly_results[
        anomaly_results["provider_npi"].astype(str).str.strip()
        == str(provider_npi).strip()
    ]

    if provider.empty:
        return {"error": f"Provider {provider_npi} not found"}

    row = provider.iloc[0]

    return {
        "provider_npi": str(row["provider_npi"]),
        "anomaly_prediction": int(row["anomaly_prediction"]),
        "anomaly_score": float(row["anomaly_score"]),
        "log_total_claim_lines": float(row["log_total_claim_lines"]),
        "log_unique_claims": float(row["log_unique_claims"]),
        "log_unique_beneficiaries": float(row["log_unique_beneficiaries"]),
        "log_unique_hcpcs": float(row["log_unique_hcpcs"]),
        "log_total_payment": float(row["log_total_payment"]),
        "avg_payment": float(row["avg_payment"]),
        "active_months": float(row["active_months"]),
        "log_avg_monthly_claim_lines": float(
            row["log_avg_monthly_claim_lines"]
        ),
        "log_max_monthly_claim_lines": float(
            row["log_max_monthly_claim_lines"]
        ),
        "log_avg_monthly_payment": float(
            row["log_avg_monthly_payment"]
        ),
        "std_monthly_claim_lines": float(
            row["std_monthly_claim_lines"]
        ),
        "std_monthly_payment": float(
            row["std_monthly_payment"]
        )
    }


#3) Tool 2 Monthly activity

def get_provider_monthly_activity(provider_npi):
    """
    Retrieve month-by-month claims activity for a provider.
    """

    try:
        provider_npi = int(provider_npi)
    except (TypeError, ValueError):
        return {"error": f"Invalid provider NPI: {provider_npi}"}

    monthly_df = (
        monthly_provider_activity
        .filter(F.col("provider_npi") == provider_npi)
        .orderBy("claim_month")
    )

    rows = monthly_df.collect()

    if not rows:
        return {
            "error": f"No monthly activity found for provider {provider_npi}"
        }

    return [row.asDict() for row in rows]


#4) Population comparison

comparison_features = [
    "log_total_claim_lines",
    "log_unique_claims",
    "log_unique_beneficiaries",
    "log_unique_hcpcs",
    "log_total_payment",
    "avg_payment",
    "active_months",
    "log_avg_monthly_claim_lines",
    "log_max_monthly_claim_lines",
    "log_avg_monthly_payment",
    "std_monthly_claim_lines",
    "std_monthly_payment"
]


population_reference = {}

for feature in comparison_features:
    population_reference[feature] = {
        "median": anomaly_results[feature].median(),
        "p90": anomaly_results[feature].quantile(0.90),
        "p95": anomaly_results[feature].quantile(0.95),
        "p99": anomaly_results[feature].quantile(0.99),
        "p999": anomaly_results[feature].quantile(0.999)
    }


def compare_provider_to_population(provider_npi):
    """
    Compare a provider's anomaly-detection features
    against the broader provider population.
    """

    try:
        provider_npi = int(provider_npi)
    except (TypeError, ValueError):
        return {"error": f"Invalid provider NPI: {provider_npi}"}

    provider_rows = anomaly_results[
        anomaly_results["provider_npi"] == provider_npi
    ]

    if provider_rows.empty:
        return {
            "error": f"No provider found for NPI {provider_npi}"
        }

    provider = provider_rows.iloc[0]

    comparisons = {}

    for feature in comparison_features:
        value = provider[feature]
        reference = population_reference[feature]

        comparisons[feature] = {
            "provider_value": float(value),
            "population_median": float(reference["median"]),
            "population_p90": float(reference["p90"]),
            "population_p95": float(reference["p95"]),
            "population_p99": float(reference["p99"]),
            "population_p999": float(reference["p999"])
        }

    return {
        "provider_npi": str(provider_npi),
        "comparisons": comparisons
    }



# 5) Tool 4: HCPCS activity

def get_provider_hcpcs_activity(provider_npi, top_n=10):
    """
    Retrieve the HCPCS/service codes driving a provider's activity.
    """

    try:
        provider_npi = int(provider_npi)
    except (TypeError, ValueError):
        return {"error": f"Invalid provider NPI: {provider_npi}"}

    provider_df = (
        provider_hcpcs_summary
        .filter(F.col("provider_npi") == provider_npi)
    )

    # Calculate provider-level totals
    totals = provider_df.agg(
        F.sum("claim_lines").alias("total_claim_lines"),
        F.sum("total_payment").alias("total_payment")
    ).collect()[0]

    total_claim_lines = totals["total_claim_lines"] or 0
    total_payment = totals["total_payment"] or 0

    if total_claim_lines == 0:
        return {
            "error": f"No HCPCS activity found for provider {provider_npi}"
        }

    # Get highest-payment HCPCS codes
    rows = (
        provider_df
        .orderBy(F.desc("total_payment"))
        .limit(top_n)
        .collect()
    )

    records = []

    for row in rows:
        record = row.asDict()

        record["payment_share"] = (
            record["total_payment"] / total_payment
            if total_payment > 0
            else 0
        )

        record["claim_line_share"] = (
            record["claim_lines"] / total_claim_lines
            if total_claim_lines > 0
            else 0
        )

        records.append(record)

    top_codes_payment = sum(
        record["total_payment"] or 0
        for record in records
    )

    return {
        "provider_npi": str(provider_npi),
        "total_claim_lines": total_claim_lines,
        "total_payment": total_payment,
        "top_hcpcs_count": len(records),
        "top_hcpcs_by_payment": records,
        "top_codes_payment": top_codes_payment,
        "top_codes_payment_share": (
            top_codes_payment / total_payment
            if total_payment > 0
            else 0
        )
    }


# 6) LangGraph state

class InvestigationState(TypedDict):
    provider_npi: str
    profile: dict
    monthly_activity: list
    population_comparison: dict
    hcpcs_activity: dict
    monthly_trends: dict
    monthly_consistency: dict
    report: dict


# 7) Evidence collection node
def collect_evidence(state: InvestigationState):
    npi = state["provider_npi"]

    return {
        "profile": get_provider_profile(npi),
        "monthly_activity": get_provider_monthly_activity(npi),
        "population_comparison": compare_provider_to_population(npi),
        "hcpcs_activity": get_provider_hcpcs_activity(npi)
    }


# 8) Monthly trend analysis
def analyze_monthly_trends(state: InvestigationState):
    monthly = state["monthly_activity"]

    if not monthly:
        return {
            "monthly_trends": {
                "error": "No monthly activity available"
            }
        }

    # Sort records chronologically
    monthly = sorted(
        monthly,
        key=lambda row: row["claim_month"]
    )

    # Find peak months
    highest_payment_month = max(
        monthly,
        key=lambda row: row["monthly_payment"] or 0
    )

    highest_claim_month = max(
        monthly,
        key=lambda row: row["monthly_claim_lines"] or 0
    )

    # Calculate month-over-month payment changes
    changes = []

    for i in range(1, len(monthly)):
        previous = monthly[i - 1]
        current = monthly[i]

        previous_payment = previous["monthly_payment"] or 0
        current_payment = current["monthly_payment"] or 0

        change = current_payment - previous_payment

        if previous_payment != 0:
            pct_change = change / previous_payment
        else:
            pct_change = None

        changes.append({
            "from_month": previous["claim_month"],
            "to_month": current["claim_month"],
            "payment_change": change,
            "payment_pct_change": pct_change
        })

    largest_increase = max(
        changes,
        key=lambda row: row["payment_change"]
    ) if changes else None

    largest_decrease = min(
        changes,
        key=lambda row: row["payment_change"]
    ) if changes else None

    total_payment = sum(
        row["monthly_payment"] or 0
        for row in monthly
    )

    total_claims = sum(
        row["monthly_claim_lines"] or 0
        for row in monthly
    )

    return {
        "monthly_trends": {
            "months_observed": len(monthly),
            "average_monthly_payment": total_payment / len(monthly),
            "average_monthly_claim_lines": total_claims / len(monthly),
            "highest_payment_month": highest_payment_month,
            "highest_claim_month": highest_claim_month,
            "largest_payment_increase": largest_increase,
            "largest_payment_decrease": largest_decrease
        }
    }


# 9) Monthly consistency analysis
def analyze_monthly_consistency(state):
    monthly = state["monthly_activity"]

    claim_values = [
        row["monthly_claim_lines"] for row in monthly
    ]

    payment_values = [
        row["monthly_payment"] for row in monthly
    ]

    avg_claims = sum(claim_values) / len(claim_values)
    total_claims = sum(claim_values)
    total_payment = sum(payment_values)

    above_average_months = sum(
        value > avg_claims for value in claim_values
    )

    busiest_months = sorted(
        monthly,
        key=lambda row: row["monthly_claim_lines"],
        reverse=True
    )[:5]

    top_five_claims = sum(
        row["monthly_claim_lines"] for row in busiest_months
    )

    top_five_share = top_five_claims / total_claims

    return {
        "above_average_months": above_average_months,
        "months_observed": len(monthly),
        "top_five_months": busiest_months,
        "top_five_claim_share": top_five_share,
        "total_claim_lines": total_claims,
        "average_monthly_claim_lines": avg_claims,
        "total_monthly_payment": total_payment,
    }


def analyze_consistency(state: InvestigationState):
    return {
        "monthly_consistency": analyze_monthly_consistency(state)
    }


# 10) Structured investigation report

def build_investigation_report(state: InvestigationState):
    profile = state["profile"]
    monthly = state["monthly_activity"]
    comparison = state["population_comparison"]
    hcpcs = state["hcpcs_activity"]
    trends = state["monthly_trends"]
    consistency = state["monthly_consistency"]

    # Identify features above the population's 99th percentile
    elevated_features = []

    for feature, values in comparison.get("comparisons", {}).items():
        provider_value = values.get("provider_value")
        p99 = values.get("population_p99")

        if provider_value is not None and p99 is not None:
            if provider_value > p99:
                elevated_features.append({
                    "feature": feature,
                    "provider_value": provider_value,
                    "population_p99": p99
                })

    return {
        "report": {
            "provider_npi": state["provider_npi"],

            "screening": {
                "anomaly_prediction": profile.get(
                    "anomaly_prediction"
                ),
                "anomaly_score": profile.get(
                    "anomaly_score"
                ),
                "interpretation": (
                    "Flagged by the Isolation Forest for further review."
                    if profile.get("anomaly_prediction") == -1
                    else "Not flagged by the Isolation Forest."
                )
            },

            "population_context": {
                "features_above_p99": elevated_features
            },

            "activity_summary": {
                "months_observed": len(monthly),
                "total_claim_lines": hcpcs.get(
                    "total_claim_lines"
                ),
                "total_payment": hcpcs.get(
                    "total_payment"
                )
            },

            "monthly_trend_analysis": trends,

            "hcpcs_summary": {
                "top_codes_by_payment": hcpcs.get(
                    "top_hcpcs_by_payment",
                    []
                ),
                "top_codes_payment_share": hcpcs.get(
                    "top_codes_payment_share"
                )
            },

            "monthly_consistency": consistency,

            "limitations": [
                "An anomaly flag is not evidence of fraud.",
                "Population comparisons are descriptive, not causal.",
                "Log-transformed features are reported in log space."
            ]
        }
    }


# 11) Group elevated features for investigator brief

def group_elevated_features(elevated):
    groups = {
        "Utilization and volume": [
            "log_total_claim_lines",
            "log_unique_claims",
            "log_unique_beneficiaries",
            "log_unique_hcpcs",
            "log_avg_monthly_claim_lines",
            "log_max_monthly_claim_lines",
        ],
        "Payments": [
            "log_total_payment",
            "log_avg_monthly_payment",
        ],
        "Duration": [
            "active_months",
        ],
        "Variability": [
            "std_monthly_claim_lines",
            "std_monthly_payment",
        ],
    }

    grouped = {}

    for group_name, feature_names in groups.items():
        matches = [
            item for item in elevated
            if item["feature"] in feature_names
        ]

        if matches:
            grouped[group_name] = matches

    return grouped


# 12) Investigator-facing report formatter

def format_investigation_brief(report):
    provider = report["provider_npi"]
    screening = report["screening"]
    population = report["population_context"]
    activity = report["activity_summary"]
    trends = report["monthly_trend_analysis"]
    hcpcs = report["hcpcs_summary"]
    limitations = report["limitations"]

    lines = []

    lines.append("# Provider Investigation Brief")
    lines.append(f"\n**Provider NPI:** {provider}")

    # Screening
    lines.append("\n## 1. Screening")

    lines.append(
        screening.get(
            "interpretation",
            "No interpretation available."
        )
    )

    lines.append(
        f"\n- Anomaly prediction: "
        f"{screening.get('anomaly_prediction')}"
        f"\n- Anomaly score: "
        f"{screening.get('anomaly_score'):.4f}"
    )

    # Population context
    lines.append("\n## 2. Population Context")

    elevated = population.get(
        "features_above_p99",
        []
    )

    grouped = group_elevated_features(elevated)

    if grouped:
        lines.append(
            f"{len(elevated)} features exceeded their population "
            "99th-percentile reference values, across these categories:"
        )

        for group_name, features in grouped.items():
            lines.append(
                f"\n### {group_name}"
            )

            for item in features:
                lines.append(
                    f"- **{item['feature']}**: "
                    f"provider = {item['provider_value']:.3f}; "
                    f"population p99 = "
                    f"{item['population_p99']:.3f}"
                )
    else:
        lines.append(
            "No features above the population p99 were reported."
        )

    # Activity
    lines.append("\n## 3. Activity Summary")

    lines.append(
        f"- Months observed: "
        f"{activity['months_observed']}"
    )

    lines.append(
        f"- Total claim lines: "
        f"{activity['total_claim_lines']:,}"
    )

    lines.append(
        f"- Total payments: "
        f"${activity['total_payment']:,.2f}"
    )

    # Trends
    lines.append("\n## 4. Monthly Trend Analysis")

    lines.append(
        f"- Average monthly payment: "
        f"${trends['average_monthly_payment']:,.2f}"
    )

    lines.append(
        f"- Average monthly claim lines: "
        f"{trends['average_monthly_claim_lines']:,.1f}"
    )

    high_payment = trends["highest_payment_month"]
    high_claims = trends["highest_claim_month"]
    increase = trends["largest_payment_increase"]
    decrease = trends["largest_payment_decrease"]

    lines.append(
        f"- Highest payment month: "
        f"{high_payment['claim_month']} "
        f"(${high_payment['monthly_payment']:,.2f})"
    )

    lines.append(
        f"- Highest claim-volume month: "
        f"{high_claims['claim_month']} "
        f"({high_claims['monthly_claim_lines']:,} claim lines)"
    )

    lines.append(
        f"- Largest payment increase: "
        f"${increase['payment_change']:,.2f} "
        f"({increase['payment_pct_change']:.1%}) "
        f"from {increase['from_month']} "
        f"to {increase['to_month']}"
    )

    lines.append(
        f"- Largest payment decrease: "
        f"${decrease['payment_change']:,.2f} "
        f"({decrease['payment_pct_change']:.1%}) "
        f"from {decrease['from_month']} "
        f"to {decrease['to_month']}"
    )

    # HCPCS
    lines.append("\n## 5. HCPCS Activity")

    lines.append(
        f"The ten listed codes account for "
        f"{hcpcs['top_codes_payment_share']:.1%} "
        "of total payments."
    )

    lines.append(
        "\n| HCPCS | Claim lines | Payment | Payment share |"
    )

    lines.append(
        "|---|---:|---:|---:|"
    )

    for item in hcpcs.get(
        "top_codes_by_payment",
        []
    ):
        lines.append(
            f"| {item['hcpcs_code']} "
            f"| {item['claim_lines']:,} "
            f"| ${item['total_payment']:,.2f} "
            f"| {item['payment_share']:.1%} |"
        )

    # Limitations
    lines.append("\n## 6. Limitations")

    for limitation in limitations:
        lines.append(
            f"- {limitation}"
        )

    lines.append(
        "\n## 7. Suggested Follow-up\n"
        "Review the elevated utilization and payment measures in context, "
        "including provider specialty, peer-group composition, and the "
        "underlying claims. Examine the months with the largest payment "
        "changes and assess whether the procedure mix helps explain them. "
        "The screening results alone do not establish fraud."
    )

    return "\n".join(lines)


# 13) Build LangGraph investigation workflow

graph_builder = StateGraph(InvestigationState)

graph_builder.add_node(
    "collect_evidence",
    collect_evidence
)

graph_builder.add_node(
    "analyze_trends",
    analyze_monthly_trends
)

graph_builder.add_node(
    "analyze_consistency",
    analyze_consistency
)

graph_builder.add_node(
    "build_report",
    build_investigation_report
)

graph_builder.add_edge(
    START,
    "collect_evidence"
)

graph_builder.add_edge(
    "collect_evidence",
    "analyze_trends"
)

graph_builder.add_edge(
    "analyze_trends",
    "analyze_consistency"
)

graph_builder.add_edge(
    "analyze_consistency",
    "build_report"
)

graph_builder.add_edge(
    "build_report",
    END
)

investigation_graph = graph_builder.compile()