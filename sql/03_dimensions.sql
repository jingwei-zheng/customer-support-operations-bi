-- 03: dimensions. Only dimensions supported by the source are built. The requester segment is an
-- explicitly DERIVED analytical segment (reporter ticket-count band), not a source attribute.

-- ---------------------------------------------------------------- date
DROP TABLE IF EXISTS analytics.dim_date CASCADE;
CREATE TABLE analytics.dim_date AS
SELECT
    to_char(d, 'YYYYMMDD')::int          AS date_key,
    d::date                              AS full_date,
    EXTRACT(YEAR FROM d)::int            AS year,
    EXTRACT(QUARTER FROM d)::int         AS quarter,
    EXTRACT(MONTH FROM d)::int           AS month,
    to_char(d, 'Mon')                    AS month_name,
    to_char(d, 'YYYY-MM')                AS year_month,
    to_char(d, 'YYYY') || '-Q' || EXTRACT(QUARTER FROM d)::int AS year_quarter,
    EXTRACT(ISODOW FROM d)::int          AS iso_day_of_week,
    to_char(d, 'Dy')                     AS day_name,
    EXTRACT(ISODOW FROM d) >= 6          AS is_weekend,
    EXTRACT(WEEK FROM d)::int            AS iso_week
FROM generate_series(DATE '2007-01-01', DATE '2023-12-31', INTERVAL '1 day') AS d;
ALTER TABLE analytics.dim_date ADD PRIMARY KEY (date_key);

-- ---------------------------------------------------------------- priority
DROP TABLE IF EXISTS analytics.dim_priority CASCADE;
CREATE TABLE analytics.dim_priority (
    priority_key     SMALLINT PRIMARY KEY,
    priority         TEXT NOT NULL UNIQUE,
    priority_rank    SMALLINT NOT NULL,
    is_known         BOOLEAN NOT NULL,
    is_high_severity BOOLEAN NOT NULL
);
INSERT INTO analytics.dim_priority VALUES
    (0, 'unknown', 0, FALSE, FALSE),
    (1, 'Lowest',  1, TRUE,  FALSE),
    (2, 'Low',     2, TRUE,  FALSE),
    (3, 'Medium',  3, TRUE,  FALSE),
    (4, 'High',    4, TRUE,  TRUE),
    (5, 'Highest', 5, TRUE,  TRUE),
    (6, 'Blocker', 6, TRUE,  TRUE);

-- ---------------------------------------------------------------- issue type (work-item type)
DROP TABLE IF EXISTS analytics.dim_issue_type CASCADE;
CREATE TABLE analytics.dim_issue_type AS
SELECT row_number() OVER (ORDER BY is_helpdesk_ticket DESC, n DESC) AS issue_type_key,
       issue_type, work_item_class, is_helpdesk_ticket, n AS ticket_count
FROM (
    SELECT issue_type, work_item_class, is_helpdesk_ticket, count(*) AS n
    FROM staging.tickets GROUP BY 1, 2, 3
) s;
ALTER TABLE analytics.dim_issue_type ADD PRIMARY KEY (issue_type_key);
CREATE UNIQUE INDEX ON analytics.dim_issue_type (issue_type);

-- ---------------------------------------------------------------- project (product/client key; masked)
DROP TABLE IF EXISTS analytics.dim_project CASCADE;
CREATE TABLE analytics.dim_project AS
SELECT project_key,
       project_country_code,
       project_scope,
       count(*)                                        AS ticket_count,
       count(*) FILTER (WHERE is_helpdesk_ticket)      AS helpdesk_ticket_count,
       min(created_at)                                 AS first_ticket_at,
       max(created_at)                                 AS last_ticket_at,
       count(DISTINCT reporter_id)                     AS distinct_reporters
FROM staging.tickets GROUP BY 1, 2, 3;
ALTER TABLE analytics.dim_project ADD PRIMARY KEY (project_key);

-- ---------------------------------------------------------------- reporter (requester) with DERIVED segment
DROP TABLE IF EXISTS analytics.dim_reporter CASCADE;
CREATE TABLE analytics.dim_reporter AS
SELECT reporter_id,
       count(*)                                   AS ticket_count,
       count(*) FILTER (WHERE is_helpdesk_ticket) AS helpdesk_ticket_count,
       count(DISTINCT project_key)                AS distinct_projects,
       min(created_at)                            AS first_ticket_at,
       max(created_at)                            AS last_ticket_at,
       CASE WHEN count(*) = 1 THEN 'single'
            WHEN count(*) BETWEEN 2 AND 4 THEN 'occasional'
            WHEN count(*) BETWEEN 5 AND 19 THEN 'regular'
            ELSE 'frequent' END                   AS requester_segment_derived
FROM staging.tickets GROUP BY 1;
ALTER TABLE analytics.dim_reporter ADD PRIMARY KEY (reporter_id);
