# Delta Live Tables — Silver Layer: Cleaned & Validated Data
import dlt
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, TimestampType

import dlt


@dlt.table(
    name="silver_sales_transactions",
    comment="Cleaned, validated, and enriched sales transactions.",
    table_properties={"quality": "silver"},
)
@dlt.expect_or_drop("valid_order_id",    "order_id IS NOT NULL")
@dlt.expect_or_drop("valid_customer_id", "customer_id IS NOT NULL")
@dlt.expect_or_drop("positive_quantity", "quantity > 0")
@dlt.expect_or_drop("positive_price",    "unit_price > 0")
@dlt.expect("discount_range",            "discount_pct BETWEEN 0 AND 1")
def silver_sales_transactions():
    return (
        dlt.read_stream("bronze_sales_transactions")
        .withColumn("order_date",    F.to_timestamp("order_date", "yyyy-MM-dd"))
        .withColumn("discount_pct",  F.col("discount_pct").cast(DoubleType()))
        .withColumn("gross_revenue", F.round(F.col("quantity") * F.col("unit_price"), 2))
        .withColumn(
            "net_revenue",
            F.round(F.col("gross_revenue") * (1 - F.col("discount_pct")), 2),
        )
        .withColumn("order_year",    F.year("order_date"))
        .withColumn("order_month",   F.month("order_date"))
        .withColumn("order_quarter", F.quarter("order_date"))
        .withColumn("order_week",    F.weekofyear("order_date"))
        .withColumn(
            "revenue_leakage",
            F.round(F.col("gross_revenue") - F.col("net_revenue"), 2),
        )
        .drop("_source_file")
    )


@dlt.table(
    name="silver_customers",
    comment="Deduplicated and standardised customer records.",
    table_properties={"quality": "silver"},
)
def silver_customers():
    return (
        dlt.read("bronze_customers")
        .dropDuplicates(["customer_id"])
        .withColumn("customer_segment", F.upper(F.trim(F.col("customer_segment"))))
        .withColumn("country",          F.upper(F.trim(F.col("country"))))
    )


@dlt.table(
    name="silver_products",
    comment="Deduplicated and enriched product catalogue.",
    table_properties={"quality": "silver"},
)
def silver_products():
    return (
        dlt.read("bronze_products")
        .dropDuplicates(["product_id"])
        .withColumn("category", F.upper(F.trim(F.col("category"))))
    )
