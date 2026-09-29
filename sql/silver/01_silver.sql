-- ===================================================================
-- SILVER: typed, cleaned, de-duplicated tables. Rows that break hard
-- rules go to silver.quarantine with the reason, instead of silently
-- disappearing.
-- ===================================================================
CREATE SCHEMA IF NOT EXISTS silver;

CREATE OR REPLACE TABLE silver.quarantine (
    source_table VARCHAR, record_id VARCHAR, reason VARCHAR, quarantined_at TIMESTAMP
);

-- ---------- orders ----------
INSERT INTO silver.quarantine
SELECT 'orders', order_id, 'status delivered but no delivery date', now()
FROM bronze.orders
WHERE order_status = 'delivered' AND order_delivered_customer_date IS NULL;

CREATE OR REPLACE TABLE silver.orders AS
SELECT
    order_id,
    customer_id,
    lower(trim(order_status))                        AS order_status,
    order_purchase_timestamp                          AS purchased_at,
    order_approved_at                                 AS approved_at,
    order_delivered_carrier_date                      AS shipped_at,
    order_delivered_customer_date                     AS delivered_at,
    order_estimated_delivery_date                     AS estimated_delivery_at,
    date_diff('day', order_purchase_timestamp, order_delivered_customer_date)    AS delivery_days,
    date_diff('day', order_purchase_timestamp, order_estimated_delivery_date)    AS promised_days,
    CASE WHEN order_delivered_customer_date IS NULL THEN NULL
         ELSE order_delivered_customer_date::DATE > order_estimated_delivery_date::DATE END AS is_late
FROM bronze.orders
WHERE order_id NOT IN (SELECT record_id FROM silver.quarantine WHERE source_table = 'orders');

-- ---------- order items ----------
CREATE OR REPLACE TABLE silver.order_items AS
SELECT order_id, order_item_id, product_id, seller_id,
       shipping_limit_date AS shipping_limit_at,
       price::DECIMAL(10, 2)         AS price,
       freight_value::DECIMAL(10, 2) AS freight_value
FROM bronze.order_items
WHERE order_id IN (SELECT order_id FROM silver.orders);

-- ---------- payments ----------
INSERT INTO silver.quarantine
SELECT 'order_payments', order_id || '#' || payment_sequential, 'unknown payment type (not_defined)', now()
FROM bronze.order_payments WHERE payment_type = 'not_defined';

CREATE OR REPLACE TABLE silver.payments AS
SELECT order_id, payment_sequential, payment_type, payment_installments,
       payment_value::DECIMAL(10, 2) AS payment_value
FROM bronze.order_payments
WHERE payment_type <> 'not_defined'
  AND order_id IN (SELECT order_id FROM silver.orders);

-- ---------- reviews: keep one review per order (the most recent answer) ----------
CREATE OR REPLACE TABLE silver.reviews AS
SELECT order_id, review_id, review_score, review_comment_title, review_comment_message,
       review_creation_date AS reviewed_at, review_answer_timestamp AS answered_at
FROM bronze.order_reviews
WHERE order_id IN (SELECT order_id FROM silver.orders)
QUALIFY row_number() OVER (PARTITION BY order_id ORDER BY review_answer_timestamp DESC, review_id) = 1;

-- ---------- products: English category, fix column name typos ----------
CREATE OR REPLACE TABLE silver.products AS
SELECT
    p.product_id,
    coalesce(t.product_category_name_english,
             CASE p.product_category_name
                  WHEN 'pc_gamer' THEN 'pc_gamer'
                  WHEN 'portateis_cozinha_e_preparadores_de_alimentos' THEN 'portable_kitchen_food_preparers'
             END,
             'unknown')                        AS category,
    p.product_name_lenght                      AS name_length,
    p.product_description_lenght               AS description_length,
    p.product_photos_qty                       AS photos_qty,
    p.product_weight_g                         AS weight_g,
    p.product_length_cm * p.product_height_cm * p.product_width_cm AS volume_cm3
FROM bronze.products p
LEFT JOIN bronze.category_translation t USING (product_category_name);

-- ---------- geolocation: one clean point per zip prefix ----------
-- ~53 raw rows per zip; median is robust to the few mis-geocoded points.
CREATE OR REPLACE TABLE silver.geolocation AS
SELECT geolocation_zip_code_prefix AS zip_prefix,
       median(geolocation_lat) AS lat,
       median(geolocation_lng) AS lng
FROM bronze.geolocation
WHERE geolocation_lat BETWEEN -34 AND 6          -- inside Brazil's bounding box
  AND geolocation_lng BETWEEN -74 AND -34
GROUP BY 1;

-- ---------- customers & sellers: normalised city names ----------
CREATE OR REPLACE TABLE silver.customers AS
SELECT customer_id, customer_unique_id, customer_zip_code_prefix AS zip_prefix,
       strip_accents(lower(trim(customer_city))) AS city, upper(customer_state) AS state
FROM bronze.customers;

CREATE OR REPLACE TABLE silver.sellers AS
SELECT seller_id, seller_zip_code_prefix AS zip_prefix,
       strip_accents(lower(trim(seller_city))) AS city, upper(seller_state) AS state
FROM bronze.sellers;
