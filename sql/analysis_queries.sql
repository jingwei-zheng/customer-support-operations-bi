-- Six reporting questions selected and adapted from the original SQL analysis.
-- Every demand query excludes internal work items. Complete-year comparisons stop at 2022.

-- name: q01_reporting_population
SELECT * FROM analytics.v_kpi_summary;

-- name: q02_yearly_volume_growth
WITH y AS (
    SELECT left(created_month, 4)::int AS year, count(*) AS tickets,
           count(DISTINCT reporter_id) AS active_reporters
    FROM analytics.fact_ticket
    WHERE is_helpdesk_ticket AND created_month BETWEEN '2016-01' AND '2022-12'
    GROUP BY 1
)
SELECT year, tickets, active_reporters,
       tickets - lag(tickets) OVER (ORDER BY year) AS yoy_change,
       round(100.0 * (tickets - lag(tickets) OVER (ORDER BY year))
             / NULLIF(lag(tickets) OVER (ORDER BY year), 0), 1) AS yoy_change_pct,
       round(avg(tickets) OVER (ORDER BY year ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 1) AS rolling_3y_avg
FROM y ORDER BY year;

-- name: q03_priority_mix_and_speed
SELECT priority, priority_rank, tickets, share_pct, median_resolution_hours, open_tickets
FROM analytics.v_priority_breakdown ORDER BY priority_rank DESC;

-- name: q04_resolution_by_year
SELECT member AS created_year, tickets, median_hours, mean_hours, p90_hours
FROM analytics.v_resolution_metrics
WHERE dimension = 'year' AND member BETWEEN '2016' AND '2022'
ORDER BY member;

-- name: q05_backlog_ageing
SELECT age_bucket, open_tickets, open_high_severity, share_pct, mean_age_days, max_age_days
FROM analytics.v_backlog_ageing ORDER BY age_bucket_order;

-- name: q06_oldest_open_case_per_priority
SELECT DISTINCT ON (priority) priority, ticket_id, issue_type, status, created_date, age_days
FROM analytics.v_longest_open_cases
ORDER BY priority, age_days DESC;
