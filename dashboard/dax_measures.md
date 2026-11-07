# DAX measures

I use these 17 measures in `customer_support_operations.pbix`. They belong to `_Measures`. The first 13 drive the overview; the final four compare report values with the validation baselines. The Validation page has 13 checks; a check can combine several measures, so the check count and measure count are different.

`Tickets` counts fact rows in the current filter context. I apply `fact_tickets[is_helpdesk_ticket] = TRUE` at report level, so the overview uses customer-support tickets. Dates filter through the active creation-date relationship.

```dax
Tickets =
COUNTROWS ( fact_tickets )
```

```dax
Open Backlog =
CALCULATE ( [Tickets], fact_tickets[is_open_backlog] = TRUE () )
```

```dax
High Severity Tickets =
CALCULATE ( [Tickets], fact_tickets[is_high_severity] = TRUE () )
```

```dax
Tickets With Known Priority =
CALCULATE ( [Tickets], fact_tickets[priority_known] = TRUE () )
```

```dax
Reopened Tickets =
CALCULATE ( [Tickets], fact_tickets[was_reopened] = TRUE () )
```

```dax
Reopen Rate % =
DIVIDE ( [Reopened Tickets], [Tickets] )
```

```dax
High Severity Share % =
DIVIDE ( [High Severity Tickets], [Tickets With Known Priority] )
```

```dax
Median Resolution Hours =
CALCULATE ( MEDIAN ( fact_tickets[resolution_hours] ), fact_tickets[is_resolved] = TRUE (), fact_tickets[in_system_period] = TRUE () )
```

```dax
Median Resolution Days =
DIVIDE ( [Median Resolution Hours], 24 )
```

```dax
Tickets PY =
CALCULATE ( [Tickets], SAMEPERIODLASTYEAR ( dim_date[full_date] ) )
```

```dax
Tickets YoY % =
DIVIDE ( [Tickets] - [Tickets PY], [Tickets PY] )
```

```dax
Tickets Rolling 12M =
VAR EndDate = MAX ( dim_date[full_date] )
RETURN
    CALCULATE ( [Tickets], DATESINPERIOD ( dim_date[full_date], EndDate, -12, MONTH ) ) / 12
```

```dax
Share of Tickets % =
DIVIDE ( [Tickets], CALCULATE ( [Tickets], ALLSELECTED ( dim_issue_type ), ALLSELECTED ( dim_priority ) ) )
```

```dax
Power BI Value =
VAR CheckId = SELECTEDVALUE ( validation_checks[check_id] )
VAR RawValue =
    SWITCH (
        CheckId,
        1,  CALCULATE ( [Tickets], REMOVEFILTERS ( fact_tickets[is_helpdesk_ticket] ) ),
        2,  [Tickets],
        3,  [Open Backlog],
        4,  [Median Resolution Hours],
        5,  [High Severity Share %] * 100,
        6,  [Reopen Rate %] * 100,
        7,  CALCULATE ( [Reopen Rate %], fact_tickets[in_system_period] = TRUE () ) * 100,
        8,  CALCULATE ( [Tickets YoY %], dim_date[year] = 2022 ) * 100,
        9,  DIVIDE ( CALCULATE ( [Tickets], dim_issue_type[issue_type] = "Ticket" ), [Tickets] ) * 100,
        10, DIVIDE ( CALCULATE ( [Tickets], dim_priority[priority] = "Medium" ), [Tickets With Known Priority] ) * 100,
        11, ( DIVIDE ( CALCULATE ( [Tickets], dim_date[year] = 2022 ), CALCULATE ( [Tickets], dim_date[year] = 2016 ) ) - 1 ) * 100,
        12, ( DIVIDE ( CALCULATE ( [Tickets], dim_date[year] = 2020 ), CALCULATE ( [Tickets], dim_date[year] = 2016 ) ) - 1 ) * 100,
        13, DIVIDE ( CALCULATE ( [Open Backlog], fact_tickets[age_days_at_extract] >= 30 ), [Open Backlog] ) * 100
    )
RETURN
    ROUND ( RawValue, 1 )
```

```dax
Check Status =
VAR SqlValue = SELECTEDVALUE ( validation_checks[sql_result] )
VAR PbiValue = [Power BI Value]
RETURN
    IF (
        ISBLANK ( SqlValue ),
        BLANK (),
        IF ( NOT ISBLANK ( PbiValue ) && ABS ( PbiValue - SqlValue ) < 0.05, "✓ Match", "✗ Mismatch" )
    )
```

```dax
Checks Passed =
VAR Passed = COUNTROWS ( FILTER ( validation_checks, [Check Status] = "✓ Match" ) )
RETURN
    COALESCE ( Passed, 0 ) & " of " & COUNTROWS ( validation_checks ) & " checks match"
```

```dax
Status Colour =
IF ( [Check Status] = "✓ Match", "#16A34A", "#DC2626" )
```

## Definitions and checks

- **Reopen rate:** 1,974 reopened helpdesk tickets / 52,370 tickets across all history = 3.7693%, displayed as **3.8%**. Restricting both counts to tickets created from 2016 gives **4.5%**. The validation page checks both definitions.
- **Median resolution:** resolved helpdesk tickets created from 2016; the imported fact gives 213.64 elapsed hours, or 8.9 days. The date filter selects a creation cohort.
- **High-severity share:** High, Highest or Blocker tickets divided by tickets with recorded priority; the unfiltered helpdesk reference is 6,402 / 23,100 = 27.7%.
- **Open backlog:** cases still open at 14 March 2023. Filtering their creation year does not reconstruct backlog in that year.
- **Year-on-year card:** I filter the overview card to 2022, comparing it with 2021. The measure itself is generic.
- **Rolling average:** a trailing 12-month ticket count divided by 12. Its period ends at the maximum date in the visual's date context.
- **Validation values:** `Power BI Value` selects a calculation by `check_id` and rounds it to one decimal place. `Check Status` compares it with the stored baseline using a tolerance below 0.05.

`validation_checks` is a disconnected baseline table, embedded in the report rather than queried live from PostgreSQL. I check it at the unfiltered helpdesk scope; further report filters can change the live values while the baselines stay fixed.

The model has no resolved-date relationship or resolved-in-period measure. The extra `is_backlog_30_plus`, `backlog_age_bucket` and `backlog_age_bucket_order` export fields support further analysis; these measures do not use them.
