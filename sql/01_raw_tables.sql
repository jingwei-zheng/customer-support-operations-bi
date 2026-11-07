-- 01: raw landing tables. Every column is TEXT on purpose: raw stores the public files exactly as
-- received; all typing/cleaning happens in 02_staging.sql so the transformation is auditable.

DROP TABLE IF EXISTS raw.issues CASCADE;
CREATE TABLE raw.issues (
    raw_row_id BIGSERIAL PRIMARY KEY,
    id TEXT, started TEXT, ended TEXT, issue_num TEXT, issue_proj TEXT, issue_reporter TEXT,
    issue_assignee TEXT, issue_contr_count TEXT, issue_type TEXT, issue_priority TEXT,
    issue_created TEXT, issue_resolution_date TEXT, issue_resolution TEXT, issue_status TEXT,
    issue_comments_count TEXT, last_change_date TEXT,
    wf_in_review TEXT, wfe_in_review TEXT, wf_deployment TEXT, wfe_deployment TEXT,
    wf_resolved TEXT, wfe_resolved TEXT, wf_open TEXT, wfe_open TEXT,
    wf_monitoring TEXT, wfe_monitoring TEXT, wf_done TEXT, wfe_done TEXT,
    wf_pending_customer_approval TEXT, wfe_pending_customer_approval TEXT,
    wf_rejected TEXT, wfe_rejected TEXT, wf_testing_monitoring TEXT, wfe_testing_monitoring TEXT,
    wf_in_progress TEXT, wfe_in_progress TEXT, wf_reopened TEXT, wfe_reopened TEXT,
    wf_to_do TEXT, wfe_to_do TEXT, wf_validation TEXT, wfe_validation TEXT,
    wf_resolved_under_monitoring TEXT, wfe_resolved_under_monitoring TEXT,
    wf_closed TEXT, wfe_closed TEXT, wf_waiting TEXT, wfe_waiting TEXT,
    wf_cancelled TEXT, wfe_cancelled TEXT, wf_under_review TEXT, wfe_under_review TEXT,
    wf_approved TEXT, wfe_approved TEXT, wf_pending_deployment TEXT, wfe_pending_deployment TEXT,
    wf_total_time TEXT, processing_steps TEXT
);
