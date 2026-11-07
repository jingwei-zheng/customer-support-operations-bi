-- Grain: one row per work item. Filter is_helpdesk_ticket for customer demand.

-- ---------------------------------------------------------------- fact_ticket
DROP TABLE IF EXISTS analytics.fact_ticket CASCADE;
CREATE TABLE analytics.fact_ticket AS
SELECT
    t.ticket_id,
    t.issue_num,
    to_char(t.created_at, 'YYYYMMDD')::int                           AS created_date_key,
    to_char(t.resolved_at, 'YYYYMMDD')::int                          AS resolved_date_key,
    p.priority_key,
    it.issue_type_key,
    t.project_key,
    t.reporter_id,
    t.assignee_id,
    t.created_at, t.resolved_at, t.last_change_at, t.created_month,
    t.issue_type, t.priority, t.status, t.resolution,
    t.is_helpdesk_ticket, t.work_item_class, t.priority_known, t.is_high_severity,
    t.is_resolved, t.is_terminal_status, t.is_open_backlog, t.was_reopened, t.in_system_period,
    t.project_country_code, t.project_scope,
    t.contributor_count, t.comment_count, t.processing_steps,
    t.resolution_hours, t.resolution_days,
    t.wf_total_seconds / 3600.0                                       AS workflow_hours,
    t.wf_open_seconds / 3600.0                                        AS open_state_hours,
    t.wf_in_progress_seconds / 3600.0                                 AS in_progress_hours,
    t.wf_waiting_seconds / 3600.0                                     AS waiting_hours,
    t.wf_resolved_seconds / 3600.0                                    AS resolved_state_hours,
    t.wf_validation_seconds / 3600.0                                  AS validation_hours,
    t.wfe_reopened_count, t.wfe_waiting_count, t.wfe_in_progress_count,
    CASE WHEN t.is_open_backlog
         THEN EXTRACT(EPOCH FROM (TIMESTAMPTZ '2023-03-14 23:59:59+00' - t.created_at)) / 86400.0
    END                                                               AS age_days_at_extract,
    r.requester_segment_derived
FROM staging.tickets t
JOIN analytics.dim_priority   p  ON p.priority = t.priority
JOIN analytics.dim_issue_type it ON it.issue_type = t.issue_type
JOIN analytics.dim_reporter   r  ON r.reporter_id = t.reporter_id;

ALTER TABLE analytics.fact_ticket ADD PRIMARY KEY (ticket_id);
CREATE INDEX ON analytics.fact_ticket (created_date_key);
CREATE INDEX ON analytics.fact_ticket (is_helpdesk_ticket, created_month);
CREATE INDEX ON analytics.fact_ticket (priority_key);
CREATE INDEX ON analytics.fact_ticket (issue_type_key);
