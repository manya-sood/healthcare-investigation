import streamlit as st
import pandas as pd
import investigation


st.set_page_config(
    page_title="Healthcare Provider Investigation",
    page_icon="🔎",
    layout="wide"
)


st.title("Healthcare Provider Investigation")

st.write(
    "Enter a provider NPI to run the investigation workflow."
)


provider_npi = st.text_input(
    "Provider NPI",
    value="9979265126"
)


if st.button("Run Investigation"):

    with st.spinner("Running investigation..."):

        result = investigation.investigation_graph.invoke({
            "provider_npi": provider_npi,
            "profile": {},
            "monthly_activity": [],
            "population_comparison": {},
            "hcpcs_activity": {},
            "monthly_trends": {},
            "monthly_consistency": {},
            "report": {}
        })

    report = result["report"]

    st.success("Investigation complete!")
    
    # Investigation Overview
    st.header("Investigation Overview")

    screening = report["screening"]
    activity = report["activity_summary"]
    elevated_features = report["population_context"]["features_above_p99"]

    if screening["anomaly_prediction"] == -1:
        st.warning(
            "Provider flagged for further review by the anomaly detection model. "
            "This is a screening signal, not evidence of fraud."
        )
    else:
        st.success(
            "Provider was not flagged by the anomaly detection model. "
            "This does not rule out potential issues."
        )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Anomaly Score",
            f"{screening['anomaly_score']:.4f}"
        )

    with col2:
        st.metric(
            "Months Observed",
            activity["months_observed"]
        )

    with col3:
        st.metric(
            "Total Claim Lines",
            f"{activity['total_claim_lines']:,}"
        )

    with col4:
        st.metric(
            "Features Above P99",
            len(elevated_features)
        )

    st.caption(
        "Automated screening and descriptive analytics support investigation "
        "prioritization; they do not determine whether fraud occurred."
    )

    st.divider()


    # 1. Screening
    st.header("Investigation Results")

    st.subheader("1. Screening")

    screening = report["screening"]

    if screening["anomaly_prediction"] == -1:
        st.warning("⚠️ Provider flagged for further review")
    else:
        st.success("Provider was not flagged by the anomaly model")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Anomaly Prediction",
            screening["anomaly_prediction"]
        )

    with col2:
        st.metric(
            "Anomaly Score",
            f"{screening['anomaly_score']:.4f}"
        )

    st.write(screening["interpretation"])

    # 2. Population Context
    st.subheader("2. Population Context")
    elevated_features = report["population_context"]["features_above_p99"]

    st.write(
        f"**{len(elevated_features)} features** were above "
        "the population 99th percentile."
    )

    if elevated_features:
        feature_labels = {
            "log_total_claim_lines": "Total claim lines",
            "log_unique_claims": "Unique claims",
            "log_unique_beneficiaries": "Unique beneficiaries",
            "log_unique_hcpcs": "Unique HCPCS codes",
            "log_total_payment": "Total payment",
            "active_months": "Active months",
            "log_avg_monthly_claim_lines": "Average monthly claim lines",
            "log_max_monthly_claim_lines": "Maximum monthly claim lines",
            "log_avg_monthly_payment": "Average monthly payment",
            "std_monthly_claim_lines": "Monthly claim-line variability",
            "std_monthly_payment": "Monthly payment variability",
        }

        population_rows = []

        for item in elevated_features:
            feature = item["feature"]
            is_log = feature.startswith("log_")

            population_rows.append({
                "Feature": feature_labels.get(
                    feature,
                    feature.replace("_", " ").title()
                ),
                "Scale": "Log-transformed" if is_log else "Original scale",
                "Provider value": f"{item['provider_value']:.3f}",
                "Population 99th percentile": (
                    f"{item['population_p99']:.3f}"
                ),
            })

        population_df = pd.DataFrame(population_rows)

        st.dataframe(
            population_df,
            use_container_width=True,
            hide_index=True
        )

        st.caption(
            "Log-transformed features are displayed in log space, "
            "not in their original units. Exceeding the 99th percentile "
            "indicates an unusual value relative to the reference "
            "population, not proof of fraud."
        )
    else:
        st.success(
            "No features exceeded the population 99th percentile."
        )

    # 3. Activity Summary

    st.subheader("3. Activity Summary")

    activity = report["activity_summary"]

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Months Observed",
            activity["months_observed"]
        )

    with col2:
        st.metric(
            "Total Claim Lines",
            f"{activity['total_claim_lines']:,}"
        )

    with col3:
        st.metric(
            "Total Payment",
            f"${activity['total_payment']:,.2f}"
        )

    # 4. Monthly Trend Analysis

    st.subheader("4. Monthly Trend Analysis")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Avg. Monthly Claim Lines",
            f"{report['monthly_trend_analysis']['average_monthly_claim_lines']:,.1f}"
        )

    with col2:
        st.metric(
            "Avg. Monthly Payment",
            f"${report['monthly_trend_analysis']['average_monthly_payment']:,.2f}"
        )

    # Prepare monthly data for charts
    monthly_df = pd.DataFrame(result["monthly_activity"])

    monthly_df["claim_month"] = pd.to_datetime(
        monthly_df["claim_month"]
    )

    monthly_df = monthly_df.sort_values("claim_month")

    st.write("### Claim Volume Over Time")

    claim_chart_df = monthly_df.set_index(
        "claim_month"
    )[["monthly_claim_lines"]]

    st.line_chart(claim_chart_df)

    st.write("### Payments Over Time")
    payment_chart_df = monthly_df.set_index("claim_month")[["monthly_payment"]]
    st.line_chart(
        payment_chart_df,
        x_label="Claim month",
        y_label="Total payment ($)"
    )


    # 5. HCPCS Activity
    st.subheader("5. HCPCS Activity")
    hcpcs = report["hcpcs_summary"]

    st.write(
        f"Top codes account for "
        f"{hcpcs['top_codes_payment_share']:.1%} "
        "of total payments."
    )

    hcpcs_rows = hcpcs.get("top_codes_by_payment", [])

    if hcpcs_rows:
        hcpcs_display_rows = []

        for item in hcpcs_rows:
            hcpcs_display_rows.append({
                "HCPCS Code": item.get("hcpcs_code", "Unknown"),
                "Claim Lines": item.get("claim_lines", 0),
                "Total Payment": item.get("total_payment", 0),
                "Payment Share": item.get("payment_share", 0),
                "Claim-Line Share": item.get("claim_line_share", 0),
            })

        hcpcs_df = pd.DataFrame(hcpcs_display_rows)

        hcpcs_df["Claim Lines"] = hcpcs_df["Claim Lines"].map(
            lambda value: f"{value:,}"
        )
        hcpcs_df["Total Payment"] = hcpcs_df["Total Payment"].map(
            lambda value: f"${value:,.2f}"
        )
        hcpcs_df["Payment Share"] = hcpcs_df["Payment Share"].map(
            lambda value: f"{value:.1%}"
        )
        hcpcs_df["Claim-Line Share"] = hcpcs_df["Claim-Line Share"].map(
            lambda value: f"{value:.1%}"
        )

        st.dataframe(
            hcpcs_df,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No HCPCS activity is available for this provider.")

    # 6. Monthly Consistency
    st.subheader("6. Monthly Consistency")
    consistency = report["monthly_consistency"]

    above_average = consistency["above_average_months"]
    months_observed = consistency["months_observed"]
    top_five_share = consistency["top_five_claim_share"]

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Months Above Average Volume",
            f"{above_average}/{months_observed}",
            help="Number of observed months with claim volume above the provider's average."
        )

    with col2:
        st.metric(
            "Claims From Top 5 Months",
            f"{top_five_share:.1%}",
            help="Share of all claim lines concentrated in the five busiest months."
        )

    if months_observed > 0:
        above_average_share = above_average / months_observed

        if above_average_share >= 0.75:
            st.write(
                "Claim volume was consistently above its average across "
                "most observed months."
            )
        elif above_average_share <= 0.25:
            st.write(
                "Claim volume was above its average in relatively few "
                "observed months."
            )
        else:
            st.write(
                "Claim volume fluctuated around its average across "
                "the observed period."
            )

    st.caption(
        "These metrics describe activity patterns and concentration; "
        "they do not establish fraud or explain the causes of observed patterns."
    )


    # 7. Limitations

    st.subheader("7. Limitations")

    for limitation in report["limitations"]:
        st.write(f"• {limitation}")