# Metric definitions

I use **14 March 2023, 23:59:59 UTC** as the extract cutoff. The fact table has **one row per work item**, identified by `ticket_id`. The values below reconcile with the source records, PostgreSQL outputs and the report's imported data.

| Metric | Population and calculation | Value |
|---|---|---:|
| All work items | All fact rows, including internal work | 66,691 |
| Helpdesk tickets | Work-item type in Ticket, Service, HD Service or Assistance | 52,370 |
| Helpdesk tickets created from 2016 | Helpdesk population with creation date on or after 1 January 2016 | 34,426 |
| Full-year demand growth, 2016–2022 | `(2022 ticket count / 2016 ticket count) - 1`; compare complete creation years | 57.8% |
| Demand growth, 2016–2020 | `(4,391 / 4,013) - 1`; modest growth across four complete years | 9.4% |
| Median resolution hours | Median of resolution timestamp minus creation timestamp, in elapsed hours; resolved helpdesk tickets created from 2016 | 213.6 h |
| Median resolution days | Median resolution hours divided by 24 | 8.9 days |
| Open backlog | Helpdesk tickets without a resolution timestamp and without a terminal status at the extract | 521 |
| Aged backlog | Open backlog with age at extract of at least 30 elapsed days | 296 |
| Aged backlog share | Aged backlog divided by all open backlog | 56.8% |
| Known-priority tickets | Helpdesk tickets with a recorded priority, across all history | 23,100 |
| High-severity tickets | Helpdesk tickets with High, Highest or Blocker priority, across all history | 6,402 |
| High-severity share | High-severity tickets divided by known-priority helpdesk tickets | 27.7% |
| Open high severity | Open backlog with High, Highest or Blocker priority | 202 |
| Aged open high severity | Open high severity with age at extract of at least 30 days | 95 |
| Reopen rate | Helpdesk tickets with a recorded reopening divided by all helpdesk tickets, across all history | 1,974 / 52,370 = 3.8% |

## Date roles and filtering

Demand by month or year uses the ticket's creation date. Resolved volume by month uses its resolution date. A creation-year resolution chart describes the resolution durations of that creation cohort; it is different from a chart of cases resolved during that year.

Backlog is the state at the extract cutoff. Applying a creation-year slicer narrows that snapshot to tickets created in the selected year. It does not calculate what was open at a past month-end. Historical backlog would require an explicit reconstruction or dated snapshots.

The report's 3.8% reopen rate uses all helpdesk history. Restricting the population to tickets created from 2016 gives about 4.5%. Both calculations are valid for their stated populations; compare them only when the date scope matches.

2023 ends on 14 March and must not be compared with a complete 2022 as annual growth. Legacy records before 2016 may be counted in historical demand, but are excluded from service-duration measures because migration and bulk closure distort those durations.

## Power BI checks

- Apply `is_helpdesk_ticket = TRUE` to customer-demand and service visuals.
- Use the same date and population filters when comparing SQL and DAX results.
- Compute ratios from their underlying counts, and medians from ticket-level durations. Do not average group percentages or group medians.
- Keep unknown priority visible as a data-quality issue, even when excluding it from the known-priority denominator.
- Use fact and dimension tables for interactive visuals. Disconnected summary exports will not automatically respond to dimension slicers.
