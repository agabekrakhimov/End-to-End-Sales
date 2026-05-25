# Power BI DAX Measures

## Revenue Measures

```dax
-- Total Net Revenue
Net Revenue =
SUMX(
    gold_monthly_revenue_summary,
    gold_monthly_revenue_summary[net_revenue]
)

-- YoY Revenue Growth %
YoY Revenue Growth % =
VAR CurrentYear  = CALCULATE([Net Revenue], YEAR(TODAY()) = gold_monthly_revenue_summary[order_year])
VAR PreviousYear = CALCULATE([Net Revenue], YEAR(TODAY()) - 1 = gold_monthly_revenue_summary[order_year])
RETURN
    DIVIDE(CurrentYear - PreviousYear, PreviousYear, 0) * 100

-- Running Total Revenue
Revenue Running Total =
CALCULATE(
    [Net Revenue],
    FILTER(
        ALLSELECTED(gold_monthly_revenue_summary[order_month]),
        gold_monthly_revenue_summary[order_month] <= MAX(gold_monthly_revenue_summary[order_month])
    )
)

-- Revenue vs Target
Revenue vs Target % =
DIVIDE([Net Revenue], [Revenue Target], 0) * 100
```

## Discount & Leakage Measures

```dax
-- Total Revenue Leakage
Revenue Leakage =
SUM(gold_monthly_revenue_summary[revenue_leakage])

-- Leakage as % of Gross
Leakage % =
DIVIDE([Revenue Leakage], SUM(gold_monthly_revenue_summary[gross_revenue]), 0) * 100

-- Avg Discount %
Avg Discount % =
AVERAGE(gold_monthly_revenue_summary[avg_discount_pct])
```

## Customer Measures

```dax
-- Active Customers (purchased in last 90 days)
Active Customers =
CALCULATE(
    DISTINCTCOUNT(silver_sales_transactions[customer_id]),
    silver_sales_transactions[order_date] >= TODAY() - 90
)

-- Customer Acquisition Rate MoM
New Customers MoM =
VAR ThisMonth = CALCULATE(DISTINCTCOUNT(silver_sales_transactions[customer_id]),
    MONTH(silver_sales_transactions[order_date]) = MONTH(TODAY()))
VAR LastMonth = CALCULATE(DISTINCTCOUNT(silver_sales_transactions[customer_id]),
    MONTH(silver_sales_transactions[order_date]) = MONTH(TODAY()) - 1)
RETURN ThisMonth - LastMonth
```

## Row-Level Security

```dax
-- Filter table: restrict reps to their own data
[sales_rep_id] = USERPRINCIPALNAME()
    || LOOKUPVALUE(dim_roles[is_manager], dim_roles[email], USERPRINCIPALNAME()) = TRUE
```
