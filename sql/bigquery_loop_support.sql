-- LoopLens support-file SQL templates.
-- Replace PROJECT_ID_HERE and table/column names to match the official schema.

-- Charity identification summary.
CREATE OR REPLACE TABLE `PROJECT_ID_HERE.cra_support.charity_profiles` AS
SELECT
  CAST(bn AS STRING) AS bn,
  ANY_VALUE(account_name) AS charity_name,
  ANY_VALUE(designation) AS designation
FROM `PROJECT_ID_HERE.cra.cra_identification`
GROUP BY bn;

-- Government funding summary.
CREATE OR REPLACE TABLE `PROJECT_ID_HERE.cra_support.govt_funding_by_charity` AS
SELECT
  CAST(bn AS STRING) AS bn,
  SUM(total_government_funding) AS total_govt_all_years,
  SAFE_DIVIDE(SUM(total_government_funding), NULLIF(SUM(total_revenue), 0)) AS max_govt_share_pct
FROM `PROJECT_ID_HERE.cra.cra_financial_general`
GROUP BY bn;

-- Overhead summary. Adjust field names for strict or broad overhead definitions.
CREATE OR REPLACE TABLE `PROJECT_ID_HERE.cra_support.overhead_by_charity` AS
SELECT
  CAST(bn AS STRING) AS bn,
  MAX(SAFE_DIVIDE(management_admin_expenses, NULLIF(total_expenses, 0))) AS max_strict_overhead_pct,
  MAX(SAFE_DIVIDE(management_admin_expenses + fundraising_expenses, NULLIF(total_expenses, 0))) AS max_broad_overhead_pct
FROM `PROJECT_ID_HERE.cra.cra_financial_general`
GROUP BY bn;

-- Charity transfer and donee summary. Replace amount/year fields as needed.
CREATE OR REPLACE TABLE `PROJECT_ID_HERE.cra_support.charity_transfer_summary` AS
SELECT
  CAST(donor_bn AS STRING) AS from_bn,
  CAST(donee_bn AS STRING) AS to_bn,
  fiscal_year AS year,
  SUM(amount) AS amount
FROM `PROJECT_ID_HERE.cra.cra_qualified_donees`
WHERE donor_bn IS NOT NULL AND donee_bn IS NOT NULL
GROUP BY from_bn, to_bn, year;

-- Loop-supporting fields exported for the local Streamlit app.
SELECT
  l.loop_id,
  l.participant_count,
  l.total_flow AS total_flow,
  l.bottleneck_amt,
  g.max_govt_share_pct AS loop_max_govt_share_pct,
  o.max_strict_overhead_pct AS loop_max_strict_overhead_pct,
  l.same_year
FROM `PROJECT_ID_HERE.cra.loops` l
LEFT JOIN `PROJECT_ID_HERE.cra_support.govt_funding_by_charity` g
  ON CAST(l.primary_bn AS STRING) = g.bn
LEFT JOIN `PROJECT_ID_HERE.cra_support.overhead_by_charity` o
  ON CAST(l.primary_bn AS STRING) = o.bn;
