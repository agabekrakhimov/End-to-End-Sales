# Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                                 │
│  CRM (Salesforce)  ·  ERP (SAP)  ·  CSV Uploads  ·  Marketing APIs │
└────────────────────────────┬────────────────────────────────────────┘
                             │  Auto Loader / REST
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  DATABRICKS DELTA LAKE  (ADLS Gen2)                 │
│                                                                     │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐   │
│  │   BRONZE     │──▶│   SILVER     │──▶│        GOLD          │   │
│  │  Raw ingest  │   │  Cleansed &  │   │  Business aggregates │   │
│  │  Delta Live  │   │  validated   │   │  monthly_revenue     │   │
│  │  Tables      │   │  DLT expect  │   │  product_performance │   │
│  └──────────────┘   └──────────────┘   │  sales_rep_leader-   │   │
│                                        │  board · customer_ltv│   │
│                                        │  revenue_anomalies   │   │
│                                        └──────────────────────┘   │
│                                                                     │
│  Databricks Jobs (scheduled)  ─────────────────────────────────┐  │
│                                                                  │  │
└──────────────────────────────────────────────────────────────────┼─┘
                                                                   │
          ┌────────────────────────┐       ┌────────────────┐      │
          │  Python Automation     │◀──────│  ML Anomaly    │◀─────┘
          │  email_alerts.py       │       │  Detector      │
          │  SMTP / HTML emails    │       │  IsolationForest│
          └────────────────────────┘       └────────────────┘
                                                    │
                             ┌──────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         POWER BI                                    │
│                                                                     │
│  DirectQuery ──▶ Databricks SQL Warehouse                           │
│                                                                     │
│  Dashboards:                                                        │
│  • Executive Revenue Overview (YoY, running totals, targets)        │
│  • Product Performance (top/bottom SKUs, category mix)              │
│  • Sales Rep Leaderboard (rank, leakage, discount behaviour)        │
│  • Customer LTV & RFM Segmentation                                  │
│  • Anomaly Monitor (flagged days, z-scores)                         │
│                                                                     │
│  Security: Row-level security per sales rep / manager role          │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow Timing

| Stage | Trigger | SLA |
|---|---|---|
| Bronze ingest | Every 15 min (Auto Loader) | < 20 min end-to-end |
| Silver clean | After bronze completes | < 5 min |
| Gold aggregate | After silver completes | < 10 min |
| Anomaly detect | Daily at 07:00 UTC | < 5 min |
| Email alerts | After anomaly detect | Immediate |
| Power BI refresh | Every 30 min (DirectQuery live) | Real-time |
