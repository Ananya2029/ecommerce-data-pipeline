-- Top product categories by revenue, their share of the total and customer rating.
WITH cat AS (
    SELECT p.category,
           sum(f.price)         AS revenue,
           count(*)             AS items_sold,
           avg(f.review_score)  AS avg_review,
           avg(f.is_late::INT)  AS late_rate
    FROM gold.fact_sales f JOIN gold.dim_product p USING (product_key)
    WHERE f.order_status = 'delivered'
    GROUP BY 1
)
SELECT rank() OVER (ORDER BY revenue DESC)           AS rank,
       category,
       round(revenue, 0)                              AS revenue,
       round(100 * revenue / sum(revenue) OVER (), 1) AS revenue_share_pct,
       round(100 * sum(revenue) OVER (ORDER BY revenue DESC) / sum(revenue) OVER (), 1) AS cumulative_share_pct,
       items_sold,
       round(avg_review, 2)                           AS avg_review,
       round(100 * late_rate, 1)                      AS late_pct
FROM cat
ORDER BY rank
LIMIT 20;
