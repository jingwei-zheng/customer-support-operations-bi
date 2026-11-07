-- Reporting views adapted from the original SQL.
-- Helpdesk scope for demand; resolved tickets created >=2016 for service time.
-- Backlog is a fixed snapshot at 2023-03-14, not a historical backlog series.

DROP VIEW IF EXISTS analytics.v_kpi_summary CASCADE;
DROP VIEW IF EXISTS analytics.v_monthly_volume CASCADE;
DROP VIEW IF EXISTS analytics.v_priority_breakdown CASCADE;
DROP VIEW IF EXISTS analytics.v_resolution_metrics CASCADE;
DROP VIEW IF EXISTS analytics.v_backlog_ageing CASCADE;
DROP VIEW IF EXISTS analytics.v_longest_open_cases CASCADE;
DROP VIEW IF EXISTS analytics.v_powerbi_tickets CASCADE;

CREATE OR REPLACE VIEW analytics.v_kpi_summary AS
WITH hd AS (SELECT * FROM analytics.fact_ticket WHERE is_helpdesk_ticket),
res AS (SELECT * FROM hd WHERE is_resolved AND in_system_period)
SELECT
    (SELECT count(*) FROM hd)                                                         AS total_helpdesk_tickets,
    (SELECT count(*) FROM analytics.fact_ticket)                                      AS total_work_items,
    (SELECT count(*) FROM hd WHERE in_system_period)                                  AS tickets_since_2016,
    (SELECT min(created_at)::date FROM hd)                                            AS first_ticket_date,
    (SELECT max(created_at)::date FROM hd)                                            AS last_ticket_date,
    (SELECT count(*) FROM hd WHERE is_open_backlog)                                   AS open_backlog,
    (SELECT round(percentile_cont(0.5) WITHIN GROUP (ORDER BY resolution_hours)::numeric, 1) FROM res) AS median_resolution_hours,
    (SELECT round(avg(resolution_hours)::numeric, 1) FROM res)                        AS mean_resolution_hours,
    (SELECT round(percentile_cont(0.9) WITHIN GROUP (ORDER BY resolution_hours)::numeric, 1) FROM res) AS p90_resolution_hours,
    (SELECT round(100.0 * count(*) FILTER (WHERE is_high_severity) / NULLIF(count(*) FILTER (WHERE priority_known), 0), 1) FROM hd) AS high_severity_share_pct,
    (SELECT count(DISTINCT reporter_id) FROM hd)                                      AS distinct_reporters,
    (SELECT count(DISTINCT project_key) FROM hd)                                      AS distinct_projects,
    (SELECT count(DISTINCT assignee_id) FROM hd WHERE assignee_id <> 'unassigned')    AS distinct_assignees;

