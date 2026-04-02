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
\echo '=== KPI relations size breakdown ==='
WITH targets AS (
    SELECT unnest(ARRAY[
        'kpi_metrics',
        'kpi_metric_groups',
        'kpi_rules',
        'kpi_metric_group_rules',
        'kpi_results',
        'kpi_plan_facts',
        'kpi_plan_preferences',
        'kpi_metric_group_plan_facts',
        'kpi_metric_group_plan_preferences',
        'kpi_payout_batches',
        'kpi_payout_items'
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
\echo '=== Table usage stats for KPI relations ==='
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
    'kpi_metrics',
    'kpi_metric_groups',
    'kpi_rules',
    'kpi_metric_group_rules',
    'kpi_results',
    'kpi_plan_facts',
    'kpi_plan_preferences',
    'kpi_metric_group_plan_facts',
    'kpi_metric_group_plan_preferences',
    'kpi_payout_batches',
    'kpi_payout_items'
)
ORDER BY relname;

\echo ''
\echo '=== Index sizes and scan counts for KPI relations ==='
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
      'kpi_metrics',
      'kpi_metric_groups',
      'kpi_rules',
      'kpi_metric_group_rules',
      'kpi_results',
      'kpi_plan_facts',
      'kpi_plan_preferences',
      'kpi_metric_group_plan_facts',
      'kpi_metric_group_plan_preferences',
      'kpi_payout_batches',
      'kpi_payout_items'
  )
ORDER BY t.relname, pg_relation_size(i.oid) DESC;

\echo ''
\echo '=== KPI results growth by period start ==='
SELECT
    date_trunc('month', period_start)::date AS month,
    metric_id,
    restaurant_id,
    COUNT(*) AS results_count
FROM kpi_results
WHERE period_start IS NOT NULL
GROUP BY 1, 2, 3
ORDER BY month DESC, metric_id, restaurant_id;

\echo ''
\echo '=== KPI payouts growth by creation month ==='
SELECT
    date_trunc('month', created_at)::date AS month,
    rule_id,
    restaurant_id,
    status,
    COUNT(*) AS batches_count
FROM kpi_payout_batches
WHERE created_at IS NOT NULL
GROUP BY 1, 2, 3, 4
ORDER BY month DESC, rule_id, restaurant_id, status;

\echo ''
\echo '=== KPI payout items by batch period ==='
SELECT
    date_trunc('month', b.period_start)::date AS month,
    b.restaurant_id,
    b.position_id,
    COUNT(i.id) AS items_count,
    ROUND(COALESCE(SUM(i.base_amount + i.bonus_amount - i.penalty_amount), 0)::numeric, 2) AS net_amount
FROM kpi_payout_batches b
JOIN kpi_payout_items i ON i.batch_id = b.id
GROUP BY 1, 2, 3
ORDER BY month DESC, b.restaurant_id, b.position_id;

\echo ''
\echo '=== KPI plan/fact density by year ==='
SELECT
    'metric' AS scope_kind,
    year,
    COUNT(*) AS rows_count
FROM kpi_plan_facts
GROUP BY 1, 2
UNION ALL
SELECT
    'group' AS scope_kind,
    year,
    COUNT(*) AS rows_count
FROM kpi_metric_group_plan_facts
GROUP BY 1, 2
ORDER BY year DESC, scope_kind;

\echo ''
\echo '=== Approximate JSON footprint in KPI tables (sampled) ==='
SELECT
    'kpi_metrics.restaurant_ids' AS target,
    COUNT(*) AS sampled_rows,
    ROUND(AVG(pg_column_size(restaurant_ids))::numeric, 2) AS avg_payload_bytes,
    MAX(pg_column_size(restaurant_ids)) AS max_payload_bytes
FROM kpi_metrics TABLESAMPLE SYSTEM (10)
WHERE restaurant_ids IS NOT NULL
UNION ALL
SELECT
    'kpi_payout_items.calc_snapshot' AS target,
    COUNT(*) AS sampled_rows,
    ROUND(AVG(pg_column_size(calc_snapshot))::numeric, 2) AS avg_payload_bytes,
    MAX(pg_column_size(calc_snapshot)) AS max_payload_bytes
FROM kpi_payout_items TABLESAMPLE SYSTEM (10)
WHERE calc_snapshot IS NOT NULL;
