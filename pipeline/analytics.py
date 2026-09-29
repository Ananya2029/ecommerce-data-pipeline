"""Run the business-question SQL in sql/analytics, save results as CSV and draw charts."""
import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from pipeline.config import ANALYSIS_END, ANALYSIS_START, REPORT_DIR, SQL_DIR, WAREHOUSE  # noqa: E402

OUT = REPORT_DIR / "analytics"


def run_query(con, path):
    sql = path.read_text(encoding="utf-8").replace("{start}", ANALYSIS_START).replace("{end}", ANALYSIS_END)
    return con.sql(sql).df()


def charts(r):
    fig, ax = plt.subplots(2, 2, figsize=(14, 9))

    m = r["01_monthly_revenue"]
    ax[0, 0].bar(m["year_month"], m["revenue"] / 1e6, color="tab:blue")
    ax[0, 0].set(title="Monthly revenue (R$ millions)")
    ax[0, 0].tick_params(axis="x", rotation=90)

    d = r["03_delivery_vs_review"]
    ax[0, 1].bar(d["delivery_vs_promise"].str[3:], d["avg_review"],
                 color=["tab:green", "tab:green", "tab:orange", "tab:red", "tab:red"])
    ax[0, 1].set(title="Average review score vs delivery promise", ylim=(1, 5))
    for i, v in enumerate(d["avg_review"]):
        ax[0, 1].text(i, v + 0.05, f"{v:.2f}", ha="center")

    c = r["02_category_performance"].head(10).iloc[::-1]
    ax[1, 0].barh(c["category"], c["revenue"] / 1e6, color="tab:purple")
    ax[1, 0].set(title="Top 10 categories by revenue (R$ millions)")

    s = r["07_seller_concentration"]
    ax[1, 1].plot(s["seller_decile"] * 10, s["cumulative_pct"], marker="o")
    ax[1, 1].set(title="Seller revenue concentration", xlabel="Top % of sellers",
                 ylabel="Cumulative % of revenue", ylim=(0, 105))
    ax[1, 1].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(REPORT_DIR / "business_insights.png", dpi=120)


def run_analytics():
    OUT.mkdir(parents=True, exist_ok=True)
    results = {}
    with duckdb.connect(str(WAREHOUSE), read_only=True) as con:
        for path in sorted((SQL_DIR / "analytics").glob("*.sql")):
            df = run_query(con, path)
            df.to_csv(OUT / f"{path.stem}.csv", index=False)
            results[path.stem] = df
            print(f"  analytics: {path.stem} ({len(df)} rows)")
    charts(results)
    return results


if __name__ == "__main__":
    run_analytics()
