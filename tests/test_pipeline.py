"""
End-to-end tests on the committed sample data (runs in a few seconds, no Kaggle download).

    python -m pytest -q
"""
import os
import subprocess
import sys
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def warehouse(tmp_path_factory):
    out = tmp_path_factory.mktemp("run")
    env = os.environ | {"PIPELINE_DATA_DIR": str(ROOT / "data" / "sample"),
                        "PIPELINE_WAREHOUSE": str(out / "test.duckdb"),
                        "PIPELINE_OUTPUT_DIR": str(out),
                        "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run([sys.executable, "-m", "pipeline.run"], cwd=ROOT, env=env,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    return out


@pytest.fixture
def con(warehouse):
    c = duckdb.connect(str(warehouse / "test.duckdb"))
    yield c
    c.close()


def test_all_error_checks_pass(con):
    from pipeline.quality import run_checks
    failed = [r for r in run_checks(con) if r["severity"] == "error" and not r["passed"]]
    assert failed == []


def test_bad_records_are_quarantined_not_dropped(con):
    reasons = dict(con.sql("SELECT reason, count(*) FROM silver.quarantine GROUP BY 1").fetchall())
    assert reasons["status delivered but no delivery date"] == 8
    assert reasons["unknown payment type (not_defined)"] == 3


def test_one_review_per_order_and_customer_is_a_person(con):
    assert con.sql("SELECT count(*) - count(DISTINCT order_id) FROM silver.reviews").fetchone()[0] == 0
    # dim_customer is keyed on the person (customer_unique_id), not the per-order customer_id
    people = con.sql("SELECT count(DISTINCT customer_unique_id) FROM silver.customers").fetchone()[0]
    assert con.sql("SELECT count(*) FROM gold.dim_customer").fetchone()[0] == people


def test_every_category_is_translated(con):
    assert con.sql("SELECT count(*) FROM gold.dim_product WHERE category IS NULL").fetchone()[0] == 0


@pytest.mark.parametrize("sabotage, expected_check", [
    ("INSERT INTO gold.fact_orders SELECT * FROM gold.fact_orders LIMIT 1", "gold.fact_orders: order_id is unique"),
    ("UPDATE silver.order_items SET price = -1 WHERE rowid = 0", "item price is positive"),
    ("DELETE FROM gold.dim_product WHERE product_key = (SELECT min(product_key) FROM gold.fact_sales)",
     "gold.fact_sales.product_key exists in gold.dim_product"),
])
def test_checks_catch_injected_errors(con, sabotage, expected_check):
    from pipeline.quality import run_checks
    con.sql("BEGIN")
    con.sql(sabotage)
    failed = {r["check"] for r in run_checks(con) if not r["passed"]}
    con.sql("ROLLBACK")
    assert expected_check in failed


def test_outputs_written(warehouse):
    assert (warehouse / "reports" / "data_quality.md").exists()
    assert (warehouse / "exports" / "fact_sales.parquet").exists()
    assert len(list((warehouse / "reports" / "analytics").glob("*.csv"))) == 8
