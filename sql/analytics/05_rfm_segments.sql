-- RFM segmentation: Recency, Frequency and Monetary value.
-- Recency and monetary are scored in quintiles with NTILE; frequency is scored directly
-- because ~97% of customers buy only once, so quintiles would be meaningless.
WITH snapshot AS (SELECT max(purchased_at)::DATE + 1 AS as_of FROM gold.fact_orders),
rfm AS (
    SELECT customer_key,
           date_diff('day', max(purchased_at)::DATE, (SELECT as_of FROM snapshot)) AS recency_days,
           count(*)           AS frequency,
           sum(payment_value) AS monetary
    FROM gold.fact_orders
    WHERE order_status NOT IN ('canceled', 'unavailable') AND payment_value IS NOT NULL
    GROUP BY 1
),
scored AS (
    SELECT *,
           ntile(5) OVER (ORDER BY recency_days DESC) AS r,   -- 5 = bought most recently
           CASE WHEN frequency >= 3 THEN 5 WHEN frequency = 2 THEN 4 ELSE 1 END AS f,
           ntile(5) OVER (ORDER BY monetary) AS m
    FROM rfm
)
SELECT CASE WHEN f >= 4 AND r >= 4   THEN '1. Loyal (repeat, recent)'
            WHEN f >= 4              THEN '2. Repeat, lapsing'
            WHEN r >= 4 AND m >= 4   THEN '3. New high spenders'
            WHEN r >= 4              THEN '4. New customers'
            WHEN m >= 4              THEN '5. High spenders at risk'
            ELSE                          '6. Low value, inactive' END AS segment,
       count(*)                                                 AS customers,
       round(100 * count(*) / sum(count(*)) OVER (), 1)         AS customers_pct,
       round(sum(monetary), 0)                                  AS revenue,
       round(100 * sum(monetary) / sum(sum(monetary)) OVER (), 1) AS revenue_pct,
       round(avg(recency_days), 0)                              AS avg_recency_days
FROM scored
GROUP BY 1
ORDER BY 1;
