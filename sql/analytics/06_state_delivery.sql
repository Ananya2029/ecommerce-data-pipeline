-- Delivery performance by customer state (states with at least 500 delivered orders).
SELECT c.state,
       count(*)                            AS delivered_orders,
       round(avg(o.delivery_days), 1)      AS avg_delivery_days,
       round(100 * avg(o.is_late::INT), 1) AS late_pct,
       round(avg(o.review_score), 2)       AS avg_review
FROM gold.fact_orders o JOIN gold.dim_customer c USING (customer_key)
WHERE o.order_status = 'delivered' AND o.delivery_days IS NOT NULL
GROUP BY 1
HAVING count(*) >= 500
ORDER BY avg_delivery_days DESC;
