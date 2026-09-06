-- SQL equivalent of the KPI and validation logic in python/reporting_pipeline.py.
-- Useful when the same reporting logic needs to run inside a warehouse rather
-- than a Python process (e.g., as a scheduled query or stored procedure).

-- Validation: transaction_id uniqueness
SELECT transaction_id, COUNT(*) AS occurrences
FROM transactions
GROUP BY transaction_id
HAVING COUNT(*) > 1;

-- Validation: missing amount
SELECT transaction_id
FROM transactions
WHERE amount IS NULL;

-- Validation: amount out of expected range
SELECT transaction_id, amount
FROM transactions
WHERE amount < 0 OR amount > 100000;

-- KPI: total revenue, average transaction value, transaction count
SELECT
    ROUND(SUM(amount), 2) AS total_revenue,
    ROUND(AVG(amount), 2) AS avg_transaction_value,
    COUNT(*) AS transaction_count
FROM transactions
WHERE amount IS NOT NULL;

-- KPI: revenue by region
SELECT
    region,
    ROUND(SUM(amount), 2) AS revenue
FROM transactions
WHERE amount IS NOT NULL
GROUP BY region
ORDER BY revenue DESC;

-- KPI: revenue by product category
SELECT
    product_category,
    ROUND(SUM(amount), 2) AS revenue
FROM transactions
WHERE amount IS NOT NULL
GROUP BY product_category
ORDER BY revenue DESC;
