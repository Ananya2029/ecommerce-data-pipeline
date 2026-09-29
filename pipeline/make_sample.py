"""
Build a small, referentially consistent sample of the raw data for tests and CI
(the full Kaggle download is ~120 MB and is not committed).

    python -m pipeline.make_sample
"""
import duckdb

from pipeline.config import RAW_DIR, RAW_TABLES, ROOT

SAMPLE_DIR = ROOT / "data" / "sample"
N_ORDERS = 3000


def main():
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    for t, f in RAW_TABLES.items():
        con.sql(f"CREATE VIEW {t} AS SELECT * FROM read_csv('{(RAW_DIR / f).as_posix()}', header=true, auto_detect=true)")
    # Keep a random set of orders, but always include the known problem records so the
    # quality rules and quarantine logic are exercised in tests.
    con.sql(f"""
        CREATE TABLE keep_orders AS
        SELECT order_id FROM (SELECT order_id FROM orders USING SAMPLE {N_ORDERS} ROWS (reservoir, 42))
        UNION SELECT order_id FROM orders WHERE order_status = 'delivered' AND order_delivered_customer_date IS NULL
        UNION SELECT order_id FROM order_payments WHERE payment_type = 'not_defined'
        UNION SELECT order_id FROM (SELECT order_id FROM order_reviews GROUP BY 1 HAVING count(*) > 1 LIMIT 20)
    """)
    queries = {
        "orders": "SELECT * FROM orders WHERE order_id IN (SELECT order_id FROM keep_orders)",
        "order_items": "SELECT * FROM order_items WHERE order_id IN (SELECT order_id FROM keep_orders)",
        "order_payments": "SELECT * FROM order_payments WHERE order_id IN (SELECT order_id FROM keep_orders)",
        "order_reviews": "SELECT * FROM order_reviews WHERE order_id IN (SELECT order_id FROM keep_orders)",
        "customers": "SELECT * FROM customers WHERE customer_id IN (SELECT customer_id FROM orders WHERE order_id IN (SELECT order_id FROM keep_orders))",
        "products": "SELECT * FROM products WHERE product_id IN (SELECT product_id FROM order_items WHERE order_id IN (SELECT order_id FROM keep_orders))",
        "sellers": "SELECT * FROM sellers WHERE seller_id IN (SELECT seller_id FROM order_items WHERE order_id IN (SELECT order_id FROM keep_orders))",
        "category_translation": "SELECT * FROM category_translation",
    }
    for t, q in queries.items():
        con.sql(f"COPY ({q}) TO '{(SAMPLE_DIR / RAW_TABLES[t]).as_posix()}' (HEADER, DELIMITER ',')")
    # Geolocation: only zips used by the sampled customers/sellers, max 5 points each
    con.sql(f"""COPY (
        SELECT * EXCLUDE (rn) FROM (
            SELECT *, row_number() OVER (PARTITION BY geolocation_zip_code_prefix) rn FROM geolocation
            WHERE geolocation_zip_code_prefix IN (
                SELECT customer_zip_code_prefix FROM read_csv('{(SAMPLE_DIR / RAW_TABLES["customers"]).as_posix()}')
                UNION SELECT seller_zip_code_prefix FROM read_csv('{(SAMPLE_DIR / RAW_TABLES["sellers"]).as_posix()}')))
        WHERE rn <= 5) TO '{(SAMPLE_DIR / RAW_TABLES["geolocation"]).as_posix()}' (HEADER, DELIMITER ',')""")
    for t, f in RAW_TABLES.items():
        n = duckdb.sql(f"SELECT count(*) FROM read_csv('{(SAMPLE_DIR / f).as_posix()}')").fetchone()[0]
        print(f"  {f}: {n:,} rows")


if __name__ == "__main__":
    main()
