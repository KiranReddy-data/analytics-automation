"""
Generates the synthetic transactions dataset used by this project.
Run this once before running reporting_pipeline.py or the SQL queries.

python generate_data.py
"""

import numpy as np
import pandas as pd
from pathlib import Path

np.random.seed(88)


def generate_transactions(n: int = 3000) -> pd.DataFrame:
    df = pd.DataFrame({
        'transaction_id': [f"T{i:06d}" for i in range(n)],
        'region': np.random.choice(['Northeast', 'South', 'Midwest', 'West'], n),
        'product_category': np.random.choice(['Hardware', 'Software', 'Services', 'Support'], n),
        'amount': np.round(np.random.lognormal(5, 1, n), 2),
        'transaction_date': (
            pd.to_datetime('2025-01-01') + pd.to_timedelta(np.random.randint(0, 240, n), unit='D')
        ).astype(str),
    })

    null_idx = np.random.choice(n, 15, replace=False)
    df.loc[null_idx, 'amount'] = np.nan

    dup_idx = np.random.choice(n, 10, replace=False)
    df = pd.concat([df, df.iloc[dup_idx]], ignore_index=True)

    return df


if __name__ == '__main__':
    output_path = Path('../data/raw/transactions.csv')
    output_path.parent.mkdir(parents=True, exist_ok=True)

    transactions = generate_transactions()
    transactions.to_csv(output_path, index=False)
    print(f"Generated {len(transactions)} rows -> {output_path}")