CREATE OR REPLACE VIEW analytics.v_monthly_volume AS
WITH months AS (
    SELECT DISTINCT year_month FROM analytics.dim_date
    WHERE full_date BETWEEN DATE '2007-04-01' AND DATE '2023-03-31'
),
counts AS (
    SELECT created_month AS year_month,
           count(*)                                       AS tickets_created,
           count(*) FILTER (WHERE is_high_severity)       AS high_severity_created,
           count(DISTINCT reporter_id)                    AS active_reporters
    FROM analytics.fact_ticket WHERE is_helpdesk_ticket GROUP BY 1
),
resolved AS (
    -- tickets_resolved_in_period excludes legacy (pre-2016) tickets, which were bulk-closed in Aug 2018
    SELECT to_char(resolved_at, 'YYYY-MM') AS year_month,
           count(*) AS tickets_resolved,
           count(*) FILTER (WHERE in_system_period) AS tickets_resolved_in_period
    FROM analytics.fact_ticket WHERE is_helpdesk_ticket AND is_resolved GROUP BY 1
),
joined AS (
    SELECT m.year_month,
           COALESCE(c.tickets_created, 0)        AS tickets_created,
           COALESCE(r.tickets_resolved, 0)       AS tickets_resolved,
           COALESCE(r.tickets_resolved_in_period, 0) AS tickets_resolved_in_period,
           COALESCE(c.high_severity_created, 0)  AS high_severity_created,
           COALESCE(c.active_reporters, 0)       AS active_reporters
    FROM months m LEFT JOIN counts c USING (year_month) LEFT JOIN resolved r USING (year_month)
)
SELECT year_month,
       left(year_month, 4)::int AS year,
       tickets_created, tickets_resolved, tickets_resolved_in_period, high_severity_created, active_reporters,
       lag(tickets_created) OVER (ORDER BY year_month)                                       AS prev_month_created,
       tickets_created - lag(tickets_created) OVER (ORDER BY year_month)                     AS mom_change,
       CASE WHEN year_month = '2023-03' THEN NULL ELSE round(100.0 * (tickets_created - lag(tickets_created) OVER (ORDER BY year_month))
             / NULLIF(lag(tickets_created) OVER (ORDER BY year_month), 0), 1) END            AS mom_change_pct,
       round(avg(tickets_created) OVER (ORDER BY year_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 1) AS rolling_3m_avg_created,
       round(avg(tickets_created) OVER (ORDER BY year_month ROWS BETWEEN 11 PRECEDING AND CURRENT ROW), 1) AS rolling_12m_avg_created,
       lag(tickets_created, 12) OVER (ORDER BY year_month)                                   AS same_month_prev_year,
       CASE WHEN year_month = '2023-03' THEN NULL ELSE round(100.0 * (tickets_created - lag(tickets_created, 12) OVER (ORDER BY year_month))
             / NULLIF(lag(tickets_created, 12) OVER (ORDER BY year_month), 0), 1) END        AS yoy_change_pct,
       year_month >= '2016-01'                                                               AS in_system_period
FROM joined;

CREATE OR REPLACE VIEW analytics.v_priority_breakdown AS
SELECT p.priority, p.priority_rank, p.is_high_severity,
       count(f.ticket_id)                                                                       AS tickets,
       round(100.0 * count(f.ticket_id) / NULLIF(sum(count(f.ticket_id)) OVER (), 0), 2)       AS share_pct,
       round(percentile_cont(0.5) WITHIN GROUP (ORDER BY f.resolution_hours) FILTER (WHERE f.is_resolved AND f.in_system_period)::numeric, 1) AS median_resolution_hours,
       round(avg(f.resolution_hours) FILTER (WHERE f.is_resolved AND f.in_system_period)::numeric, 1) AS mean_resolution_hours,
       count(*) FILTER (WHERE f.is_open_backlog)                                                AS open_tickets
FROM analytics.fact_ticket f
JOIN analytics.dim_priority p USING (priority_key)
WHERE f.is_helpdesk_ticket AND f.priority_known
GROUP BY p.priority, p.priority_rank, p.is_high_severity;

CREATE OR REPLACE VIEW analytics.v_resolution_metrics AS
WITH res AS (
    SELECT * FROM analytics.fact_ticket WHERE is_helpdesk_ticket AND is_resolved AND in_system_period
),
by_priority AS (
    SELECT 'priority' AS dimension, priority AS member, count(*) AS tickets,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY resolution_hours) AS median_hours,
           avg(resolution_hours) AS mean_hours,
           percentile_cont(0.9) WITHIN GROUP (ORDER BY resolution_hours) AS p90_hours,
           avg(waiting_hours) AS mean_waiting_hours,
           avg(in_progress_hours) AS mean_in_progress_hours
    FROM res WHERE priority_known GROUP BY priority
),
by_type AS (
    SELECT 'issue_type', issue_type, count(*),
           percentile_cont(0.5) WITHIN GROUP (ORDER BY resolution_hours), avg(resolution_hours),
           percentile_cont(0.9) WITHIN GROUP (ORDER BY resolution_hours), avg(waiting_hours), avg(in_progress_hours)
    FROM res GROUP BY issue_type
),
by_segment AS (
    SELECT 'requester_segment', requester_segment_derived, count(*),
           percentile_cont(0.5) WITHIN GROUP (ORDER BY resolution_hours), avg(resolution_hours),
           percentile_cont(0.9) WITHIN GROUP (ORDER BY resolution_hours), avg(waiting_hours), avg(in_progress_hours)
    FROM res GROUP BY requester_segment_derived
),
by_scope AS (
    SELECT 'project_scope', project_scope, count(*),
           percentile_cont(0.5) WITHIN GROUP (ORDER BY resolution_hours), avg(resolution_hours),
           percentile_cont(0.9) WITHIN GROUP (ORDER BY resolution_hours), avg(waiting_hours), avg(in_progress_hours)
    FROM res GROUP BY project_scope
),
by_year AS (
    SELECT 'year', left(created_month, 4), count(*),
           percentile_cont(0.5) WITHIN GROUP (ORDER BY resolution_hours), avg(resolution_hours),
           percentile_cont(0.9) WITHIN GROUP (ORDER BY resolution_hours), avg(waiting_hours), avg(in_progress_hours)
    FROM res GROUP BY left(created_month, 4)
),
all_rows AS (
    SELECT * FROM by_priority UNION ALL SELECT * FROM by_type UNION ALL SELECT * FROM by_segment
    UNION ALL SELECT * FROM by_scope UNION ALL SELECT * FROM by_year
)
SELECT dimension, member, tickets,
       round(median_hours::numeric, 1) AS median_hours,
       round(mean_hours::numeric, 1)   AS mean_hours,
       round(p90_hours::numeric, 1)    AS p90_hours,
       round((median_hours / 24.0)::numeric, 2) AS median_days,
       round(mean_waiting_hours::numeric, 1) AS mean_waiting_hours,
       round(mean_in_progress_hours::numeric, 1) AS mean_in_progress_hours,
       rank() OVER (PARTITION BY dimension ORDER BY median_hours DESC) AS slowest_rank
