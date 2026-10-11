CREATE OR REPLACE VIEW vw_growth_analysis AS
WITH national_monthly AS (
    SELECT
        date,
        SUM(company_volume_mwh) AS market_volume_mwh,
        SUM(company_volume_mwh) FILTER (WHERE company_type = 'Focus company')
            AS focus_volume_mwh
    FROM vw_company_monthly
    GROUP BY date
),
lagged AS (
    SELECT
        *,
        focus_volume_mwh / NULLIF(market_volume_mwh, 0) AS focus_market_share,
        LAG(market_volume_mwh, 1) OVER (ORDER BY date) AS prior_month_market_volume,
        LAG(market_volume_mwh, 12) OVER (ORDER BY date) AS prior_year_market_volume,
        LAG(focus_volume_mwh, 12) OVER (ORDER BY date) AS prior_year_focus_volume,
        LAG(focus_volume_mwh / NULLIF(market_volume_mwh, 0), 12)
            OVER (ORDER BY date) AS prior_year_focus_share,
        AVG(market_volume_mwh) OVER (
            ORDER BY date ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) AS market_volume_rolling_3m,
        AVG(market_volume_mwh) OVER (
            ORDER BY date ROWS BETWEEN 5 PRECEDING AND CURRENT ROW
        ) AS market_volume_rolling_6m,
        AVG(focus_volume_mwh) OVER (
            ORDER BY date ROWS BETWEEN 5 PRECEDING AND CURRENT ROW
        ) AS focus_volume_rolling_6m
    FROM national_monthly
)
SELECT
    *,
    (market_volume_mwh - prior_month_market_volume) / NULLIF(prior_month_market_volume, 0)
        AS market_mom_growth,
    (market_volume_mwh - prior_year_market_volume) / NULLIF(prior_year_market_volume, 0)
        AS market_yoy_growth,
    (focus_volume_mwh - prior_year_focus_volume)
        / NULLIF(prior_year_focus_volume, 0) AS focus_yoy_growth,
    (focus_market_share - prior_year_focus_share) * 100 AS share_change_pp
FROM lagged;
