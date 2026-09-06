"""
Tests for the reporting pipeline. Run with: pytest tests/

Covers: validation rule logic (duplicate/null detection, pass-through on
clean data), KPI computation (simple and grouped aggregation, including that
nulls are correctly excluded from sum), and error handling (missing column,
unsupported aggregation type) -- the core logic units, exercised directly
rather than through a full end-to-end pipeline run.
"""

import sys
import os
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))
from reporting_pipeline import validate_data, compute_kpis, PipelineError


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        'id': [1, 2, 3, 3],
        'region': ['East', 'West', 'East', 'East'],
        'amount': [100.0, 200.0, None, 150.0],
    })


@pytest.fixture
def logger():
    import logging
    log = logging.getLogger('test_logger')
    log.addHandler(logging.NullHandler())
    return log


def test_validate_data_flags_duplicates(sample_df, logger):
    config = {'validation_rules': [{'column': 'id', 'type': 'unique'}]}
    failures = validate_data(sample_df, config, logger)
    assert len(failures) == 1
    assert failures[0]['column'] == 'id'
    assert failures[0]['failing_rows'] == 2


def test_validate_data_flags_nulls(sample_df, logger):
    config = {'validation_rules': [{'column': 'amount', 'type': 'not_null'}]}
    failures = validate_data(sample_df, config, logger)
    assert len(failures) == 1
    assert failures[0]['failing_rows'] == 1


def test_validate_data_passes_when_clean(logger):
    df = pd.DataFrame({'id': [1, 2, 3]})
    config = {'validation_rules': [{'column': 'id', 'type': 'unique'}]}
    failures = validate_data(df, config, logger)
    assert failures == []


def test_compute_kpis_simple_sum(sample_df, logger):
    config = {'kpis': [{'name': 'total', 'column': 'amount', 'aggregation': 'sum'}]}
    result = compute_kpis(sample_df, config, logger)
    assert len(result) == 1
    assert result.iloc[0]['kpi_name'] == 'total'
    assert result.iloc[0]['value'] == 450.0  # nulls excluded from sum


def test_compute_kpis_grouped(sample_df, logger):
    config = {'kpis': [{'name': 'by_region', 'column': 'amount', 'aggregation': 'sum', 'group_by': 'region'}]}
    result = compute_kpis(sample_df, config, logger)
    assert len(result) == 2
    assert set(result['group_value']) == {'East', 'West'}


def test_compute_kpis_raises_on_missing_column(sample_df, logger):
    config = {'kpis': [{'name': 'bad', 'column': 'nonexistent', 'aggregation': 'sum'}]}
    with pytest.raises(PipelineError):
        compute_kpis(sample_df, config, logger)


def test_compute_kpis_unsupported_aggregation_raises(sample_df, logger):
    config = {'kpis': [{'name': 'bad_agg', 'column': 'amount', 'aggregation': 'median'}]}
    with pytest.raises(PipelineError):
        compute_kpis(sample_df, config, logger)
