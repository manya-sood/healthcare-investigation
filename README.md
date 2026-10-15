# Healthcare Provider Investigation

An AI-assisted healthcare fraud investigation system that combines anomaly detection, population benchmarking, longitudinal claims analysis, and agentic evidence gathering to help prioritize providers for further review.

## Overview

Healthcare claims data can contain complex activity patterns that are difficult to assess using a single metric. This project brings multiple analytical signals together into a structured investigation workflow.

Users enter a provider's NPI and receive an investigation report containing anomaly screening results, population comparisons, monthly activity trends, procedure-level payment analysis, and investigation limitations.

**The system supports investigation prioritization; it does not determine whether fraud occurred.**

## Features

* **Anomaly detection:** Uses an Isolation Forest model to flag unusual provider activity for further review.
* **Population benchmarking:** Compares provider-level features against the reference population's 99th percentile.
* **Longitudinal analysis:** Examines monthly claim volume and payments over time.
* **Procedure-level analysis:** Summarizes HCPCS codes by claim lines, total payments, payment share, and claim-line share.
* **Investigation workflow:** Uses LangGraph to cioordinate evidence collection, trend analysis, consistency analysis, and report generation.
* **Interactive dashboard:** Presents investigation findings and key metrics in a Streamlit interface.
* **Responsible interpretation:** Includes limitations to distinguish statistical anomalies from evidence of fraud.

## Architecture

Claims Data
    |
    v
Data Preparation & Feature Engineering
    |
    v
Provider-Level Features and Processed Data
    |
    v
Isolation Forest Anomaly Screening
    |
    v
LangGraph Investigation Workflow
    |
    +--> Population Benchmarking
    +--> Monthly Trend Analysis
    +--> Activity Consistency Analysis
    +--> HCPCS Procedure Analysis
    |
    v
Structured Investigation Report
    |
    v
Streamlit Dashboard


## Technology Stack

* **Python** — application logic and data analysis
* **Apache Spark / PySpark** — claims processing and feature engineering
* **pandas** — tabular data preparation and dashboard presentation
* **scikit-learn** — Isolation Forest anomaly detection
* **LangGraph** — investigation workflow orchestration
* **Streamlit** — interactive user interface

## Data

This project uses the CMS DE-SynPUF synthetic Medicare claims dataset.

The data is synthetic and is intended for research and demonstration. Results from this project should not be interpreted as findings about actual provider misconduct.

The application relies on processed datasets generated during data preparation. Raw claims data and generated datasets are not included in this repository.

## Limitations

* An anomaly detection flag indicates unusual activity relative to the model; it is not proof of fraud.
* Population percentile comparisons are descriptive and do not establish causation.
* Log-transformed features must be interpreted on their transformed scale.
* The synthetic dataset does not represent verified real-world fraud cases.
* Findings are intended to support human review, not replace expert judgment.

## Future Improvements

* Containerized execution with Docker
* Additional validation and automated tests
* Improved deployment and reproducibility documentation
