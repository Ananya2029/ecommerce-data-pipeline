# Data-quality report

Run: 2026-09-29 22:00 · raw rows loaded: 1,550,922

| Layer | Check | Severity | Failing rows | Result |
|---|---|---|---|---|
| silver | silver.orders: order_id is unique | error | 0 | ✅ |
| silver | silver.order_items: order_id, order_item_id is unique | error | 0 | ✅ |
| silver | silver.reviews: order_id is unique | error | 0 | ✅ |
| silver | silver.products: product_id is unique | error | 0 | ✅ |
| silver | silver.orders.purchased_at is not null | error | 0 | ✅ |
| silver | silver.products.category is not null | error | 0 | ✅ |
| silver | order_status has an accepted value | error | 0 | ✅ |
| silver | item price is positive | error | 0 | ✅ |
| silver | review score is between 1 and 5 | error | 0 | ✅ |
| silver | delivery is not before purchase | error | 0 | ✅ |
| silver | delivered orders have a delivery date | error | 0 | ✅ |
| silver | geolocation points are inside Brazil | error | 0 | ✅ |
| silver | customer zip has a known location | warn | 158 | ⚠️ |
| gold | gold.dim_customer: customer_key is unique | error | 0 | ✅ |
| gold | gold.dim_customer: customer_unique_id is unique | error | 0 | ✅ |
| gold | gold.dim_product: product_key is unique | error | 0 | ✅ |
| gold | gold.dim_seller: seller_key is unique | error | 0 | ✅ |
| gold | gold.dim_date: date_key is unique | error | 0 | ✅ |
| gold | gold.fact_sales: order_id, order_item_id is unique | error | 0 | ✅ |
| gold | gold.fact_orders: order_id is unique | error | 0 | ✅ |
| gold | gold.fact_sales.customer_key exists in gold.dim_customer | error | 0 | ✅ |
| gold | gold.fact_sales.seller_key exists in gold.dim_seller | error | 0 | ✅ |
| gold | gold.fact_sales.product_key exists in gold.dim_product | error | 0 | ✅ |
| gold | fact_sales.purchase_date_key exists in gold.dim_date | error | 0 | ✅ |
| reconciliation | every clean order reaches fact_orders | error | 0 | ✅ |
| reconciliation | item revenue reconciles silver -> gold | error | 0 | ✅ |
| reconciliation | bronze orders = silver orders + quarantined | error | 0 | ✅ |
| reconciliation | payment total matches items + freight (within 1 BRL) | warn | 249 | ⚠️ |
