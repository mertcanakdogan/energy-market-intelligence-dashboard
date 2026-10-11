-- Price waterfall: list -> on-invoice discount -> invoice -> off-invoice rebate
-- -> payment-term cost -> freight/service cost -> pocket price (all per MWh, volume weighted).
-- Discount depth is a fraction of list price on a 0–1 scale.
CREATE OR REPLACE VIEW vw_pricing_detail AS
SELECT
    d.date,
    d.month_id,
    d.month,
    r.region_name,
    p.product_name,
    s.customer_segment_name,
    f.volume_mwh,
    f.promo_flag,
    f.list_price,
    f.on_invoice_discount,
    f.invoice_price,
    f.off_invoice_rebate,
    f.payment_term_cost,
    f.freight_service_cost,
    f.pocket_price,
    f.unit_variable_cost,
    f.competitor_price,
    f.list_revenue,
    f.on_invoice_discount_amount,
    f.invoice_revenue,
    f.off_invoice_rebate_amount,
    f.payment_term_cost_amount,
    f.freight_service_cost_amount,
    f.pocket_revenue,
    f.variable_cost,
    f.gross_profit
FROM fact_pricing AS f
JOIN dim_date AS d USING (month_id)
JOIN dim_region AS r USING (region_id)
JOIN dim_product AS p USING (product_id)
JOIN dim_customer_segment AS s USING (customer_segment_id);

-- Model input for the Python elasticity and promotion estimators.
CREATE OR REPLACE VIEW vw_pricing_regression_input AS
SELECT
    month_id,
    month,
    region_name,
    product_name,
    customer_segment_name,
    volume_mwh,
    pocket_price,
    competitor_price,
    promo_flag
FROM vw_pricing_detail;

-- Latest 12 months by customer segment × region × product.
CREATE OR REPLACE VIEW vw_price_waterfall AS
WITH boundaries AS (
    SELECT MAX(date) AS max_date FROM vw_pricing_detail
),
recent AS (
    SELECT detail.*
    FROM vw_pricing_detail AS detail
    CROSS JOIN boundaries AS b
    WHERE detail.date > b.max_date - INTERVAL 12 MONTH
),
aggregated AS (
    SELECT
        customer_segment_name,
        region_name,
        product_name,
        SUM(volume_mwh) AS volume_mwh,
        SUM(list_revenue) AS list_revenue,
        SUM(on_invoice_discount_amount) AS on_invoice_discount_amount,
        SUM(invoice_revenue) AS invoice_revenue,
        SUM(off_invoice_rebate_amount) AS off_invoice_rebate_amount,
        SUM(payment_term_cost_amount) AS payment_term_cost_amount,
        SUM(freight_service_cost_amount) AS freight_service_cost_amount,
        SUM(pocket_revenue) AS pocket_revenue,
        SUM(variable_cost) AS variable_cost,
        SUM(gross_profit) AS gross_profit
    FROM recent
    GROUP BY ALL
)
SELECT
    *,
    list_revenue / volume_mwh AS list_price,
    on_invoice_discount_amount / volume_mwh AS on_invoice_discount,
    invoice_revenue / volume_mwh AS invoice_price,
    off_invoice_rebate_amount / volume_mwh AS off_invoice_rebate,
    payment_term_cost_amount / volume_mwh AS payment_term_cost,
    freight_service_cost_amount / volume_mwh AS freight_service_cost,
    pocket_revenue / volume_mwh AS pocket_price,
    variable_cost / volume_mwh AS unit_variable_cost,
    on_invoice_discount_amount / NULLIF(list_revenue, 0) AS on_invoice_discount_pct,
    (list_revenue - pocket_revenue) / NULLIF(list_revenue, 0) AS leakage_pct,
    pocket_revenue / NULLIF(list_revenue, 0) AS price_realization_pct,
    gross_profit / NULLIF(pocket_revenue, 0) AS pocket_margin_pct
FROM aggregated;

-- Policy check: average on-invoice discount depth versus the segment threshold,
-- ranked by the revenue given away above policy (latest 12 months).
CREATE OR REPLACE VIEW vw_discount_policy_flags AS
WITH by_region AS (
    SELECT
        customer_segment_name,
        region_name,
        SUM(volume_mwh) AS volume_mwh,
        SUM(list_revenue) AS list_revenue,
        SUM(on_invoice_discount_amount) AS on_invoice_discount_amount
    FROM vw_price_waterfall
    GROUP BY ALL
),
scored AS (
    SELECT
        b.*,
        b.on_invoice_discount_amount / NULLIF(b.list_revenue, 0) AS on_invoice_discount_pct,
        policy.max_discount_pct AS policy_max_discount_pct
    FROM by_region AS b
    JOIN dim_discount_policy AS policy USING (customer_segment_name)
)
SELECT
    *,
    on_invoice_discount_pct - policy_max_discount_pct AS excess_discount_pp,
    on_invoice_discount_pct > policy_max_discount_pct AS exceeds_policy,
    GREATEST(on_invoice_discount_pct - policy_max_discount_pct, 0) * list_revenue
        AS revenue_leakage_above_policy,
    RANK() OVER (
        PARTITION BY customer_segment_name
        ORDER BY on_invoice_discount_pct - policy_max_discount_pct DESC
    ) AS excess_rank_in_segment,
    SUM(GREATEST(on_invoice_discount_pct - policy_max_discount_pct, 0) * list_revenue)
        OVER () AS total_leakage_above_policy
FROM scored;
