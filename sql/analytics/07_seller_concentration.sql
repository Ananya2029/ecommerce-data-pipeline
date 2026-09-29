-- How concentrated is revenue among sellers? (Pareto analysis by seller decile)
WITH s AS (
    SELECT seller_key, sum(price) AS revenue
    FROM gold.fact_sales WHERE order_status = 'delivered' GROUP BY 1
),
ranked AS (
    SELECT revenue, ntile(10) OVER (ORDER BY revenue DESC) AS decile FROM s
)
SELECT decile                                                   AS seller_decile,
       count(*)                                                 AS sellers,
       round(sum(revenue), 0)                                   AS revenue,
       round(100 * sum(revenue) / sum(sum(revenue)) OVER (), 1) AS revenue_pct,
       round(100 * sum(sum(revenue)) OVER (ORDER BY decile) / sum(sum(revenue)) OVER (), 1) AS cumulative_pct
FROM ranked
GROUP BY 1
ORDER BY 1;
