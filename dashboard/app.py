"""
E-commerce analytics dashboard on the gold star schema.

    streamlit run dashboard/app.py
"""
import json
import sys
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline.config import ANALYSIS_END, ANALYSIS_START, REPORT_DIR, WAREHOUSE  # noqa: E402

st.set_page_config(page_title="Olist E-commerce Analytics", page_icon="🛒", layout="wide")


@st.cache_data
def q(sql):
    with duckdb.connect(str(WAREHOUSE), read_only=True) as con:
        return con.sql(sql).df()


def analytics(name):
    return pd.read_csv(REPORT_DIR / "analytics" / f"{name}.csv")


st.title("🛒 Olist E-commerce Analytics")
st.caption(f"Gold star schema built by the pipeline · complete months {ANALYSIS_START[:7]} to {ANALYSIS_END[:7]}")

kpi = q("""
    SELECT count(*) AS orders, sum(payment_value) AS revenue,
           count(DISTINCT customer_key) AS customers,
           avg(review_score) AS review, avg(is_late::INT) AS late
    FROM gold.fact_orders WHERE order_status = 'delivered'""").iloc[0]
repeat = q("""SELECT avg((n > 1)::INT) AS r FROM (SELECT customer_key, count(*) n FROM gold.fact_orders
              WHERE order_status NOT IN ('canceled','unavailable') GROUP BY 1)""").iloc[0]["r"]
c = st.columns(6)
c[0].metric("Delivered orders", f"{kpi.orders:,.0f}")
c[1].metric("Revenue", f"R$ {kpi.revenue / 1e6:.1f} M")
c[2].metric("Customers", f"{kpi.customers:,.0f}")
c[3].metric("Avg review", f"{kpi.review:.2f} ★")
c[4].metric("Late deliveries", f"{kpi.late:.1%}")
c[5].metric("Repeat customers", f"{repeat:.1%}")

tab_sales, tab_delivery, tab_customers, tab_quality = st.tabs(
    ["📈 Sales", "🚚 Delivery & satisfaction", "👥 Customers", "✅ Data quality"])

with tab_sales:
    m = analytics("01_monthly_revenue")
    st.plotly_chart(px.bar(m, x="year_month", y="revenue", title="Monthly revenue (R$)",
                           hover_data=["orders", "avg_order_value", "revenue_growth_pct"]), width="stretch")
    left, right = st.columns(2)
    cat = analytics("02_category_performance").head(10)
    left.plotly_chart(px.bar(cat.iloc[::-1], x="revenue", y="category", orientation="h",
                             title="Top 10 categories by revenue", hover_data=["avg_review", "late_pct"]),
                      width="stretch")
    pay = analytics("08_payment_mix")
    right.plotly_chart(px.pie(pay, names="payment_type", values="orders", title="Payment methods (orders)"),
                       width="stretch")
    s = analytics("07_seller_concentration")
    st.info(f"**Seller concentration:** the top 10% of sellers generate {s.iloc[0]['revenue_pct']:.0f}% of revenue.")

with tab_delivery:
    d = analytics("03_delivery_vs_review")
    left, right = st.columns(2)
    left.plotly_chart(px.bar(d, x="delivery_vs_promise", y="avg_review", title="Average review vs delivery promise",
                             range_y=[1, 5], text="avg_review"), width="stretch")
    right.plotly_chart(px.bar(d, x="delivery_vs_promise", y="pct_negative_reviews",
                              title="% negative reviews (1-2 ★)", text="pct_negative_reviews"), width="stretch")
    st.plotly_chart(px.bar(analytics("06_state_delivery"), x="state", y="avg_delivery_days", color="late_pct",
                           title="Average delivery time by customer state", color_continuous_scale="Reds"),
                    width="stretch")

with tab_customers:
    rfm = analytics("05_rfm_segments")
    left, right = st.columns(2)
    left.plotly_chart(px.bar(rfm, x="segment", y=["customers_pct", "revenue_pct"], barmode="group",
                             title="RFM segments: share of customers vs share of revenue"), width="stretch")
    ret = analytics("04_customer_retention")
    right.plotly_chart(px.line(ret, x="cohort_month", y="retention_6m_pct", markers=True,
                               title="6-month repeat-purchase rate by first-order cohort (%)"), width="stretch")
    geo = q("""SELECT c.state, avg(c.lat) lat, avg(c.lng) lng, count(*) orders, avg(o.review_score) review
               FROM gold.fact_orders o JOIN gold.dim_customer c USING (customer_key)
               WHERE c.lat IS NOT NULL GROUP BY 1""")
    fig = px.scatter_geo(geo, lat="lat", lon="lng", size="orders", color="review", hover_name="state",
                         scope="south america", title="Orders by customer state (colour = avg review)",
                         color_continuous_scale="RdYlGn")
    st.plotly_chart(fig, width="stretch")

with tab_quality:
    dq = pd.DataFrame(json.loads((REPORT_DIR / "data_quality.json").read_text()))
    ok = int(dq["passed"].sum())
    st.subheader(f"{ok} of {len(dq)} checks passed · {int((~dq['passed'] & (dq['severity'] == 'warn')).sum())} warnings")
    st.dataframe(dq, hide_index=True, width="stretch")
    st.subheader("Quarantined records")
    st.dataframe(q("SELECT source_table, reason, count(*) AS records FROM silver.quarantine GROUP BY ALL"),
                 hide_index=True)
