CREATE OR REPLACE VIEW vw_regional_opportunity_inputs AS
WITH boundaries AS (
    SELECT MAX(date) AS max_date FROM dim_date
),
period_company AS (
    SELECT
        r.region_name,
        c.company_name,
        c.company_type,
        CASE
            WHEN d.date > b.max_date - INTERVAL 12 MONTH THEN 'current'
            WHEN d.date > b.max_date - INTERVAL 24 MONTH
                AND d.date <= b.max_date - INTERVAL 12 MONTH THEN 'prior'
        END AS period,
        SUM(f.volume_mwh) AS volume_mwh,
        SUM(f.revenue) AS revenue,
        SUM(f.gross_profit) AS gross_profit
    FROM fact_sales AS f
    JOIN dim_date AS d USING (month_id)
    JOIN dim_region AS r USING (region_id)
    JOIN dim_company AS c USING (company_id)
    CROSS JOIN boundaries AS b
    WHERE d.date > b.max_date - INTERVAL 24 MONTH
    GROUP BY ALL
),
shares AS (
    SELECT
        *,
        volume_mwh / NULLIF(SUM(volume_mwh) OVER (PARTITION BY region_name, period), 0)
            AS market_share
    FROM period_company
),
regional AS (
    SELECT
        region_name,
        SUM(volume_mwh) FILTER (WHERE period = 'current') AS market_volume,
        SUM(volume_mwh) FILTER (WHERE period = 'prior') AS prior_market_volume,
        MAX(market_share) FILTER (
            WHERE period = 'current' AND company_type = 'Focus company'
        ) AS focus_share,
        MAX(market_share) FILTER (
            WHERE period = 'prior' AND company_type = 'Focus company'
        ) AS prior_focus_share,
        SUM(gross_profit) FILTER (
            WHERE period = 'current' AND company_type = 'Focus company'
        ) / NULLIF(SUM(revenue) FILTER (
            WHERE period = 'current' AND company_type = 'Focus company'
        ), 0) AS gross_margin_pct,
        SUM(POWER(market_share, 2)) FILTER (WHERE period = 'current') AS hhi
    FROM shares
    GROUP BY region_name
)
SELECT
    region_name,
    market_volume,
    (market_volume - prior_market_volume) / NULLIF(prior_market_volume, 0) AS market_growth,
    focus_share,
    focus_share - prior_focus_share AS share_momentum,
    gross_margin_pct,
    hhi
FROM regional;
