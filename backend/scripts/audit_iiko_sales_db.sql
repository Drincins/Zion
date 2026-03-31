\echo '=== Largest relations in current database ==='
SELECT
    n.nspname AS schema_name,
    c.relname AS relation_name,
    c.relkind AS relation_kind,
    pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size,
    pg_size_pretty(pg_relation_size(c.oid)) AS table_size,
    pg_size_pretty(pg_indexes_size(c.oid)) AS indexes_size,
    pg_size_pretty(COALESCE(pg_total_relation_size(c.reltoastrelid), 0)) AS toast_total_size
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relkind IN ('r', 'm')
ORDER BY pg_total_relation_size(c.oid) DESC
LIMIT 30;

\echo ''
\echo '=== iiko sales relations size breakdown ==='
WITH targets AS (
    SELECT unnest(ARRAY[
        'iiko_sale_orders',
        'iiko_sale_items',
        'iiko_sales_location_mappings',
        'iiko_sales_halls',
        'iiko_sales_hall_zones',
        'iiko_sales_hall_tables',
        'iiko_sales_sync_settings'
    ]) AS relname
)
SELECT
    c.relname AS relation_name,
    pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size,
    pg_size_pretty(pg_relation_size(c.oid)) AS table_size,
    pg_size_pretty(pg_indexes_size(c.oid)) AS indexes_size,
    pg_size_pretty(COALESCE(pg_total_relation_size(c.reltoastrelid), 0)) AS toast_total_size,
    c.reltuples::bigint AS estimated_rows
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN targets t ON t.relname = c.relname
WHERE n.nspname = 'public'
ORDER BY pg_total_relation_size(c.oid) DESC;

\echo ''
\echo '=== Table and index usage stats for iiko sales relations ==='
SELECT
    relname,
    seq_scan,
    seq_tup_read,
    idx_scan,
    idx_tup_fetch,
    n_tup_ins,
    n_tup_upd,
    n_tup_del,
    n_live_tup,
    n_dead_tup,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables
WHERE relname IN (
    'iiko_sale_orders',
    'iiko_sale_items',
    'iiko_sales_location_mappings',
    'iiko_sales_halls',
    'iiko_sales_hall_zones',
    'iiko_sales_hall_tables',
    'iiko_sales_sync_settings'
)
ORDER BY relname;

\echo ''
\echo '=== Index sizes and scan counts for iiko sales relations ==='
SELECT
    t.relname AS table_name,
    i.relname AS index_name,
    pg_size_pretty(pg_relation_size(i.oid)) AS index_size,
    COALESCE(sui.idx_scan, 0) AS idx_scan,
    COALESCE(sui.idx_tup_read, 0) AS idx_tup_read,
    COALESCE(sui.idx_tup_fetch, 0) AS idx_tup_fetch
FROM pg_class t
JOIN pg_index ix ON ix.indrelid = t.oid
JOIN pg_class i ON i.oid = ix.indexrelid
JOIN pg_namespace n ON n.oid = t.relnamespace
LEFT JOIN pg_stat_user_indexes sui ON sui.indexrelid = i.oid
WHERE n.nspname = 'public'
  AND t.relname IN (
      'iiko_sale_orders',
      'iiko_sale_items',
      'iiko_sales_location_mappings',
      'iiko_sales_halls',
      'iiko_sales_hall_zones',
      'iiko_sales_hall_tables',
      'iiko_sales_sync_settings'
  )
ORDER BY t.relname, pg_relation_size(i.oid) DESC;

\echo ''
\echo '=== Estimated monthly growth by orders ==='
SELECT
    date_trunc('month', open_date)::date AS month,
    source_restaurant_id,
    restaurant_id,
    COUNT(*) AS orders_count
FROM iiko_sale_orders
WHERE open_date IS NOT NULL
GROUP BY 1, 2, 3
ORDER BY month DESC, source_restaurant_id NULLS FIRST, restaurant_id;

\echo ''
\echo '=== Estimated monthly growth by items ==='
SELECT
    date_trunc('month', open_date)::date AS month,
    source_restaurant_id,
    restaurant_id,
    COUNT(*) AS items_count,
    ROUND(COALESCE(SUM(sum), 0)::numeric, 2) AS gross_sum
FROM iiko_sale_items
WHERE open_date IS NOT NULL
GROUP BY 1, 2, 3
ORDER BY month DESC, source_restaurant_id NULLS FIRST, restaurant_id;

\echo ''
\echo '=== Approximate raw_payload footprint (sampled) ==='
SELECT
    'iiko_sale_orders' AS table_name,
    COUNT(*) AS sampled_rows,
    ROUND(AVG(pg_column_size(raw_payload))::numeric, 2) AS avg_payload_bytes,
    MAX(pg_column_size(raw_payload)) AS max_payload_bytes
FROM iiko_sale_orders TABLESAMPLE SYSTEM (1)
WHERE raw_payload IS NOT NULL
UNION ALL
SELECT
    'iiko_sale_items' AS table_name,
    COUNT(*) AS sampled_rows,
    ROUND(AVG(pg_column_size(raw_payload))::numeric, 2) AS avg_payload_bytes,
    MAX(pg_column_size(raw_payload)) AS max_payload_bytes
FROM iiko_sale_items TABLESAMPLE SYSTEM (1)
WHERE raw_payload IS NOT NULL;

\echo ''
\echo '=== Optional exact raw_payload totals (heavy full scan) ==='
\echo 'Uncomment and run only in a quiet maintenance window if needed.'
-- SELECT
--     'iiko_sale_orders' AS table_name,
--     COUNT(*) AS rows_count,
--     pg_size_pretty(SUM(pg_column_size(raw_payload))) AS raw_payload_total
-- FROM iiko_sale_orders
-- WHERE raw_payload IS NOT NULL
-- UNION ALL
-- SELECT
--     'iiko_sale_items' AS table_name,
--     COUNT(*) AS rows_count,
--     pg_size_pretty(SUM(pg_column_size(raw_payload))) AS raw_payload_total
-- FROM iiko_sale_items
-- WHERE raw_payload IS NOT NULL;
