-- Focus-company price–volume–mix bridge: latest 12 months versus the prior 12 months at
-- product × customer-segment level, on pocket (net) revenue and on gross profit.
--
-- For cell i with volumes V0/V1 and unit net price P0/P1 (shares s = V / total volume):
--   volume effect = (VT1 - VT0) × s0 × P0
--   mix effect    = VT1 × (s1 - s0) × P0
--   price effect  = V1 × (P1 - P0)
-- These three sum exactly to V1×P1 - V0×P0. Gross profit uses the unit margin M = P - C
-- for volume and mix, plus a separate unit-cost effect = -V1 × (C1 - C0).
-- A cell missing in one period takes its price/cost from the other period, which keeps the
-- identity exact (its price effect is then zero).
CREATE OR REPLACE VIEW vw_pvm_bridge AS
WITH boundaries AS (
    SELECT MAX(date) AS max_date FROM vw_pricing_detail
),
labelled AS (
    SELECT
        detail.*,
        CASE
            WHEN detail.date > b.max_date - INTERVAL 12 MONTH THEN 'current'
            WHEN detail.date > b.max_date - INTERVAL 24 MONTH THEN 'prior'
        END AS period
    FROM vw_pricing_detail AS detail
    CROSS JOIN boundaries AS b
),
cells AS (
    SELECT
        product_name,
        customer_segment_name,
        SUM(volume_mwh) FILTER (WHERE period = 'prior') AS prior_volume,
        SUM(volume_mwh) FILTER (WHERE period = 'current') AS current_volume,
        SUM(pocket_revenue) FILTER (WHERE period = 'prior') AS prior_revenue,
        SUM(pocket_revenue) FILTER (WHERE period = 'current') AS current_revenue,
        SUM(variable_cost) FILTER (WHERE period = 'prior') AS prior_variable_cost,
        SUM(variable_cost) FILTER (WHERE period = 'current') AS current_variable_cost
    FROM labelled
    WHERE period IS NOT NULL
    GROUP BY ALL
),
filled AS (
    SELECT
        product_name,
        customer_segment_name,
        COALESCE(prior_volume, 0) AS prior_volume,
        COALESCE(current_volume, 0) AS current_volume,
        COALESCE(prior_revenue, 0) AS prior_revenue,
        COALESCE(current_revenue, 0) AS current_revenue,
        COALESCE(prior_variable_cost, 0) AS prior_variable_cost,
        COALESCE(current_variable_cost, 0) AS current_variable_cost,
        COALESCE(prior_revenue / NULLIF(prior_volume, 0), current_revenue / current_volume)
            AS prior_price,
        COALESCE(current_revenue / NULLIF(current_volume, 0), prior_revenue / prior_volume)
            AS current_price,
        COALESCE(
            prior_variable_cost / NULLIF(prior_volume, 0), current_variable_cost / current_volume
        ) AS prior_unit_cost,
        COALESCE(
            current_variable_cost / NULLIF(current_volume, 0), prior_variable_cost / prior_volume
        ) AS current_unit_cost
    FROM cells
),
shares AS (
    SELECT
        *,
        SUM(prior_volume) OVER () AS prior_total_volume,
        SUM(current_volume) OVER () AS current_total_volume,
        prior_volume / SUM(prior_volume) OVER () AS prior_share,
        current_volume / SUM(current_volume) OVER () AS current_share
    FROM filled
),
effects AS (
    SELECT
        *,
        (current_total_volume - prior_total_volume) * prior_share * prior_price
            AS volume_effect,
        current_total_volume * (current_share - prior_share) * prior_price AS mix_effect,
        current_volume * (current_price - prior_price) AS price_effect,
        current_revenue - prior_revenue AS total_revenue_change,
        (current_total_volume - prior_total_volume) * prior_share
            * (prior_price - prior_unit_cost) AS gp_volume_effect,
        current_total_volume * (current_share - prior_share)
            * (prior_price - prior_unit_cost) AS gp_mix_effect,
        current_volume * (current_price - prior_price) AS gp_price_effect,
        -current_volume * (current_unit_cost - prior_unit_cost) AS gp_cost_effect,
        (current_revenue - current_variable_cost) - (prior_revenue - prior_variable_cost)
            AS total_gp_change
    FROM shares
)
SELECT
    *,
    total_revenue_change - (volume_effect + mix_effect + price_effect) AS reconciliation_gap,
    total_gp_change - (gp_volume_effect + gp_mix_effect + gp_price_effect + gp_cost_effect)
        AS gp_reconciliation_gap
FROM effects;

-- Compact component totals for charts and headline numbers.
CREATE OR REPLACE VIEW vw_pvm_bridge_summary AS
SELECT
    SUM(prior_revenue) AS prior_revenue,
    SUM(volume_effect) AS volume_effect,
    SUM(mix_effect) AS mix_effect,
    SUM(price_effect) AS price_effect,
    SUM(current_revenue) AS current_revenue,
    SUM(total_revenue_change) AS total_revenue_change,
    SUM(reconciliation_gap) AS reconciliation_gap,
    SUM(prior_revenue - prior_variable_cost) AS prior_gross_profit,
    SUM(gp_volume_effect) AS gp_volume_effect,
    SUM(gp_mix_effect) AS gp_mix_effect,
    SUM(gp_price_effect) AS gp_price_effect,
    SUM(gp_cost_effect) AS gp_cost_effect,
    SUM(current_revenue - current_variable_cost) AS current_gross_profit,
    SUM(total_gp_change) AS total_gp_change,
    SUM(gp_reconciliation_gap) AS gp_reconciliation_gap
FROM vw_pvm_bridge;
