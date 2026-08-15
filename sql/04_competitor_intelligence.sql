CREATE OR REPLACE VIEW vw_competitor_momentum AS
WITH boundaries AS (
    SELECT MAX(date) AS max_date FROM dim_date
),
period_volume AS (
    SELECT
        c.company_name,
        CASE
            WHEN d.date > b.max_date - INTERVAL 12 MONTH THEN 'current'
            WHEN d.date > b.max_date - INTERVAL 24 MONTH
                AND d.date <= b.max_date - INTERVAL 12 MONTH THEN 'prior'
        END AS period,
        SUM(f.volume_mwh) AS company_volume
    FROM fact_sales AS f
    JOIN dim_date AS d USING (month_id)
    JOIN dim_company AS c USING (company_id)
    CROSS JOIN boundaries AS b
    WHERE d.date > b.max_date - INTERVAL 24 MONTH
    GROUP BY ALL
),
period_share AS (
    SELECT
        *,
        company_volume / NULLIF(SUM(company_volume) OVER (PARTITION BY period), 0) AS share
    FROM period_volume
),
pivoted AS (
    SELECT
        company_name,
        MAX(share) FILTER (WHERE period = 'current') AS current_share,
        MAX(share) FILTER (WHERE period = 'prior') AS prior_share
    FROM period_share
    GROUP BY company_name
)
SELECT
    *,
    (current_share - prior_share) * 100 AS share_change_pp,
    RANK() OVER (ORDER BY current_share - prior_share DESC) AS momentum_rank,
    CASE
        WHEN current_share - prior_share > 0.0025 THEN 'Gaining'
        WHEN current_share - prior_share < -0.0025 THEN 'Losing'
        ELSE 'Stable'
    END AS momentum_signal
FROM pivoted;

CREATE OR REPLACE VIEW vw_regional_company_ranking AS
WITH boundaries AS (
    SELECT MAX(date) AS max_date FROM dim_date
),
company_volume AS (
    SELECT
        r.region_name,
        c.company_name,
        SUM(f.volume_mwh) AS company_volume_mwh
    FROM fact_sales AS f
    JOIN dim_date AS d USING (month_id)
    JOIN dim_region AS r USING (region_id)
    JOIN dim_company AS c USING (company_id)
    CROSS JOIN boundaries AS b
    WHERE d.date > b.max_date - INTERVAL 12 MONTH
    GROUP BY ALL
)
SELECT
    *,
    company_volume_mwh / NULLIF(SUM(company_volume_mwh) OVER (PARTITION BY region_name), 0)
        AS market_share,
    RANK() OVER (PARTITION BY region_name ORDER BY company_volume_mwh DESC) AS company_rank
FROM company_volume;

CREATE OR REPLACE VIEW vw_regional_concentration AS
WITH shares AS (
    SELECT region_name, company_name, market_share
    FROM vw_regional_company_ranking
),
concentration AS (
    SELECT region_name, SUM(POWER(market_share, 2)) AS hhi
    FROM shares
    GROUP BY region_name
)
SELECT
    *,
    CASE
        WHEN hhi < 0.15 THEN 'Fragmented'
        WHEN hhi < 0.25 THEN 'Moderately concentrated'
        ELSE 'Concentrated'
    END AS concentration_classification
FROM concentration;
