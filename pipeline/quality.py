"""
Data-quality checks, dbt-test style: each check is a SQL query returning the
offending rows. 'error' checks fail the pipeline; 'warn' checks are reported.
"""
from dataclasses import dataclass

ACCEPTED_STATUSES = ("delivered", "shipped", "canceled", "unavailable", "invoiced",
                     "processing", "created", "approved")


@dataclass
class Check:
    name: str
    layer: str
    severity: str  # "error" or "warn"
    sql: str       # returns failing rows


def unique(table, cols, layer, severity="error"):
    return Check(f"{table}: {cols} is unique", layer, severity,
                 f"SELECT {cols}, count(*) FROM {table} GROUP BY ALL HAVING count(*) > 1")


def not_null(table, col, layer, severity="error"):
    return Check(f"{table}.{col} is not null", layer, severity,
                 f"SELECT * FROM {table} WHERE {col} IS NULL")


def references(fact, key, dim, layer="gold"):
    return Check(f"{fact}.{key} exists in {dim}", layer, "error",
                 f"SELECT f.{key} FROM {fact} f ANTI JOIN {dim} d USING ({key})")


CHECKS = [
    # ---------------- silver: cleaned entities ----------------
    unique("silver.orders", "order_id", "silver"),
    unique("silver.order_items", "order_id, order_item_id", "silver"),
    unique("silver.reviews", "order_id", "silver"),
    unique("silver.products", "product_id", "silver"),
    not_null("silver.orders", "purchased_at", "silver"),
    not_null("silver.products", "category", "silver"),
    Check("order_status has an accepted value", "silver", "error",
          f"SELECT * FROM silver.orders WHERE order_status NOT IN {ACCEPTED_STATUSES}"),
    Check("item price is positive", "silver", "error",
          "SELECT * FROM silver.order_items WHERE price <= 0"),
    Check("review score is between 1 and 5", "silver", "error",
          "SELECT * FROM silver.reviews WHERE review_score NOT BETWEEN 1 AND 5"),
    Check("delivery is not before purchase", "silver", "error",
          "SELECT * FROM silver.orders WHERE delivered_at < purchased_at"),
    Check("delivered orders have a delivery date", "silver", "error",
          "SELECT * FROM silver.orders WHERE order_status = 'delivered' AND delivered_at IS NULL"),
    Check("geolocation points are inside Brazil", "silver", "error",
          "SELECT * FROM silver.geolocation WHERE lat NOT BETWEEN -34 AND 6 OR lng NOT BETWEEN -74 AND -34"),
    Check("customer zip has a known location", "silver", "warn",
          "SELECT DISTINCT zip_prefix FROM silver.customers ANTI JOIN silver.geolocation USING (zip_prefix)"),
    # ---------------- gold: star schema integrity ----------------
    unique("gold.dim_customer", "customer_key", "gold"),
    unique("gold.dim_customer", "customer_unique_id", "gold"),
    unique("gold.dim_product", "product_key", "gold"),
    unique("gold.dim_seller", "seller_key", "gold"),
    unique("gold.dim_date", "date_key", "gold"),
    unique("gold.fact_sales", "order_id, order_item_id", "gold"),
    unique("gold.fact_orders", "order_id", "gold"),
    references("gold.fact_sales", "customer_key", "gold.dim_customer"),
    references("gold.fact_sales", "seller_key", "gold.dim_seller"),
    references("gold.fact_sales", "product_key", "gold.dim_product"),
    Check("fact_sales.purchase_date_key exists in gold.dim_date", "gold", "error",
          "SELECT purchase_date_key FROM gold.fact_sales ANTI JOIN gold.dim_date d ON purchase_date_key = d.date_key"),
    # ---------------- reconciliation: nothing lost or duplicated between layers ----------------
    Check("every clean order reaches fact_orders", "reconciliation", "error",
          "SELECT order_id FROM silver.orders ANTI JOIN gold.fact_orders USING (order_id)"),
    Check("item revenue reconciles silver -> gold", "reconciliation", "error",
          "SELECT s, g FROM (SELECT sum(price) s FROM silver.order_items), (SELECT sum(price) g FROM gold.fact_sales) WHERE s <> g"),
    Check("bronze orders = silver orders + quarantined", "reconciliation", "error",
          """SELECT b, s, q FROM (SELECT count(*) b FROM bronze.orders), (SELECT count(*) s FROM silver.orders),
             (SELECT count(*) q FROM silver.quarantine WHERE source_table = 'orders') WHERE b <> s + q"""),
    Check("payment total matches items + freight (within 1 BRL)", "reconciliation", "warn",
          """SELECT order_id FROM gold.fact_orders WHERE items > 0 AND payment_value IS NOT NULL
             AND abs(payment_value - (items_value + freight_value)) > 1"""),
]


def run_checks(con):
    results = []
    for c in CHECKS:
        failing = con.sql(f"SELECT count(*) FROM ({c.sql})").fetchone()[0]
        results.append({"check": c.name, "layer": c.layer, "severity": c.severity,
                        "failing_rows": int(failing), "passed": failing == 0})
    return results
