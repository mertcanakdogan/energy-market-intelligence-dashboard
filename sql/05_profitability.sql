CREATE OR REPLACE VIEW vw_northstar_profitability_monthly AS
SELECT
    d.date,
    r.region_name,
    p.product_segment,
    SUM(f.volume_mwh) AS volume_mwh,
    SUM(f.revenue) AS revenue,
    SUM(f.variable_cost) AS variable_cost,
    SUM(f.gross_profit) AS gross_profit,
    SUM(f.gross_profit) / NULLIF(SUM(f.revenue), 0) AS gross_margin_pct,
    SUM(f.gross_profit) / NULLIF(SUM(f.volume_mwh), 0) AS profit_per_mwh
FROM fact_sales AS f
JOIN dim_date AS d USING (month_id)
JOIN dim_region AS r USING (region_id)
JOIN dim_company AS c USING (company_id)
JOIN dim_product AS p USING (product_id)
WHERE c.company_name = 'Northstar Energy'
GROUP BY ALL;

CREATE OR REPLACE VIEW vw_profitability_summary AS
WITH boundaries AS (
    SELECT MAX(date) AS max_date FROM dim_date
)
SELECT
    region_name,
    product_segment,
    SUM(volume_mwh) AS volume_mwh,
    SUM(revenue) AS revenue,
    SUM(variable_cost) AS variable_cost,
    SUM(gross_profit) AS gross_profit,
    SUM(gross_profit) / NULLIF(SUM(revenue), 0) AS gross_margin_pct,
    SUM(gross_profit) / NULLIF(SUM(volume_mwh), 0) AS profit_per_mwh
FROM vw_northstar_profitability_monthly
CROSS JOIN boundaries
WHERE date > max_date - INTERVAL 12 MONTH
GROUP BY region_name, product_segment;

CREATE OR REPLACE VIEW vw_revenue_bridge AS
WITH boundaries AS (
    SELECT MAX(date) AS current_date, MAX(date) - INTERVAL 12 MONTH AS prior_date
    FROM dim_date
),
periods AS (
    SELECT
        r.region_name,
        p.product_segment,
        d.date,
        SUM(f.volume_mwh) AS volume_mwh,
        SUM(f.revenue) AS revenue,
        SUM(f.revenue) / NULLIF(SUM(f.volume_mwh), 0) AS average_price
    FROM fact_sales AS f
    JOIN dim_date AS d USING (month_id)
    JOIN dim_region AS r USING (region_id)
    JOIN dim_company AS c USING (company_id)
    JOIN dim_product AS p USING (product_id)
    CROSS JOIN boundaries AS b
    WHERE c.company_name = 'Northstar Energy'
      AND d.date IN (b.current_date, b.prior_date)
    GROUP BY ALL
),
pivoted AS (
    SELECT
        region_name,
        product_segment,
        MAX(volume_mwh) FILTER (WHERE date = b.prior_date) AS prior_volume,
        MAX(average_price) FILTER (WHERE date = b.prior_date) AS prior_price,
        MAX(revenue) FILTER (WHERE date = b.prior_date) AS prior_revenue,
        MAX(volume_mwh) FILTER (WHERE date = b.current_date) AS current_volume,
        MAX(average_price) FILTER (WHERE date = b.current_date) AS current_price,
        MAX(revenue) FILTER (WHERE date = b.current_date) AS current_revenue
    FROM periods
    CROSS JOIN boundaries AS b
    GROUP BY region_name, product_segment
)
SELECT
    *,
    (current_volume - prior_volume) * prior_price AS volume_effect,
    prior_volume * (current_price - prior_price) AS price_effect,
    (current_volume - prior_volume) * (current_price - prior_price) AS interaction_effect,
    current_revenue - prior_revenue AS total_revenue_change,
    (current_revenue - prior_revenue)
      - (
          (current_volume - prior_volume) * prior_price
          + prior_volume * (current_price - prior_price)
          + (current_volume - prior_volume) * (current_price - prior_price)
        ) AS reconciliation_gap
FROM pivoted;
