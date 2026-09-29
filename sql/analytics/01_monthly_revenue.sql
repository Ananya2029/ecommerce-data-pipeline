-- Monthly revenue, orders and average order value, with month-over-month growth.
-- Revenue = items + freight of orders that were not canceled or unavailable.
WITH monthly AS (
    SELECT d.year_month,
           count(DISTINCT f.order_id) AS orders,
           sum(f.item_total)          AS revenue
    FROM gold.fact_sales f
    JOIN gold.dim_date d ON f.purchase_date_key = d.date_key
    WHERE f.order_status NOT IN ('canceled', 'unavailable')
      AND d.date BETWEEN DATE '{start}' AND DATE '{end}'
    GROUP BY 1
)
SELECT year_month, orders,
       round(revenue, 0)          AS revenue,
       round(revenue / orders, 2) AS avg_order_value,
       round(100 * (revenue / lag(revenue) OVER (ORDER BY year_month) - 1), 1) AS revenue_growth_pct
FROM monthly
ORDER BY year_month;
