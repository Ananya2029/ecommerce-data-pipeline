"""Paths and pipeline settings."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = ROOT / "sql"
# PIPELINE_DATA_DIR lets tests/CI run the same pipeline on the small sample in data/sample
RAW_DIR = Path(os.environ.get("PIPELINE_DATA_DIR", ROOT / "data" / "raw"))
WAREHOUSE = Path(os.environ.get("PIPELINE_WAREHOUSE", ROOT / "warehouse" / "olist.duckdb"))
# PIPELINE_OUTPUT_DIR keeps test/CI outputs away from the real reports and exports
_OUTPUT = Path(os.environ.get("PIPELINE_OUTPUT_DIR", ROOT))
REPORT_DIR = _OUTPUT / "reports"
EXPORT_DIR = _OUTPUT / "exports"

RAW_TABLES = {
    "customers": "olist_customers_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}

# Months with a complete order history (the dataset tails off after Aug 2018)
ANALYSIS_START, ANALYSIS_END = "2017-01-01", "2018-08-31"
