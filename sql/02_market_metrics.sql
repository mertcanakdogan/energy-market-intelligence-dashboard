-- Fractional market shares are represented on a 0–1 scale throughout the SQL layer.
CREATE OR REPLACE VIEW vw_company_monthly AS
WITH company_totals AS (
    SELECT
        d.date,
        r.region_name,
        c.company_name,
        c.company_type,
        SUM(f.volume_mwh) AS company_volume_mwh,
        SUM(f.revenue) AS revenue,
        SUM(f.gross_profit) AS gross_profit
    FROM fact_sales AS f
    JOIN dim_date AS d USING (month_id)
    JOIN dim_region AS r USING (region_id)
    JOIN dim_company AS c USING (company_id)
    GROUP BY ALL
)
SELECT
    *,
    SUM(company_volume_mwh) OVER (PARTITION BY date, region_name) AS market_volume_mwh,
    company_volume_mwh
        / NULLIF(SUM(company_volume_mwh) OVER (PARTITION BY date, region_name), 0)
        AS market_share,
    gross_profit / NULLIF(revenue, 0) AS gross_margin_pct
FROM company_totals;

CREATE OR REPLACE VIEW vw_market_metrics AS
WITH monthly AS (
    SELECT
        date,
        region_name,
        SUM(company_volume_mwh) AS market_volume_mwh,
        SUM(company_volume_mwh) FILTER (WHERE company_type = 'Focus company')
            AS focus_volume_mwh
    FROM vw_company_monthly
    GROUP BY ALL
),
lagged AS (
    SELECT
        *,
        focus_volume_mwh / NULLIF(market_volume_mwh, 0) AS focus_market_share,
        LAG(market_volume_mwh, 1) OVER regional_window AS prior_month_market_volume,
        LAG(market_volume_mwh, 12) OVER regional_window AS prior_year_market_volume,
        LAG(focus_volume_mwh, 12) OVER regional_window AS prior_year_focus_volume,
        AVG(market_volume_mwh) OVER (
            PARTITION BY region_name ORDER BY date ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) AS market_volume_rolling_3m,
        AVG(market_volume_mwh) OVER (
            PARTITION BY region_name ORDER BY date ROWS BETWEEN 5 PRECEDING AND CURRENT ROW
        ) AS market_volume_rolling_6m
    FROM monthly
    WINDOW regional_window AS (PARTITION BY region_name ORDER BY date)
)
SELECT
    *,
    1 - focus_market_share AS competitor_market_share,
    (market_volume_mwh - prior_month_market_volume) / NULLIF(prior_month_market_volume, 0)
        AS market_mom_growth,
    (market_volume_mwh - prior_year_market_volume) / NULLIF(prior_year_market_volume, 0)
        AS market_yoy_growth,
    (focus_volume_mwh - prior_year_focus_volume)
        / NULLIF(prior_year_focus_volume, 0) AS focus_yoy_growth
FROM lagged;
