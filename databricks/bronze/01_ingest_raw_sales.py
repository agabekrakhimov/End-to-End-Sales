# Delta Live Tables — Bronze Layer: Raw Sales Ingestion
import dlt
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, IntegerType, TimestampType
)

RAW_PATH = "dbfs:/mnt/sales-datalake/raw/transactions/"

SALES_SCHEMA = StructType([
    StructField("order_id",       StringType(),    False),
    StructField("customer_id",    StringType(),    False),
    StructField("product_id",     StringType(),    False),
    StructField("region",         StringType(),    True),
    StructField("sales_rep_id",   StringType(),    True),
    StructField("order_date",     StringType(),    True),
    StructField("quantity",       IntegerType(),   True),
    StructField("unit_price",     DoubleType(),    True),
    StructField("discount_pct",   DoubleType(),    True),
    StructField("channel",        StringType(),    True),
    StructField("product_category", StringType(), True),
])


@dlt.table(
    name="bronze_sales_transactions",
    comment="Raw sales transactions landed from source CSV/JSON files.",
    table_properties={"quality": "bronze"},
)
def bronze_sales_transactions():
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "csv")
        .option("cloudFiles.schemaLocation", "dbfs:/mnt/sales-datalake/schema/sales")
        .option("header", "true")
        .schema(SALES_SCHEMA)
        .load(RAW_PATH)
        .withColumn("_ingested_at", F.current_timestamp())
        .withColumn("_source_file", F.input_file_name())
    )


@dlt.table(
    name="bronze_customers",
    comment="Raw customer master data.",
    table_properties={"quality": "bronze"},
)
def bronze_customers():
    return (
        spark.read
        .format("csv")
        .option("header", "true")
        .option("inferSchema", "true")
        .load("dbfs:/mnt/sales-datalake/raw/customers/customers.csv")
        .withColumn("_ingested_at", F.current_timestamp())
    )


@dlt.table(
    name="bronze_products",
    comment="Raw product catalog.",
    table_properties={"quality": "bronze"},
)
def bronze_products():
    return (
        spark.read
        .format("csv")
        .option("header", "true")
        .option("inferSchema", "true")
        .load("dbfs:/mnt/sales-datalake/raw/products/products.csv")
        .withColumn("_ingested_at", F.current_timestamp())
    )
