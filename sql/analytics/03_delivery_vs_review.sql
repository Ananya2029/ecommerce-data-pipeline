-- Does delivery performance drive customer satisfaction?
-- Compares actual delivery time with the delivery date promised to the customer.
SELECT CASE WHEN delivery_days - promised_days <= -10 THEN '1. 10+ days early'
            WHEN delivery_days - promised_days <= 0   THEN '2. on time'
            WHEN delivery_days - promised_days <= 5   THEN '3. 1-5 days late'
            WHEN delivery_days - promised_days <= 15  THEN '4. 6-15 days late'
            ELSE                                           '5. 15+ days late' END AS delivery_vs_promise,
       count(*)                                      AS orders,
       round(avg(review_score), 2)                   AS avg_review,
       round(100 * avg((review_score <= 2)::INT), 1) AS pct_negative_reviews
FROM gold.fact_orders
WHERE order_status = 'delivered' AND delivery_days IS NOT NULL AND review_score IS NOT NULL
GROUP BY 1
ORDER BY 1;
