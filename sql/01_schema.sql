-- Star schema. One fact row represents month × region × company × product.
CREATE OR REPLACE TABLE dim_date AS SELECT * FROM source_dim_date;
CREATE OR REPLACE TABLE dim_region AS SELECT * FROM source_dim_region;
CREATE OR REPLACE TABLE dim_company AS SELECT * FROM source_dim_company;
CREATE OR REPLACE TABLE dim_product AS SELECT * FROM source_dim_product;
CREATE OR REPLACE TABLE fact_sales AS SELECT * FROM source_fact_sales;

CREATE INDEX IF NOT EXISTS idx_fact_grain
ON fact_sales (month_id, region_id, company_id, product_id);
