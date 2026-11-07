-- Validation checks for the Executive Overview.
-- Dialect: PostgreSQL; warehouse relation: analytics.fact_ticket.
-- Baselines verified on 1 Nov 2026 against dashboard/exports/fact_tickets.csv.
-- Verification engine: SQLite over typed exported rows; PostgreSQL's percentile_cont
-- expression was evaluated with an equivalent Python statistics.median aggregate.
-- Re-run against PostgreSQL 18 on 6 Nov 2026: 13 of 13 match (reports/powerbi_validation.json).
-- SQL results are fixed baseline snapshots; Power BI values are live DAX measures.
-- Percentage values use percentage points, e.g. 27.7 rather than 0.277.
-- Resolution uses the system period; the overview reopen card intentionally uses all years.

-- 01. All work items, before the helpdesk filter
-- Baseline: 66,691.0
SELECT count(*)
FROM analytics.fact_ticket;

-- 02. Helpdesk tickets (Tickets card)
-- Baseline: 52,370.0
SELECT count(*)
FROM analytics.fact_ticket
WHERE is_helpdesk_ticket;

-- 03. Open backlog
-- Baseline: 521.0
SELECT count(*)
FROM analytics.fact_ticket
WHERE is_helpdesk_ticket AND is_open_backlog;

-- 04. Median resolution, hours (card = hours / 24)
-- Baseline: 213.6
SELECT round(percentile_cont(0.5) WITHIN GROUP (ORDER BY resolution_hours)::numeric, 1)
FROM analytics.fact_ticket
WHERE is_helpdesk_ticket AND is_resolved AND in_system_period;

-- 05. High-severity share of recorded priorities %
-- Baseline: 27.7
SELECT round(100.0 * count(*) FILTER (WHERE is_high_severity) / NULLIF(count(*) FILTER (WHERE priority_known), 0), 1)
FROM analytics.fact_ticket
WHERE is_helpdesk_ticket;

-- 06. Reopen rate %, all years (as on the card)
-- Baseline: 3.8
SELECT round(100.0 * count(*) FILTER (WHERE was_reopened) / NULLIF(count(*), 0), 1)
FROM analytics.fact_ticket
WHERE is_helpdesk_ticket;

-- 07. Reopen rate %, 2016 onward (repo SQL summary)
-- Baseline: 4.5
SELECT round(100.0 * count(*) FILTER (WHERE was_reopened) / NULLIF(count(*), 0), 1)
FROM analytics.fact_ticket
WHERE is_helpdesk_ticket AND in_system_period;

-- 08. Tickets 2022 vs 2021 %
-- Baseline: 18.2
SELECT round(100.0 * (count(*) FILTER (WHERE created_month BETWEEN '2022-01' AND '2022-12') - count(*) FILTER (WHERE created_month BETWEEN '2021-01' AND '2021-12')) / NULLIF(count(*) FILTER (WHERE created_month BETWEEN '2021-01' AND '2021-12'), 0), 1)
FROM analytics.fact_ticket
WHERE is_helpdesk_ticket;

-- 09. 'Ticket' share of demand %
-- Baseline: 86.5
SELECT round(100.0 * count(*) FILTER (WHERE issue_type = 'Ticket') / NULLIF(count(*), 0), 1)
FROM analytics.fact_ticket
WHERE is_helpdesk_ticket;

-- 10. Medium share of recorded priorities %
-- Baseline: 70.2
SELECT round(100.0 * count(*) FILTER (WHERE priority = 'Medium') / NULLIF(count(*), 0), 1)
FROM analytics.fact_ticket
WHERE is_helpdesk_ticket AND priority_known;

-- 11. Growth 2016 to 2022 % (typed as +58%)
-- Baseline: 57.8
SELECT round(100.0 * (1.0 * count(*) FILTER (WHERE created_month BETWEEN '2022-01' AND '2022-12') / NULLIF(count(*) FILTER (WHERE created_month BETWEEN '2016-01' AND '2016-12'), 0) - 1), 1)
FROM analytics.fact_ticket
WHERE is_helpdesk_ticket;

-- 12. Growth 2016 to 2020 % (modest growth)
-- Baseline: 9.4
SELECT round(100.0 * (1.0 * count(*) FILTER (WHERE created_month BETWEEN '2020-01' AND '2020-12') / NULLIF(count(*) FILTER (WHERE created_month BETWEEN '2016-01' AND '2016-12'), 0) - 1), 1)
FROM analytics.fact_ticket
WHERE is_helpdesk_ticket;

-- 13. Open tickets at least 30 days old % (shown as 57%)
-- Baseline: 56.8
SELECT round(100.0 * count(*) FILTER (WHERE age_days_at_extract >= 30) / NULLIF(count(*), 0), 1)
FROM analytics.fact_ticket
WHERE is_helpdesk_ticket AND is_open_backlog;
