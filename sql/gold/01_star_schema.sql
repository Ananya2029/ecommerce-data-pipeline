-- ===================================================================
-- GOLD: star schema for analytics and BI.
--   facts:      fact_sales (grain: one order item), fact_orders (grain: one order)
--   dimensions: dim_customer, dim_seller, dim_product, dim_date
-- ===================================================================
CREATE SCHEMA IF NOT EXISTS gold;

-- A "customer" is a person (customer_unique_id). Olist issues a new customer_id per
-- order, so keying on customer_id would make every buyer look like a new customer.
CREATE OR REPLACE TABLE gold.dim_customer AS
WITH people AS (
    SELECT customer_unique_id,
           any_value(zip_prefix ORDER BY customer_id) AS zip_prefix,
           any_value(city ORDER BY customer_id)       AS city,
           any_value(state ORDER BY customer_id)      AS state
    FROM silver.customers GROUP BY 1
)
SELECT row_number() OVER (ORDER BY customer_unique_id) AS customer_key,
       customer_unique_id, p.zip_prefix, city, state, g.lat, g.lng
FROM people p LEFT JOIN silver.geolocation g USING (zip_prefix);

CREATE OR REPLACE TABLE gold.dim_seller AS
SELECT row_number() OVER (ORDER BY seller_id) AS seller_key,
       seller_id, s.zip_prefix, city, state, g.lat, g.lng
FROM silver.sellers s LEFT JOIN silver.geolocation g USING (zip_prefix);

CREATE OR REPLACE TABLE gold.dim_product AS
SELECT row_number() OVER (ORDER BY product_id) AS product_key,
       product_id, category, photos_qty, weight_g, volume_cm3
FROM silver.products;

CREATE OR REPLACE TABLE gold.dim_date AS
SELECT CAST(strftime(d, '%Y%m%d') AS INTEGER) AS date_key,
       d::DATE AS date, year(d) AS year, quarter(d) AS quarter, month(d) AS month,
       strftime(d, '%b') AS month_name, strftime(d, '%Y-%m') AS year_month,
       dayofweek(d) AS day_of_week, strftime(d, '%a') AS day_name,
       dayofweek(d) IN (0, 6) AS is_weekend
FROM generate_series(TIMESTAMP '2016-01-01', TIMESTAMP '2018-12-31', INTERVAL 1 DAY) t(d);

-- Order-level measures, built once and reused by both facts
CREATE OR REPLACE TEMP TABLE order_measures AS
SELECT o.order_id,
       dc.customer_key,
       o.order_status, o.purchased_at, o.delivered_at, o.delivery_days, o.promised_days, o.is_late,
       r.review_score,
       p.payment_value, p.payment_type, p.installments
FROM silver.orders o
JOIN silver.customers c USING (customer_id)
JOIN gold.dim_customer dc USING (customer_unique_id)
LEFT JOIN silver.reviews r USING (order_id)
LEFT JOIN (
    SELECT order_id, sum(payment_value) AS payment_value,
           arg_max(payment_type, payment_value) AS payment_type,   -- main payment method
           max(payment_installments) AS installments
    FROM silver.payments GROUP BY 1
) p USING (order_id);

CREATE OR REPLACE TABLE gold.fact_sales AS
SELECT i.order_id, i.order_item_id,
       CAST(strftime(m.purchased_at, '%Y%m%d') AS INTEGER) AS purchase_date_key,
       m.customer_key, ds.seller_key, dp.product_key,
       i.price, i.freight_value, i.price + i.freight_value AS item_total,
       m.order_status, m.delivery_days, m.is_late, m.review_score, m.payment_type
FROM silver.order_items i
JOIN order_measures m USING (order_id)
JOIN gold.dim_seller ds USING (seller_id)
JOIN gold.dim_product dp USING (product_id);

CREATE OR REPLACE TABLE gold.fact_orders AS
SELECT m.order_id,
       CAST(strftime(m.purchased_at, '%Y%m%d') AS INTEGER) AS purchase_date_key,
       m.customer_key, m.order_status, m.purchased_at, m.delivered_at,
       coalesce(i.items, 0) AS items, coalesce(i.items_value, 0) AS items_value,
       coalesce(i.freight_value, 0) AS freight_value,
       m.payment_value, m.payment_type, m.installments,
       m.delivery_days, m.promised_days, m.is_late, m.review_score
FROM order_measures m
LEFT JOIN (SELECT order_id, count(*) AS items, sum(price) AS items_value, sum(freight_value) AS freight_value
           FROM silver.order_items GROUP BY 1) i USING (order_id);
