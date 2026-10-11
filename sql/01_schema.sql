-- Star schema. The market fact represents month × region × company × product.
-- The focus-company pricing fact represents month × region × product × customer segment.
CREATE OR REPLACE TABLE dim_date AS SELECT * FROM source_dim_date;
CREATE OR REPLACE TABLE dim_region AS SELECT * FROM source_dim_region;
CREATE OR REPLACE TABLE dim_company AS SELECT * FROM source_dim_company;
CREATE OR REPLACE TABLE dim_product AS SELECT * FROM source_dim_product;
CREATE OR REPLACE TABLE dim_customer_segment AS SELECT * FROM source_dim_customer_segment;
CREATE OR REPLACE TABLE dim_discount_policy AS SELECT * FROM source_dim_discount_policy;
CREATE OR REPLACE TABLE fact_sales AS SELECT * FROM source_fact_sales;
CREATE OR REPLACE TABLE fact_pricing AS SELECT * FROM source_fact_pricing;

CREATE INDEX IF NOT EXISTS idx_fact_grain
ON fact_sales (month_id, region_id, company_id, product_id);

CREATE INDEX IF NOT EXISTS idx_fact_pricing_grain
ON fact_pricing (month_id, region_id, product_id, customer_segment_id);
