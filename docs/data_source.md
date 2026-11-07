# Data source

| Item | Description |
|---|---|
| Dataset | Help Desk Tickets, version 3 |
| Contributor | Mohammad Abdellatif |
| Repository | Mendeley Data, version 3 |
| DOI | [10.17632/btm76zndnt.3](https://doi.org/10.17632/btm76zndnt.3) |
| Licence | [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/) |
| File used | `issues.csv` |
| Coverage | Historical work items from 2007 to 14 March 2023 |

Attribution: Abdellatif, Mohammad, "Help Desk Tickets", Mendeley Data, V3, doi: 10.17632/btm76zndnt.3.

I used an anonymised export from an international software company's helpdesk. Project, requester, assignee and country identifiers are masked. The findings describe that company's operation; they should not be generalised to other businesses.

## Preparation and scope

The preparation steps normalise labels, parse timestamps in UTC and check identifiers and date sequences. Derived fields identify the helpdesk population, resolution duration, severity and backlog age. These transformations and the summary exports adapt the published data for reporting.

The source contains both customer-facing and internal work items. I use `Ticket`, `Service`, `HD Service` and `Assistance` for customer-demand reporting. Service-duration measures use tickets created from 2016 because older records were migrated and bulk-closed. Unknown priorities stay visible as a data-quality issue and are excluded from known-priority percentage denominators.

## Limits

- The extract is historical, not a live source. Backlog age is measured at the extract date.
- Work-item type is a coarse administrative label, not a detailed topic taxonomy.
- Elapsed time includes weekends and time outside business hours.
- Counts and associations support investigation; they do not prove why demand or resolution times changed.

The pipeline downloads the source CSV locally. Its licence remains separate from the code's MIT licence; see [third-party notices](../THIRD_PARTY_NOTICES.md).
