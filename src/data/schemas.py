"""Expected source schemas and label vocabularies.

These are the *contracts* the loaders validate against so that an upstream
change in the public files fails loudly instead of silently corrupting analysis.
"""

from __future__ import annotations

ISSUES_REQUIRED_COLUMNS = [
    "id", "issue_num", "issue_proj", "issue_reporter", "issue_assignee", "issue_contr_count",
    "issue_type", "issue_priority", "issue_created", "issue_resolution_date", "issue_resolution",
    "issue_status", "issue_comments_count", "last_change_date", "wf_total_time", "processing_steps",
]
# Mendeley label vocabularies (as observed in v3). Anything outside is reported, not silently dropped.
PRIORITY_ORDER = ["unknown", "Lowest", "Low", "Medium", "High", "Highest", "Blocker"]
HIGH_SEVERITY_PRIORITIES = {"High", "Highest", "Blocker"}
# Work-item types that represent customer-facing helpdesk demand (vs internal delivery artefacts).
HELPDESK_ISSUE_TYPES = {"Ticket", "HD Service", "Service", "Assistance"}
INTERNAL_ISSUE_TYPES = {
    "Story", "Subtask", "Sub-task", "Task", "Epic", "Project", "Deployment", "Bug",
    "Vacation", "Retrospective", "Sprint Summary",
}
RESOLUTION_VALUES = {"Done", "Won't Do", "Duplicate", "Cannot Reproduce"}
TERMINAL_STATUSES = {"closed", "done", "cancelled", "rejected"}

# Derived requester segment bands (explicitly derived, not a source field)
REQUESTER_SEGMENT_BANDS = [(1, 1, "single"), (2, 4, "occasional"), (5, 19, "regular"), (20, 10**9, "frequent")]
