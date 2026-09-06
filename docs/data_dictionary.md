# Data Dictionary -- Analytics Automation

## transactions.csv

| Column | Type | Description |
|---|---|---|
| transaction_id | string | Unique transaction identifier (a small number are duplicated -- see validation) |
| region | string | Northeast, South, Midwest, West |
| product_category | string | Hardware, Software, Services, Support |
| amount | float | Transaction amount (a small number are null -- see validation) |
| transaction_date | string | Transaction date (ISO format) |

Fully synthetic, generated in Python with NumPy/Pandas. No real transaction
or company data is used or referenced.

## Known data quality issues (intentionally present, used to test the pipeline's validation stage)

- 20 duplicate transaction_id records
- 15 missing amount values

## Config schema (config/pipeline_config.json)

| Field | Type | Description |
|---|---|---|
| halt_on_validation_failure | bool | If true, a failed validation rule stops the pipeline before KPI computation |
| validation_rules | array | List of `{column, type}` objects; type is one of `not_null`, `unique`, `in_range` (requires `min`/`max`) |
| kpis | array | List of `{name, column, aggregation}` objects; aggregation is one of `sum`, `mean`, `count`; optional `group_by` for a grouped KPI |
