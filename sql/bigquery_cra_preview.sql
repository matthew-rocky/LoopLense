-- CRA preview helpers for LoopLens.
-- Replace PROJECT_ID_HERE with your BigQuery project ID.

-- List CRA tables.
SELECT table_name
FROM `PROJECT_ID_HERE.cra.INFORMATION_SCHEMA.TABLES`
ORDER BY table_name;

-- List CRA columns.
SELECT table_name, column_name, data_type
FROM `PROJECT_ID_HERE.cra.INFORMATION_SCHEMA.COLUMNS`
ORDER BY table_name, ordinal_position;

-- Row counts and table sizes.
SELECT table_id AS table_name, row_count, ROUND(size_bytes / 1024 / 1024, 2) AS size_mb
FROM `PROJECT_ID_HERE.cra.__TABLES__`
ORDER BY size_bytes DESC;

-- Find likely relevant tables.
SELECT table_name
FROM `PROJECT_ID_HERE.cra.INFORMATION_SCHEMA.TABLES`
WHERE REGEXP_CONTAINS(
  LOWER(table_name),
  r'(disbursement|donee|funding|financial|identification|overhead|loop)'
)
ORDER BY table_name;

-- Preview likely relevant tables. Replace table names if your dataset differs.
SELECT * FROM `PROJECT_ID_HERE.cra.cra_identification` LIMIT 100;
SELECT * FROM `PROJECT_ID_HERE.cra.cra_qualified_donees` LIMIT 100;
SELECT * FROM `PROJECT_ID_HERE.cra.cra_financial_general` LIMIT 100;
SELECT * FROM `PROJECT_ID_HERE.cra.govt_funding_by_charity` LIMIT 100;
SELECT * FROM `PROJECT_ID_HERE.cra.overhead_by_charity` LIMIT 100;
SELECT * FROM `PROJECT_ID_HERE.cra.loops` LIMIT 100;
SELECT * FROM `PROJECT_ID_HERE.cra.loop_edges` LIMIT 100;