FROM all_rows;

CREATE OR REPLACE VIEW analytics.v_backlog_ageing AS
WITH open_t AS (
    SELECT ticket_id, priority, issue_type, status, age_days_at_extract, is_high_severity,
           CASE WHEN age_days_at_extract < 7 THEN '0-7 days'
                WHEN age_days_at_extract < 30 THEN '7-30 days'
                WHEN age_days_at_extract < 90 THEN '30-90 days'
                WHEN age_days_at_extract < 365 THEN '90-365 days'
                ELSE '365+ days' END AS age_bucket,
           CASE WHEN age_days_at_extract < 7 THEN 1 WHEN age_days_at_extract < 30 THEN 2
                WHEN age_days_at_extract < 90 THEN 3 WHEN age_days_at_extract < 365 THEN 4 ELSE 5 END AS age_bucket_order
    FROM analytics.fact_ticket WHERE is_helpdesk_ticket AND is_open_backlog
)
SELECT age_bucket, age_bucket_order,
       count(*) AS open_tickets,
       count(*) FILTER (WHERE is_high_severity) AS open_high_severity,
       round(100.0 * count(*) / sum(count(*)) OVER (), 1) AS share_pct,
       round(avg(age_days_at_extract)::numeric, 1) AS mean_age_days,
       round(max(age_days_at_extract)::numeric, 1) AS max_age_days
FROM open_t GROUP BY 1, 2;

CREATE OR REPLACE VIEW analytics.v_longest_open_cases AS
SELECT ticket_id, issue_type, priority, status, project_key, project_country_code, reporter_id, assignee_id,
       created_at::date AS created_date, last_change_at::date AS last_change_date,
       round(age_days_at_extract::numeric, 1) AS age_days, comment_count, contributor_count,
       rank() OVER (ORDER BY age_days_at_extract DESC) AS age_rank
FROM analytics.fact_ticket WHERE is_helpdesk_ticket AND is_open_backlog;

CREATE OR REPLACE VIEW analytics.v_powerbi_tickets AS
SELECT f.ticket_id, f.created_at::date AS created_date, f.resolved_at::date AS resolved_date, f.created_month,
       f.issue_type, f.work_item_class, f.is_helpdesk_ticket,
       f.priority, p.priority_rank, f.priority_known, f.is_high_severity,
       f.status, f.resolution, f.is_resolved, f.is_open_backlog, f.was_reopened, f.in_system_period,
       f.project_key, f.project_country_code, f.project_scope, f.reporter_id, f.requester_segment_derived, f.assignee_id,
       f.contributor_count, f.comment_count, f.processing_steps,
       round(f.resolution_hours::numeric, 2) AS resolution_hours,
       round(f.resolution_days::numeric, 2)  AS resolution_days,
       round(f.waiting_hours::numeric, 2)    AS waiting_hours,
       round(f.in_progress_hours::numeric, 2) AS in_progress_hours,
       f.age_days_at_extract AS age_days_at_extract,
       (f.is_open_backlog AND f.age_days_at_extract >= 30) AS is_backlog_30_plus,
       CASE WHEN NOT f.is_open_backlog THEN NULL
            WHEN f.age_days_at_extract < 7 THEN '0-7 days'
            WHEN f.age_days_at_extract < 30 THEN '7-30 days'
            WHEN f.age_days_at_extract < 90 THEN '30-90 days'
            WHEN f.age_days_at_extract < 365 THEN '90-365 days'
            ELSE '365+ days' END AS backlog_age_bucket,
       CASE WHEN NOT f.is_open_backlog THEN NULL
            WHEN f.age_days_at_extract < 7 THEN 1
            WHEN f.age_days_at_extract < 30 THEN 2
            WHEN f.age_days_at_extract < 90 THEN 3
            WHEN f.age_days_at_extract < 365 THEN 4
            ELSE 5 END AS backlog_age_bucket_order,
       CASE WHEN f.resolution_hours IS NULL THEN NULL
            WHEN f.resolution_hours <= 24 THEN '0-1 day' WHEN f.resolution_hours <= 72 THEN '1-3 days'
            WHEN f.resolution_hours <= 168 THEN '3-7 days' WHEN f.resolution_hours <= 720 THEN '7-30 days'
            ELSE '30+ days' END AS resolution_bucket
FROM analytics.fact_ticket f JOIN analytics.dim_priority p USING (priority_key);
