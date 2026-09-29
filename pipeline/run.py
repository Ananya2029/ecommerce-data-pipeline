"""
Run the whole pipeline: bronze -> silver -> gold -> data-quality checks -> analytics -> exports.

    python -m pipeline.run
    python -m pipeline.run --skip-analytics
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone

import duckdb

from pipeline.config import EXPORT_DIR, RAW_DIR, RAW_TABLES, REPORT_DIR, SQL_DIR, WAREHOUSE
from pipeline.quality import run_checks


def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def load_bronze(con):
    """Raw CSVs as-is, plus load metadata. No cleaning happens here."""
    con.sql("CREATE SCHEMA IF NOT EXISTS bronze")
    loaded_at = datetime.now(timezone.utc).isoformat()
    counts = {}
    for table, file in RAW_TABLES.items():
        path = (RAW_DIR / file).as_posix()
        con.sql(f"""CREATE OR REPLACE TABLE bronze.{table} AS
                    SELECT *, '{file}' AS _source_file, TIMESTAMP '{loaded_at[:19]}' AS _loaded_at
                    FROM read_csv('{path}', header = true, auto_detect = true)""")
        counts[table] = con.sql(f"SELECT count(*) FROM bronze.{table}").fetchone()[0]
    return counts


def run_sql_dir(con, layer):
    for f in sorted((SQL_DIR / layer).glob("*.sql")):
        con.execute(f.read_text(encoding="utf-8"))


def write_quality_report(results, counts):
    REPORT_DIR.mkdir(exist_ok=True)
    (REPORT_DIR / "data_quality.json").write_text(json.dumps(results, indent=2))
    icon = {True: "✅", False: None}
    lines = ["# Data-quality report", "",
             f"Run: {datetime.now():%Y-%m-%d %H:%M} · raw rows loaded: {sum(counts.values()):,}", "",
             "| Layer | Check | Severity | Failing rows | Result |", "|---|---|---|---|---|"]
    for r in results:
        result = icon[r["passed"]] or ("❌" if r["severity"] == "error" else "⚠️")
        lines.append(f"| {r['layer']} | {r['check']} | {r['severity']} | {r['failing_rows']:,} | {result} |")
    (REPORT_DIR / "data_quality.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def export_gold(con):
    """Parquet files for Power BI / Tableau (Get Data -> Parquet)."""
    EXPORT_DIR.mkdir(exist_ok=True)
    for (t,) in con.sql("SELECT table_name FROM information_schema.tables WHERE table_schema = 'gold'").fetchall():
        con.sql(f"COPY gold.{t} TO '{(EXPORT_DIR / t).as_posix()}.parquet' (FORMAT parquet)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-analytics", action="store_true")
    args = parser.parse_args()

    WAREHOUSE.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with duckdb.connect(str(WAREHOUSE)) as con:
        log("bronze: loading raw CSVs")
        counts = load_bronze(con)
        log(f"bronze: {sum(counts.values()):,} rows across {len(counts)} tables")
        log("silver: cleaning, de-duplicating, quarantining bad records")
        run_sql_dir(con, "silver")
        q = con.sql("SELECT source_table, reason, count(*) FROM silver.quarantine GROUP BY ALL").fetchall()
        for source, reason, n in q:
            log(f"  quarantined {n} {source}: {reason}")
        log("gold: building star schema")
        run_sql_dir(con, "gold")

        log("data quality: running checks")
        results = run_checks(con)
        write_quality_report(results, counts)
        errors = [r for r in results if not r["passed"] and r["severity"] == "error"]
        warns = [r for r in results if not r["passed"] and r["severity"] == "warn"]
        log(f"  {len(results) - len(errors) - len(warns)} passed, {len(warns)} warnings, {len(errors)} errors")
        for r in errors + warns:
            log(f"  {'ERROR' if r in errors else 'WARN '} {r['check']}: {r['failing_rows']:,} rows")
        if errors:
            log("pipeline stopped: data-quality errors (see reports/data_quality.md)")
            sys.exit(1)

        export_gold(con)
        log("exports: gold tables written to exports/*.parquet")

    if not args.skip_analytics:
        from pipeline.analytics import run_analytics
        run_analytics()
    log(f"done in {time.time() - t0:.0f}s -> {WAREHOUSE}")


if __name__ == "__main__":
    main()
