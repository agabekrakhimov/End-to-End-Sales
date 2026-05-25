# Sales & Marketing Analytics Platform — Databricks + Power BI

> **End-to-end analytics solution that reduced monthly reporting time from 3 days to 2 hours**
> — replacing fragile Excel workbooks with a fully automated, self-refreshing data product.

---

## Problem Statement

The sales team was spending **3 days every month** manually consolidating CSV exports from
Salesforce, SAP, and marketing platforms into a single Excel report — a process riddled with
human error, version conflicts, and zero real-time visibility.

This project replaced that workflow with a production-grade Delta Lake pipeline, automated
anomaly detection, and an interactive Power BI dashboard suite accessible to leadership
within **2 hours of month-end close** (and refreshed every 30 minutes intra-month).

---

## Tech Stack

| Layer | Technology |
|---|---|
| Ingestion | **Databricks Auto Loader** + Delta Live Tables |
| Storage | **Delta Lake** on Azure Data Lake Storage Gen2 |
| Transformation | **Spark SQL** + **PySpark** |
| Orchestration | **Databricks Jobs** (CRON scheduler) |
| ML / Anomaly | **Scikit-learn** — Isolation Forest + Z-score |
| Alerting | **Python** (smtplib) — HTML email reports |
| Visualisation | **Power BI** — DirectQuery + DAX + Row-level security |

---

## Key Achievements

- Processed **2.5M+ rows** of transactional data across 4 source systems
- Identified **$340K potential revenue leakage** from uncontrolled discount behaviour
- Built **5 interactive dashboard pages** used daily by executive leadership
- Anomaly detection catches revenue spikes/drops with **< 20-minute latency**
- Row-level security ensures each sales rep sees only their own data

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  DATA SOURCES: CRM · ERP · CSV Uploads · Marketing APIs         │
└────────────────────────┬─────────────────────────────────────────┘
                         │  Auto Loader / REST
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│              DATABRICKS DELTA LAKE (ADLS Gen2)                   │
│                                                                  │
│  BRONZE (raw) ──▶ SILVER (cleaned) ──▶ GOLD (aggregated)        │
│  Delta Live Tables with data quality expectations                │
│                                                                  │
│  Databricks Jobs scheduler ──▶ Python anomaly detection          │
└────────────────────────┬─────────────────────────────────────────┘
                         │  DirectQuery
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│              POWER BI  (5 dashboard pages)                       │
│  Executive Revenue · Product Perf · Rep Leaderboard              │
│  Customer LTV/RFM · Anomaly Monitor                              │
└──────────────────────────────────────────────────────────────────┘
```

See [`docs/architecture.md`](docs/architecture.md) for the full data-flow diagram
with SLA timings.

---

## Repository Structure

```
End-to-End-Sales/
│
├── databricks/
│   ├── bronze/
│   │   └── 01_ingest_raw_sales.py       # Auto Loader DLT — Bronze layer
│   ├── silver/
│   │   └── 02_clean_transform.py        # DLT expectations — Silver layer
│   └── gold/
│       └── 03_gold_aggregations.sql     # Business aggregates — Gold layer
│
├── python/
│   ├── anomaly_detection/
│   │   └── anomaly_detector.py          # Isolation Forest + Z-score detector
│   └── alerts/
│       └── email_alerts.py              # Automated HTML email alerts
│
├── powerbi/
│   └── dax_measures.md                  # All DAX measures documented
│
├── docs/
│   └── architecture.md                  # Architecture diagram + SLA table
│
├── data/sample/                         # Sample CSV schemas (no PII)
├── requirements.txt
└── README.md
```

---

## Pipeline Details

### Bronze — Raw Ingestion
[`databricks/bronze/01_ingest_raw_sales.py`](databricks/bronze/01_ingest_raw_sales.py)

Uses **Databricks Auto Loader** (`cloudFiles`) for schema-inference and incremental ingestion.
Three DLT tables: `bronze_sales_transactions`, `bronze_customers`, `bronze_products`.

### Silver — Cleanse & Validate
[`databricks/silver/02_clean_transform.py`](databricks/silver/02_clean_transform.py)

DLT `@expect_or_drop` constraints enforce data quality (null keys, positive quantities,
valid discount range). Adds derived columns: `gross_revenue`, `net_revenue`,
`revenue_leakage`, and date-part columns for Power BI slicing.

### Gold — Business Aggregates
[`databricks/gold/03_gold_aggregations.sql`](databricks/gold/03_gold_aggregations.sql)

Five Gold tables consumed directly by Power BI via DirectQuery:

| Table | Description |
|---|---|
| `monthly_revenue_summary` | Revenue, leakage, orders by month/region/channel |
| `product_performance` | Units, revenue, avg price by product/category/quarter |
| `sales_rep_leaderboard` | Per-rep revenue rank, discount behaviour |
| `customer_ltv` | Lifetime value + RFM segmentation (Champions/Loyal/At Risk/Lost) |
| `revenue_anomalies` | SQL-detected anomaly days (Z-score > 2 SD) |

### Anomaly Detection
[`python/anomaly_detection/anomaly_detector.py`](python/anomaly_detection/anomaly_detector.py)

Two-stage detection per region:
1. **Z-score** on 30-day rolling mean (threshold: ± 2.5 SD)
2. **Isolation Forest** (5% contamination, 200 estimators) for non-linear patterns

Results written to `gold.revenue_anomalies_ml` Delta table.

### Email Alerts
[`python/alerts/email_alerts.py`](python/alerts/email_alerts.py)

Databricks Job triggers after each anomaly run — sends HTML email reports to
configured recipients covering anomaly details and KPI threshold breaches
(monthly revenue < $500K, avg discount > 20%).

---

## Power BI Dashboards

| Page | Key Visuals |
|---|---|
| Executive Revenue Overview | YoY bar chart, running total, revenue vs target gauge |
| Product Performance | Top/bottom SKU table, category revenue treemap |
| Sales Rep Leaderboard | Rank table, discount heatmap, quota attainment |
| Customer LTV & RFM | Segment donut, LTV scatter, country map |
| Anomaly Monitor | Flagged-day timeline, Z-score bar, region filter |

DAX measures: see [`powerbi/dax_measures.md`](powerbi/dax_measures.md)

Row-level security restricts sales reps to their own records; managers see all.

---

## How to Run

### 1. Databricks Setup

```bash
# Clone this repo into your Databricks workspace
git clone https://github.com/agabekrakhimov/end-to-end-sales

