
#preserves feature grouping, adds report formatter, safe handling of missing/invalid anomaly score

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
        "Duration": ["active_months"],
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


def format_investigation_brief(report):
    provider = report["provider_npi"]
    screening = report["screening"]
    population = report["population_context"]
    activity = report["activity_summary"]
    trends = report["monthly_trend_analysis"]
    hcpcs = report["hcpcs_summary"]
    limitations = report["limitations"]

    lines = [
        "# Provider Investigation Brief",
        f"\n**Provider NPI:** {provider}",
        "\n## 1. Screening",
        screening.get(
            "interpretation",
            "No interpretation available."
        ),
    ]

    score = screening.get("anomaly_score")
    if score is None:
        score_text = "Unavailable"
    else:
        try:
            score_text = f"{float(score):.4f}"
        except (TypeError, ValueError):
            score_text = "Unavailable"

    lines.append(
        f"\n- Anomaly prediction: "
        f"{screening.get('anomaly_prediction')}"
        f"\n- Anomaly score: {score_text}"
    )

    lines.append("\n## 2. Population Context")
    elevated = population.get("features_above_p99", [])
    grouped = group_elevated_features(elevated)

    if grouped:
        lines.append(
            f"{len(elevated)} features exceeded their population "
            "99th-percentile reference values, across these categories:"
        )

        for group_name, features in grouped.items():
            lines.append(f"\n### {group_name}")

            for item in features:
                lines.append(
                    f"- **{item['feature']}**: "
                    f"provider = {item['provider_value']:.3f}; "
                    f"population p99 = {item['population_p99']:.3f}"
                )
    else:
        lines.append(
            "No features above the population p99 were reported."
        )

    lines.append("\n## 3. Activity Summary")
    lines.append(
        f"- Months observed: {activity['months_observed']}"
    )
    lines.append(
        f"- Total claim lines: {activity['total_claim_lines']:,}"
    )
    lines.append(
        f"- Total payments: ${activity['total_payment']:,.2f}"
    )

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
        f"- Highest payment month: {high_payment['claim_month']} "
        f"(${high_payment['monthly_payment']:,.2f})"
    )
    lines.append(
        f"- Highest claim-volume month: {high_claims['claim_month']} "
        f"({high_claims['monthly_claim_lines']:,} claim lines)"
    )
    lines.append(
        f"- Largest payment increase: ${increase['payment_change']:,.2f} "
        f"({increase['payment_pct_change']:.1%}) "
        f"from {increase['from_month']} to {increase['to_month']}"
    )
    lines.append(
        f"- Largest payment decrease: ${decrease['payment_change']:,.2f} "
        f"({decrease['payment_pct_change']:.1%}) "
        f"from {decrease['from_month']} to {decrease['to_month']}"
    )

    lines.append("\n## 5. HCPCS Activity")
    share = hcpcs.get("top_codes_payment_share")
    if share is None:
        share_text = "Unavailable"
    else:
        share_text = f"{share:.1%}"

    lines.append(
        f"The ten listed codes account for {share_text} of total payments."
    )
    lines.append(
        "\n| HCPCS | Claim lines | Payment | Payment share |"
    )
    lines.append("|---|---:|---:|---:|")

    for item in hcpcs.get("top_codes_by_payment", []):
        lines.append(
            f"| {item['hcpcs_code']} "
            f"| {item['claim_lines']:,} "
            f"| ${item['total_payment']:,.2f} "
            f"| {item['payment_share']:.1%} |"
        )

    lines.append("\n## 6. Limitations")
    for limitation in limitations:
        lines.append(f"- {limitation}")

    lines.append(
        "\n## 7. Suggested Follow-up\n"
        "Review the elevated utilization and payment measures in context, "
        "including provider specialty, peer-group composition, and the "
        "underlying claims. Examine the months with the largest payment "
        "changes and assess whether the procedure mix helps explain them. "
        "The screening results alone do not establish fraud."
    )

    return "\n".join(lines)

#keeps original calculation, but handles empty inputs/no claim lines:

def analyze_monthly_consistency(state):
    monthly = state["monthly_activity"]

    if not monthly:
        return {
            "above_average_months": 0,
            "months_observed": 0,
            "top_five_months": [],
            "top_five_claim_share": 0.0,
            "total_claim_lines": 0,
            "average_monthly_claim_lines": 0.0,
            "total_monthly_payment": 0,
        }

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
        reverse=True,
    )[:5]

    top_five_claims = sum(
        row["monthly_claim_lines"] for row in busiest_months
    )

    top_five_share = (
        top_five_claims / total_claims
        if total_claims > 0
        else 0.0
    )

    return {
        "above_average_months": above_average_months,
        "months_observed": len(monthly),
        "top_five_months": busiest_months,
        "top_five_claim_share": top_five_share,
        "total_claim_lines": total_claims,
        "average_monthly_claim_lines": avg_claims,
        "total_monthly_payment": total_payment,
    }
