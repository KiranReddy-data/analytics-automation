"""
Recurring reporting automation pipeline.

Simulates the kind of weekly reporting job I'd set up to eliminate repetitive
manual report preparation: pull raw extracts, validate them, compute a set of
KPIs, and write a dated output file plus a run log -- all driven by a config
file so the same script can run against different KPI definitions without
code changes.

This is intentionally a single-machine, file-based pipeline (no real
scheduler, database, or cloud service attached) -- see the README for why,
and what would change for an actual production deployment.
"""

import json
import logging
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

import pandas as pd


def setup_logger(log_path: Path) -> logging.Logger:
    logger = logging.getLogger('reporting_pipeline')
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


@dataclass
class PipelineResult:
    run_timestamp: str
    input_rows: int
    validation_passed: bool
    validation_failures: list
    kpis_computed: int
    output_file: str
    status: str


class PipelineError(Exception):
    """Raised when a pipeline stage fails in a way that should halt the run."""
    pass


def load_config(config_path: Path) -> dict:
    with open(config_path) as f:
        return json.load(f)


def load_data(input_path: Path, logger: logging.Logger) -> pd.DataFrame:
    logger.info(f"Loading data from {input_path}")
    if not input_path.exists():
        raise PipelineError(f"Input file not found: {input_path}")
    df = pd.read_csv(input_path)
    logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns")
    return df


def validate_data(df: pd.DataFrame, config: dict, logger: logging.Logger) -> list:
    """Runs the validation rules defined in config['validation_rules'].
    Returns a list of failure dicts; an empty list means all checks passed."""
    failures = []
    for rule in config.get('validation_rules', []):
        col = rule['column']
        rule_type = rule['type']

        if rule_type == 'not_null':
            bad = df[df[col].isna()]
        elif rule_type == 'unique':
            counts = df[col].value_counts()
            bad_values = counts[counts > 1].index
            bad = df[df[col].isin(bad_values)]
        elif rule_type == 'in_range':
            bad = df[(df[col] < rule['min']) | (df[col] > rule['max'])]
        else:
            logger.warning(f"Unknown rule type '{rule_type}' for column '{col}', skipping")
            continue

        if len(bad) > 0:
            failures.append({'column': col, 'rule': rule_type, 'failing_rows': len(bad)})
            logger.warning(f"Validation failed: {col} / {rule_type} -- {len(bad)} rows flagged")
        else:
            logger.info(f"Validation passed: {col} / {rule_type}")

    return failures


def compute_kpis(df: pd.DataFrame, config: dict, logger: logging.Logger) -> pd.DataFrame:
    """Computes each KPI defined in config['kpis']. Supported aggregation
    types are intentionally limited to keep the config format simple --
    see README for how this would be extended."""
    results = []
    for kpi in config.get('kpis', []):
        name = kpi['name']
        group_by = kpi.get('group_by')
        agg_col = kpi['column']
        agg_type = kpi['aggregation']

        try:
            if group_by:
                grouped = df.groupby(group_by)[agg_col]
                if agg_type == 'sum':
                    values = grouped.sum()
                elif agg_type == 'mean':
                    values = grouped.mean()
                elif agg_type == 'count':
                    values = grouped.count()
                else:
                    raise PipelineError(f"Unsupported aggregation: {agg_type}")

                for group_val, kpi_val in values.items():
                    results.append({
                        'kpi_name': name, 'group_by': group_by,
                        'group_value': group_val, 'value': round(kpi_val, 2)
                    })
            else:
                if agg_type == 'sum':
                    value = df[agg_col].sum()
                elif agg_type == 'mean':
                    value = df[agg_col].mean()
                elif agg_type == 'count':
                    value = df[agg_col].count()
                else:
                    raise PipelineError(f"Unsupported aggregation: {agg_type}")

                results.append({
                    'kpi_name': name, 'group_by': None,
                    'group_value': None, 'value': round(value, 2)
                })
            logger.info(f"Computed KPI: {name}")
        except KeyError as e:
            logger.error(f"KPI '{name}' failed -- missing column {e}")
            raise PipelineError(f"KPI computation failed for '{name}': missing column {e}")

    return pd.DataFrame(results)


def run_pipeline(config_path: str, input_path: str, output_dir: str) -> PipelineResult:
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    run_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = output_dir_path / f'pipeline_run_{run_timestamp}.log'
    logger = setup_logger(log_path)

    logger.info("=== Pipeline run started ===")

    try:
        config = load_config(Path(config_path))
        df = load_data(Path(input_path), logger)

        failures = validate_data(df, config, logger)
        validation_passed = len(failures) == 0

        if not validation_passed and config.get('halt_on_validation_failure', False):
            raise PipelineError(f"Validation failed with {len(failures)} rule(s) flagged; halting per config")

        kpi_df = compute_kpis(df, config, logger)

        output_file = output_dir_path / f'kpi_report_{run_timestamp}.csv'
        kpi_df.to_csv(output_file, index=False)
        logger.info(f"KPI report written to {output_file}")

        result = PipelineResult(
            run_timestamp=run_timestamp,
            input_rows=len(df),
            validation_passed=validation_passed,
            validation_failures=failures,
            kpis_computed=len(kpi_df),
            output_file=str(output_file),
            status='SUCCESS',
        )

    except PipelineError as e:
        logger.error(f"Pipeline halted: {e}")
        result = PipelineResult(
            run_timestamp=run_timestamp, input_rows=0, validation_passed=False,
            validation_failures=[{'error': str(e)}], kpis_computed=0,
            output_file='', status='FAILED',
        )

    logger.info(f"=== Pipeline run finished: {result.status} ===")

    result_path = output_dir_path / f'run_result_{run_timestamp}.json'
    with open(result_path, 'w') as f:
        json.dump(asdict(result), f, indent=2)

    return result


if __name__ == '__main__':
    result = run_pipeline(
        config_path='../config/pipeline_config.json',
        input_path='../data/raw/transactions.csv',
        output_dir='../data/processed',
    )
    print(f"\nPipeline finished with status: {result.status}")
    print(f"KPIs computed: {result.kpis_computed}")
    print(f"Validation passed: {result.validation_passed}")
