-- =============================================================
-- Gold Layer: Business-ready aggregated tables for Power BI
-- =============================================================

-- ----------------------------------------------------------------
-- 1. Monthly Revenue Summary
-- ----------------------------------------------------------------
CREATE OR REPLACE TABLE gold.monthly_revenue_summary
USING DELTA
COMMENT 'Monthly net revenue, gross revenue, and discount leakage by region and channel.'
AS
SELECT
    order_year,
    order_month,
    region,
    channel,
    COUNT(DISTINCT order_id)            AS total_orders,
    COUNT(DISTINCT customer_id)         AS unique_customers,
    ROUND(SUM(gross_revenue), 2)        AS gross_revenue,
    ROUND(SUM(net_revenue),   2)        AS net_revenue,
    ROUND(SUM(revenue_leakage), 2)      AS revenue_leakage,
    ROUND(AVG(discount_pct) * 100, 2)   AS avg_discount_pct
FROM silver.silver_sales_transactions
GROUP BY order_year, order_month, region, channel;


-- ----------------------------------------------------------------
-- 2. Product Performance
-- ----------------------------------------------------------------
CREATE OR REPLACE TABLE gold.product_performance
USING DELTA
COMMENT 'Revenue and volume metrics per product and category.'
AS
SELECT
    t.product_id,
    p.product_name,
    p.category,
    t.order_year,
    t.order_quarter,
    SUM(t.quantity)                     AS units_sold,
    ROUND(SUM(t.net_revenue), 2)        AS net_revenue,
    ROUND(SUM(t.revenue_leakage), 2)    AS revenue_leakage,
    ROUND(AVG(t.unit_price), 2)         AS avg_selling_price
FROM silver.silver_sales_transactions  t
JOIN silver.silver_products            p USING (product_id)
GROUP BY t.product_id, p.product_name, p.category, t.order_year, t.order_quarter;


-- ----------------------------------------------------------------
-- 3. Sales Rep Leaderboard
-- ----------------------------------------------------------------
CREATE OR REPLACE TABLE gold.sales_rep_leaderboard
USING DELTA
COMMENT 'Per-rep performance: revenue, order count, and discount behaviour.'
AS
SELECT
    sales_rep_id,
    order_year,
    order_quarter,
    COUNT(DISTINCT order_id)            AS orders_closed,
    ROUND(SUM(net_revenue), 2)          AS net_revenue,
    ROUND(SUM(revenue_leakage), 2)      AS discount_leakage,
    ROUND(AVG(discount_pct) * 100, 2)   AS avg_discount_pct,
    RANK() OVER (
        PARTITION BY order_year, order_quarter
        ORDER BY SUM(net_revenue) DESC
    )                                   AS revenue_rank
FROM silver.silver_sales_transactions
GROUP BY sales_rep_id, order_year, order_quarter;


-- ----------------------------------------------------------------
-- 4. Customer LTV & Segmentation
-- ----------------------------------------------------------------
CREATE OR REPLACE TABLE gold.customer_ltv
USING DELTA
COMMENT 'Lifetime value, purchase frequency, and RFM classification per customer.'
AS
WITH rfm AS (
    SELECT
        t.customer_id,
        c.customer_name,
        c.customer_segment,
        c.country,
        DATEDIFF(CURRENT_DATE(), MAX(t.order_date))  AS recency_days,
        COUNT(DISTINCT t.order_id)                   AS frequency,
        ROUND(SUM(t.net_revenue), 2)                 AS monetary_value
    FROM silver.silver_sales_transactions t
    JOIN silver.silver_customers          c USING (customer_id)
    GROUP BY t.customer_id, c.customer_name, c.customer_segment, c.country
)
SELECT
    *,
    CASE
        WHEN recency_days <= 30  AND frequency >= 5 THEN 'Champions'
        WHEN recency_days <= 90  AND frequency >= 3 THEN 'Loyal'
        WHEN recency_days <= 180                    THEN 'At Risk'
        ELSE 'Lost'
    END AS rfm_segment
FROM rfm;


-- ----------------------------------------------------------------
-- 5. Anomaly Flag Table (feed for Python alerts)
-- ----------------------------------------------------------------
CREATE OR REPLACE TABLE gold.revenue_anomalies
USING DELTA
COMMENT 'Days where net revenue deviated > 2 SD from the 30-day rolling mean.'
AS
WITH daily AS (
    SELECT
        order_date::DATE                AS sale_date,
        region,
        ROUND(SUM(net_revenue), 2)      AS daily_revenue
    FROM silver.silver_sales_transactions
    GROUP BY sale_date, region
),
stats AS (
    SELECT
        sale_date,
        region,
        daily_revenue,
        AVG(daily_revenue) OVER (
            PARTITION BY region
            ORDER BY sale_date
            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        )                               AS rolling_mean,
        STDDEV(daily_revenue) OVER (
            PARTITION BY region
            ORDER BY sale_date
            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        )                               AS rolling_std
    FROM daily
)
SELECT
    *,
    ROUND((daily_revenue - rolling_mean) / NULLIF(rolling_std, 0), 2) AS z_score,
    ABS(daily_revenue - rolling_mean) > (2 * rolling_std)             AS is_anomaly
FROM stats
WHERE is_anomaly = TRUE;
