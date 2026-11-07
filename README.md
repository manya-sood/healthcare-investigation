# Healthcare Provider Investigation

An AI-assisted healthcare fraud investigation system that combines anomaly detection, population benchmarking, longitudinal claims analysis, and agentic evidence gathering to help prioritize providers for further review.

## Overview

Healthcare claims data can contain complex activity patterns that are difficult to assess using a single metric. This project brings multiple analytical signals together into a structured investigation workflow.

Users enter a provider's NPI and receive an investigation report containing anomaly screening results, population comparisons, monthly activity trends, procedure-level payment analysis, and investigation limitations.

**The system supports investigation prioritization; it does not determine whether fraud occurred.**

## Features

- **Anomaly Detection:** Uses an Isolation Forest model to flag unusual provider activity for further review.
- **Population Benchmarking:** Compares provider-level features against the reference population's 99th percentile.
- **Longitudinal Analysis:** Examines monthly claim volume and payments over time.
- **Procedure-Level Analysis:** Summarizes HCPCS codes by claim lines, total payments, payment share, and claim-line share.
- **Agentic Investigation Workflow:** Uses LangGraph to coordinate evidence collection, trend analysis, consistency analysis, and report generation.
- **Interactive Dashboard:** Presents investigation findings and key metrics through a Streamlit interface.
- **REST API:** Uses FastAPI to expose investigation functionality through an HTTP endpoint.
- **Containerized Execution:** Uses Docker and Docker Compose to run the frontend and backend as separate services.
- **Responsible Interpretation:** Includes analytical limitations to distinguish statistical anomalies from evidence of fraud.

## Architecture

### Investigation Workflow

flowchart TD
    A["CMS Claims Data"] --> B["Data Preparation & Feature Engineering"]
    B --> C["Provider-Level Features & Processed Data"]
    C --> D["Isolation Forest Anomaly Screening"]
    D --> E["LangGraph Investigation Workflow"]

    E --> F["Population Benchmarking"]
    E --> G["Monthly Trend Analysis"]
    E --> H["Activity Consistency Analysis"]
    E --> I["HCPCS Procedure Analysis"]

    F --> J["Structured Investigation Report"]
    G --> J
    H --> J
    I --> J


### Application Architecture

flowchart TD
    A["User"] --> B["Streamlit Frontend"]
    B -->|"HTTP Requests"| C["FastAPI Backend"]
    C --> D["LangGraph Investigation Workflow"]
    D --> E["PySpark Analytics & ML"]
    E --> F[("Processed Parquet Data")]

    D -->|"Investigation Results"| C
    C -->|"JSON Response"| B
    B -->|"Displays Report & Visualizations"| A

The application is containerized using Docker Compose, with the Streamlit frontend and FastAPI backend running in separate containers and communicating over an internal Docker network.

## Technology Stack

- **Python** — application logic and data analysis
- **Apache Spark / PySpark** — claims processing and feature engineering
- **pandas** — tabular data preparation and dashboard presentation
- **scikit-learn** — Isolation Forest anomaly detection
- **LangGraph** — investigation workflow orchestration
- **FastAPI** — backend REST API
- **Streamlit** — interactive user interface
- **Docker & Docker Compose** — containerization and multi-service orchestration
- **DuckDB** — analytical data querying

## Getting Started

### Prerequisites

- Docker Desktop or Docker Engine with Docker Compose
- Git

### Data Requirements

This project uses the CMS DE-SynPUF synthetic Medicare claims dataset.

The application requires the processed Parquet datasets to be available under `data/processed/` before building the Docker images.

Raw claims data and generated datasets are not included in this repository. The processed datasets must be generated through the data preparation workflow before running the application.

### Run with Docker Compose

1. Clone the repository:


git clone <repository-url>
cd healthcare-investigation

2. Ensure the required processed datasets are available under `data/processed/`.

3. Build the Docker images:


docker compose build

4. Start the application:


docker compose up


5. Open the Streamlit dashboard:

http://localhost:8501


Enter a provider NPI to run an investigation.

The FastAPI backend is available at:

http://localhost:8000


To stop the application, press `Ctrl+C` and run:

docker compose down


## Data

This project uses the CMS DE-SynPUF synthetic Medicare claims dataset.

The data is synthetic and intended for research and demonstration. Results from this project should not be interpreted as findings about actual provider misconduct.

The application operates on processed claims datasets generated during data preparation.

## Limitations

- An anomaly detection flag indicates unusual activity relative to the model; it is not proof of fraud.
- Population percentile comparisons are descriptive and do not establish causation.
- Log-transformed features must be interpreted on their transformed scale.
- The synthetic dataset does not represent verified real-world fraud cases.
- Findings are intended to support human review, not replace expert judgment.

## Future Improvements

- Expanded automated testing and validation.
- Improved deployment and reproducibility documentation.
- Additional analytical signals and investigation capabilities.
- Production deployment and monitoring.