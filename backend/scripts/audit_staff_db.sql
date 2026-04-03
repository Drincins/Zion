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
\echo '=== Staff relations size breakdown ==='
WITH targets AS (
    SELECT unnest(ARRAY[
        'users',
        'attendances',
        'employee_change_events',
        'employee_change_orders',
        'position_change_orders',
        'medical_check_records',
        'cis_document_records',
        'employment_document_records',
        'payroll_adjustments'
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
\echo '=== Table usage stats for staff relations ==='
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
    'users',
    'attendances',
    'employee_change_events',
    'employee_change_orders',
    'position_change_orders',
    'medical_check_records',
    'cis_document_records',
    'employment_document_records',
    'payroll_adjustments'
)
ORDER BY relname;

\echo ''
\echo '=== Index sizes and scan counts for staff relations ==='
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
      'users',
      'attendances',
      'employee_change_events',
      'employee_change_orders',
      'position_change_orders',
      'medical_check_records',
      'cis_document_records',
      'employment_document_records',
      'payroll_adjustments'
  )
ORDER BY t.relname, pg_relation_size(i.oid) DESC;

\echo ''
\echo '=== Attendances growth by month ==='
SELECT
    date_trunc('month', open_date)::date AS month,
    restaurant_id,
    position_id,
    COUNT(*) AS attendances_count
FROM attendances
WHERE open_date IS NOT NULL
GROUP BY 1, 2, 3
ORDER BY month DESC, restaurant_id, position_id;

\echo ''
\echo '=== Employee change events growth by month and field ==='
SELECT
    date_trunc('month', created_at)::date AS month,
    field,
    COUNT(*) AS events_count
FROM employee_change_events
WHERE created_at IS NOT NULL
GROUP BY 1, 2
ORDER BY month DESC, field;

\echo ''
\echo '=== Pending/applied staff change orders ==='
SELECT
    'employee' AS scope_kind,
    status::text AS status,
    COUNT(*) AS rows_count
FROM employee_change_orders
GROUP BY 1, 2
UNION ALL
SELECT
    'position' AS scope_kind,
    status::text AS status,
    COUNT(*) AS rows_count
FROM position_change_orders
GROUP BY 1, 2
ORDER BY scope_kind, status;
