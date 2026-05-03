-- LoopLens BigQuery table inventory
-- Replace PROJECT_ID_HERE with your real BigQuery project ID.

SELECT 'cra' AS dataset_name, table_name, row_count, size_bytes
FROM `PROJECT_ID_HERE.cra.__TABLES__`
UNION ALL
SELECT 'fed' AS dataset_name, table_name, row_count, size_bytes
FROM `PROJECT_ID_HERE.fed.__TABLES__`
UNION ALL
SELECT 'ab' AS dataset_name, table_name, row_count, size_bytes
FROM `PROJECT_ID_HERE.ab.__TABLES__`
UNION ALL
SELECT 'general' AS dataset_name, table_name, row_count, size_bytes
FROM `PROJECT_ID_HERE.general.__TABLES__`
UNION ALL
SELECT 'agency_hackathon_data' AS dataset_name, table_name, row_count, size_bytes
FROM `PROJECT_ID_HERE.agency_hackathon_data.__TABLES__`
ORDER BY dataset_name, table_name;