# Upload notebooks to Databricks Repos (or import .py files directly)
```

1. Create a **Delta Live Tables pipeline** pointing to `databricks/bronze/` → `silver/` → `gold/`
2. Set the pipeline mode to **Triggered** (or **Continuous** for near-real-time)
3. Create a **Databricks Job** with three tasks chained in order:
   - Task 1: DLT pipeline
   - Task 2: `python/anomaly_detection/anomaly_detector.py`
   - Task 3: `python/alerts/email_alerts.py`

### 2. Python Environment (local dev/testing)

```bash
pip install -r requirements.txt
```

Set environment variables before running alerts locally:

```bash
export ALERT_EMAIL="you@example.com"
export ALERT_PASSWORD="app-password"
export ALERT_RECIPIENTS="leader1@company.com,leader2@company.com"
```

### 3. Power BI

1. Open `powerbi/SalesAnalytics.pbix` in Power BI Desktop
2. Update the **Databricks SQL Warehouse** connection string in
   `File → Options → Data source settings`
3. Publish to Power BI Service and configure **scheduled refresh** or leave as **DirectQuery**
4. Assign Row-level security roles in `Modeling → Manage roles`

---

## Links

| Resource | URL |
|---|---|
| Live Power BI Dashboard | *(add your published link)* |
| Databricks Workspace | *(add your workspace URL)* |
| Azure Data Lake | *(add your storage account)* |

---

## Results & Impact

```
Reporting time:    3 days  →  2 hours   (-94%)
Manual steps:      47      →  0         (fully automated)
Revenue leakage identified:  $340,000
Anomalies caught before escalation:  12 incidents in first quarter
Dashboard users:   Leadership + 3 regional sales teams (40+ users)
```
