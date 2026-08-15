CREATE OR REPLACE VIEW vw_executive_kpis AS
WITH boundaries AS (
    SELECT MAX(date) AS max_date FROM dim_date
),
periods AS (
    SELECT
        CASE
            WHEN d.date > b.max_date - INTERVAL 12 MONTH THEN 'current'
            WHEN d.date > b.max_date - INTERVAL 24 MONTH
                AND d.date <= b.max_date - INTERVAL 12 MONTH THEN 'prior'
        END AS period,
        SUM(f.volume_mwh) AS market_volume,
        SUM(f.volume_mwh) FILTER (WHERE c.company_name = 'Northstar Energy')
            AS northstar_volume,
        SUM(f.revenue) FILTER (WHERE c.company_name = 'Northstar Energy')
            AS northstar_revenue,
        SUM(f.gross_profit) FILTER (WHERE c.company_name = 'Northstar Energy')
            AS northstar_gross_profit
    FROM fact_sales AS f
    JOIN dim_date AS d USING (month_id)
    JOIN dim_company AS c USING (company_id)
    CROSS JOIN boundaries AS b
    WHERE d.date > b.max_date - INTERVAL 24 MONTH
    GROUP BY period
),
pivoted AS (
    SELECT
        MAX(market_volume) FILTER (WHERE period = 'current') AS market_volume,
        MAX(market_volume) FILTER (WHERE period = 'prior') AS prior_market_volume,
        MAX(northstar_volume) FILTER (WHERE period = 'current') AS northstar_volume,
        MAX(northstar_volume) FILTER (WHERE period = 'prior') AS prior_northstar_volume,
        MAX(northstar_revenue) FILTER (WHERE period = 'current') AS northstar_revenue,
        MAX(northstar_revenue) FILTER (WHERE period = 'prior') AS prior_northstar_revenue,
        MAX(northstar_gross_profit) FILTER (WHERE period = 'current') AS gross_profit,
        MAX(northstar_gross_profit) FILTER (WHERE period = 'prior') AS prior_gross_profit
    FROM periods
)
SELECT
    *,
    northstar_volume / NULLIF(market_volume, 0) AS northstar_market_share,
    prior_northstar_volume / NULLIF(prior_market_volume, 0) AS prior_northstar_market_share,
    (market_volume - prior_market_volume) / NULLIF(prior_market_volume, 0)
        AS market_yoy_growth,
    (northstar_volume - prior_northstar_volume) / NULLIF(prior_northstar_volume, 0)
        AS northstar_yoy_growth,
    (
        northstar_volume / NULLIF(market_volume, 0)
        - prior_northstar_volume / NULLIF(prior_market_volume, 0)
    ) * 100 AS share_change_pp,
    gross_profit / NULLIF(northstar_revenue, 0) AS gross_margin_pct,
    prior_gross_profit / NULLIF(prior_northstar_revenue, 0) AS prior_gross_margin_pct,
    (
        gross_profit / NULLIF(northstar_revenue, 0)
        - prior_gross_profit / NULLIF(prior_northstar_revenue, 0)
    ) * 100 AS gross_margin_change_pp
FROM pivoted;

CREATE OR REPLACE VIEW vw_regional_share_change AS
SELECT
    region_name,
    northstar_share,
    share_momentum,
    share_momentum * 100 AS share_change_pp,
    RANK() OVER (ORDER BY share_momentum DESC) AS gain_rank,
    RANK() OVER (ORDER BY share_momentum ASC) AS loss_rank
FROM vw_regional_opportunity_inputs;
