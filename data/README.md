# Local data

I use `issues.csv` from Mendeley Data's [Help Desk Tickets v3](https://doi.org/10.17632/btm76zndnt.3), licensed CC BY 4.0.

Run `python scripts/pipeline.py data` from the repository root after installing the dependencies. This downloads the source, prepares one row per work item and runs the source-quality checks. Run the remaining pipeline steps to build PostgreSQL tables and Power BI exports.

The raw CSV, processed tickets and refresh CSVs are generated locally. Rebuild them with the pipeline to keep the transformations reproducible. Small SQL results and validation summaries are included in `reports/`. The [data source notes](../docs/data_source.md) explain attribution and reporting scope.
