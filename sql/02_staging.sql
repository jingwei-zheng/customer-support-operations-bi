-- 02: staging layer. Types, trims and standardises the raw text columns and adds the same
-- transparent derived flags that src/data/clean.py derives in Python (validation compares Python and SQL output).

-- ---------------------------------------------------------------- tickets
DROP TABLE IF EXISTS staging.tickets CASCADE;
CREATE TABLE staging.tickets AS
WITH typed AS (
    SELECT
        (id::numeric)::bigint                                          AS ticket_id,
        (issue_num::numeric)::int                                      AS issue_num,
        COALESCE(NULLIF(btrim(issue_proj), ''), 'unknown')             AS project_key,
        COALESCE(NULLIF(btrim(issue_reporter), ''), 'unknown')         AS reporter_id,
        COALESCE(NULLIF(btrim(issue_assignee), ''), 'unassigned')      AS assignee_id,
        COALESCE((issue_contr_count::numeric)::int, 0)                 AS contributor_count,
        COALESCE(NULLIF(regexp_replace(btrim(issue_type), '\s+', ' ', 'g'), ''), 'unknown') AS issue_type,
        COALESCE(NULLIF(btrim(issue_priority), ''), 'unknown')         AS priority,
        issue_created::timestamptz                                     AS created_at,
        NULLIF(issue_resolution_date, '')::timestamptz                 AS resolved_at,
        NULLIF(last_change_date, '')::timestamptz                      AS last_change_at,
        COALESCE(NULLIF(btrim(issue_resolution), ''), 'unresolved')    AS resolution,
        lower(COALESCE(NULLIF(btrim(issue_status), ''), 'unknown'))    AS status,
        COALESCE((issue_comments_count::numeric)::int, 0)              AS comment_count,
        NULLIF(wf_total_time, '')::numeric                             AS wf_total_seconds,
        (processing_steps::numeric)::int                               AS processing_steps,
        NULLIF(wf_open, '')::numeric                                   AS wf_open_seconds,
        NULLIF(wf_in_progress, '')::numeric                            AS wf_in_progress_seconds,
        NULLIF(wf_waiting, '')::numeric                                AS wf_waiting_seconds,
        NULLIF(wf_resolved, '')::numeric                               AS wf_resolved_seconds,
        NULLIF(wf_validation, '')::numeric                             AS wf_validation_seconds,
        COALESCE((wfe_reopened::numeric)::int, 0)                      AS wfe_reopened_count,
        COALESCE((wfe_waiting::numeric)::int, 0)                       AS wfe_waiting_count,
        COALESCE((wfe_in_progress::numeric)::int, 0)                   AS wfe_in_progress_count
    FROM raw.issues
    WHERE id IS NOT NULL
)
SELECT
    t.*,
    t.issue_type IN ('Ticket', 'HD Service', 'Service', 'Assistance')  AS is_helpdesk_ticket,
    CASE WHEN t.issue_type IN ('Ticket', 'HD Service', 'Service', 'Assistance')
         THEN 'helpdesk' ELSE 'internal' END                          AS work_item_class,
    t.priority <> 'unknown'                                            AS priority_known,
    t.priority IN ('High', 'Highest', 'Blocker')                       AS is_high_severity,
    t.resolved_at IS NOT NULL                                          AS is_resolved,
    t.status IN ('closed', 'done', 'cancelled', 'rejected')            AS is_terminal_status,
    (t.resolved_at IS NULL AND t.status NOT IN ('closed', 'done', 'cancelled', 'rejected')) AS is_open_backlog,
    EXTRACT(EPOCH FROM (t.resolved_at - t.created_at)) / 3600.0        AS resolution_hours,
    EXTRACT(EPOCH FROM (t.resolved_at - t.created_at)) / 86400.0       AS resolution_days,
    t.wfe_reopened_count > 0                                           AS was_reopened,
    CASE WHEN length(t.project_key) >= 7 AND t.project_key ~ '^C[0-9]{2}'
         THEN substr(t.project_key, 1, 3) ELSE 'internal' END          AS project_country_code,
    CASE WHEN length(t.project_key) >= 7 AND t.project_key ~ '^C[0-9]{2}'
         THEN 'external' ELSE 'internal' END                           AS project_scope,
    t.created_at >= TIMESTAMPTZ '2016-01-01'                           AS in_system_period,
    to_char(t.created_at, 'YYYY-MM')                                   AS created_month
FROM typed t;

CREATE UNIQUE INDEX ON staging.tickets (ticket_id);
CREATE INDEX ON staging.tickets (created_at);
CREATE INDEX ON staging.tickets (issue_type, priority);
