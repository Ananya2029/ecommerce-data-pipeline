-- Monthly acquisition cohorts: what share of new customers buy again within 6 months?
WITH orders AS (
    SELECT customer_key, purchased_at::DATE AS d
    FROM gold.fact_orders
    WHERE order_status NOT IN ('canceled', 'unavailable')
),
firsts AS (
    SELECT customer_key, min(d) AS first_order FROM orders GROUP BY 1
),
cohort AS (
    SELECT strftime(f.first_order, '%Y-%m') AS cohort_month,
           f.customer_key,
           max((o.d > f.first_order AND o.d <= f.first_order + INTERVAL 6 MONTH)::INT) AS returned_6m
    FROM firsts f JOIN orders o USING (customer_key)
    GROUP BY 1, 2
)
SELECT cohort_month,
       count(*)                         AS new_customers,
       sum(returned_6m)                 AS returned_within_6m,
       round(100 * avg(returned_6m), 2) AS retention_6m_pct
FROM cohort
WHERE cohort_month BETWEEN '2017-01' AND '2018-02'   -- cohorts with a full 6 months to observe
GROUP BY 1
ORDER BY 1;
