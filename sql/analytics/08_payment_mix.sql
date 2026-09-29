-- Payment methods: share of orders and value, average order value and instalments.
SELECT payment_type,
       count(*)                                         AS orders,
       round(100 * count(*) / sum(count(*)) OVER (), 1) AS orders_pct,
       round(sum(payment_value), 0)                     AS value,
       round(avg(payment_value), 2)                     AS avg_order_value,
       round(avg(installments), 1)                      AS avg_installments
FROM gold.fact_orders
WHERE payment_type IS NOT NULL AND order_status NOT IN ('canceled', 'unavailable')
GROUP BY 1
ORDER BY orders DESC;
