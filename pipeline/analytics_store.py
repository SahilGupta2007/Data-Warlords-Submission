"""
Analytics Store & Metrics Engine - TransOrg AgentIQ Datathon (Track 1)
Author: Team Antigravity
Description:
    Builds the governed analytical layer:
    - DuckDB In-Memory / File-backed Warehouse
    - Star-Schema Dimensional Model (dim_users, dim_merchants, fct_transactions, fct_chargebacks)
    - Business Views (Merchant Risk Scorecards, Category Performance, Daily KPI Trends, User Risk Profiles)
"""

import os
import sys
import duckdb
import pandas as pd
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DATA_DIR = os.path.join(BASE_DIR, "data", "processed")
DB_PATH = os.path.join(PROCESSED_DATA_DIR, "fintech_warehouse.duckdb")

def build_analytics_warehouse():
    """Initializes DuckDB database and populates analytical views."""
    print("\n--- Building Analytics Data Warehouse (DuckDB) ---")
    con = duckdb.connect(DB_PATH)
    
    # Load processed parquet datasets into base tables
    txn_path = os.path.join(PROCESSED_DATA_DIR, "clean_transactions.parquet").replace("\\", "/")
    merchants_path = os.path.join(PROCESSED_DATA_DIR, "clean_merchants.parquet").replace("\\", "/")
    kyc_path = os.path.join(PROCESSED_DATA_DIR, "clean_kyc.parquet").replace("\\", "/")
    cb_path = os.path.join(PROCESSED_DATA_DIR, "clean_chargebacks.parquet").replace("\\", "/")
    
    con.execute(f"CREATE OR REPLACE TABLE fct_transactions AS SELECT * FROM read_parquet('{txn_path}')")
    con.execute(f"CREATE OR REPLACE TABLE dim_merchants AS SELECT * FROM read_parquet('{merchants_path}')")
    con.execute(f"CREATE OR REPLACE TABLE dim_users AS SELECT * FROM read_parquet('{kyc_path}')")
    con.execute(f"CREATE OR REPLACE TABLE fct_chargebacks AS SELECT * FROM read_parquet('{cb_path}')")
    
    print("[OK] Base tables loaded: fct_transactions, dim_merchants, dim_users, fct_chargebacks")
    
    # 1. View: Daily Transaction Trends
    con.execute("""
    CREATE OR REPLACE VIEW v_daily_trends AS
    SELECT 
        CAST(timestamp AS DATE) AS txn_date,
        COUNT(*) AS total_txns,
        COUNT(CASE WHEN status = 'SUCCESS' THEN 1 END) AS successful_txns,
        COUNT(CASE WHEN status = 'FAILED' THEN 1 END) AS failed_txns,
        COUNT(CASE WHEN status = 'PENDING' THEN 1 END) AS pending_txns,
        ROUND(SUM(amount), 2) AS total_amount,
        ROUND(SUM(CASE WHEN status = 'SUCCESS' THEN amount ELSE 0 END), 2) AS successful_amount,
        ROUND(AVG(amount), 2) AS avg_ticket_size,
        ROUND(COUNT(CASE WHEN status = 'FAILED' THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 2) AS failure_rate_pct
    FROM fct_transactions
    WHERE timestamp IS NOT NULL
    GROUP BY 1
    ORDER BY 1
    """)
    print("[OK] View created: v_daily_trends")
    
    # 2. View: Merchant Category Performance & Dispute Ratios
    con.execute("""
    CREATE OR REPLACE VIEW v_category_summary AS
    WITH txn_summary AS (
        SELECT 
            COALESCE(m.merchant_category, 'Unknown Category') AS category,
            COUNT(t.txn_id) AS total_txns,
            SUM(t.amount) AS total_volume,
            AVG(t.amount) AS avg_txn_value,
            COUNT(CASE WHEN t.status = 'FAILED' THEN 1 END) AS failed_txns
        FROM fct_transactions t
        LEFT JOIN dim_merchants m ON t.merchant_id = m.merchant_id
        GROUP BY 1
    ),
    cb_summary AS (
        SELECT 
            COALESCE(m.merchant_category, 'Unknown Category') AS category,
            COUNT(c.complaint_id) AS total_chargebacks,
            SUM(c.disputed_amount) AS total_disputed_amount,
            AVG(c.reporting_delay_days) AS avg_reporting_delay
        FROM fct_chargebacks c
        LEFT JOIN dim_merchants m ON c.merchant_id = m.merchant_id
        GROUP BY 1
    )
    SELECT 
        t.category,
        t.total_txns,
        ROUND(t.total_volume, 2) AS total_volume,
        ROUND(t.avg_txn_value, 2) AS avg_txn_value,
        COALESCE(c.total_chargebacks, 0) AS chargeback_count,
        ROUND(COALESCE(c.total_disputed_amount, 0), 2) AS disputed_amount,
        ROUND(COALESCE(c.total_disputed_amount, 0) * 100.0 / NULLIF(t.total_volume, 0), 3) AS chargeback_to_volume_ratio_pct,
        ROUND(COALESCE(c.total_chargebacks, 0) * 100.0 / NULLIF(t.total_txns, 0), 3) AS dispute_frequency_pct,
        ROUND(COALESCE(c.avg_reporting_delay, 0), 1) AS avg_dispute_delay_days
    FROM txn_summary t
    LEFT JOIN cb_summary c ON t.category = c.category
    ORDER BY disputed_amount DESC
    """)
    print("[OK] View created: v_category_summary")
    
    # 3. View: Merchant Risk Scorecard
    con.execute("""
    CREATE OR REPLACE VIEW v_merchant_risk_scorecard AS
    WITH m_txns AS (
        SELECT 
            merchant_id,
            COUNT(*) AS total_txns,
            SUM(amount) AS total_volume,
            AVG(amount) AS actual_avg_ticket,
            COUNT(CASE WHEN status = 'FAILED' THEN 1 END) AS failed_txns,
            COUNT(CASE WHEN is_missing_utr THEN 1 END) AS missing_utr_txns
        FROM fct_transactions
        GROUP BY 1
    ),
    m_cbks AS (
        SELECT 
            merchant_id,
            COUNT(*) AS cb_count,
            SUM(disputed_amount) AS total_disputed,
            AVG(reporting_delay_days) AS avg_delay
        FROM fct_chargebacks
        GROUP BY 1
    )
    SELECT 
        m.merchant_id,
        m.merchant_name,
        m.merchant_category,
        m.business_type,
        m.city,
        m.state,
        m.merchant_status,
        m.declared_avg_ticket_size,
        COALESCE(t.total_txns, 0) AS total_txns,
        ROUND(COALESCE(t.total_volume, 0), 2) AS total_volume,
        ROUND(COALESCE(t.actual_avg_ticket, 0), 2) AS actual_avg_ticket,
        COALESCE(t.failed_txns, 0) AS failed_txns,
        ROUND(COALESCE(t.failed_txns, 0) * 100.0 / NULLIF(t.total_txns, 0), 2) AS failure_rate_pct,
        COALESCE(c.cb_count, 0) AS chargeback_count,
        ROUND(COALESCE(c.total_disputed, 0), 2) AS total_disputed_amount,
        ROUND(COALESCE(c.total_disputed, 0) * 100.0 / NULLIF(t.total_volume, 0), 2) AS chargeback_volume_ratio_pct,
        ROUND(COALESCE(c.cb_count, 0) * 100.0 / NULLIF(t.total_txns, 0), 2) AS dispute_rate_pct,
        ROUND(COALESCE(c.avg_delay, 0), 1) AS avg_reporting_delay_days,
        -- Composite Risk Index (0 - 100)
        ROUND(
            LEAST(100.0, 
                (COALESCE(c.total_disputed, 0) * 100.0 / NULLIF(t.total_volume, 0) * 0.4) +
                (COALESCE(t.failed_txns, 0) * 100.0 / NULLIF(t.total_txns, 0) * 0.3) +
                (LEAST(COALESCE(c.cb_count, 0), 50) * 0.3)
            ), 1
        ) AS composite_risk_score
    FROM dim_merchants m
    LEFT JOIN m_txns t ON m.merchant_id = t.merchant_id
    LEFT JOIN m_cbks c ON m.merchant_id = c.merchant_id
    WHERE t.total_txns > 0
    ORDER BY composite_risk_score DESC
    """)
    print("[OK] View created: v_merchant_risk_scorecard")
    
    # 4. View: KYC Status & Customer Risk Distribution
    con.execute("""
    CREATE OR REPLACE VIEW v_kyc_risk_analysis AS
    WITH user_txns AS (
        SELECT 
            user_id,
            COUNT(*) AS total_txns,
            SUM(amount) AS total_spent
        FROM fct_transactions
        GROUP BY 1
    ),
    user_cbks AS (
        SELECT 
            user_id,
            COUNT(*) AS total_disputes,
            SUM(disputed_amount) AS total_disputed_amount
        FROM fct_chargebacks
        GROUP BY 1
    )
    SELECT 
        u.kyc_status,
        u.risk_segment,
        COUNT(u.user_id) AS total_users,
        ROUND(AVG(u.monthly_income), 2) AS avg_monthly_income,
        SUM(COALESCE(t.total_txns, 0)) AS total_transactions,
        ROUND(SUM(COALESCE(t.total_spent, 0)), 2) AS total_transaction_volume,
        SUM(COALESCE(c.total_disputes, 0)) AS total_chargeback_count,
        ROUND(SUM(COALESCE(c.total_disputed_amount, 0)), 2) AS total_disputed_amount,
        ROUND(SUM(COALESCE(c.total_disputed_amount, 0)) * 100.0 / NULLIF(SUM(t.total_spent), 0), 3) AS dispute_ratio_pct
    FROM dim_users u
    LEFT JOIN user_txns t ON u.user_id = t.user_id
    LEFT JOIN user_cbks c ON u.user_id = c.user_id
    GROUP BY 1, 2
    ORDER BY 1, 2
    """)
    print("[OK] View created: v_kyc_risk_analysis")
    
    # 5. View: Velocity Anomaly Detection (Z-Score Based)
    con.execute("""
    CREATE OR REPLACE VIEW v_velocity_anomalies AS
    WITH user_hourly AS (
        SELECT 
            user_id,
            CAST(timestamp AS DATE) AS txn_date,
            EXTRACT(HOUR FROM CAST(timestamp AS TIMESTAMP)) AS txn_hour,
            COUNT(*) AS txn_count,
            SUM(amount) AS total_amount
        FROM fct_transactions
        WHERE timestamp IS NOT NULL
        GROUP BY 1, 2, 3
    ),
    user_stats AS (
        SELECT 
            user_id,
            AVG(txn_count) AS avg_hourly_txns,
            STDDEV(txn_count) AS std_hourly_txns,
            AVG(total_amount) AS avg_hourly_amount,
            STDDEV(total_amount) AS std_hourly_amount
        FROM user_hourly
        GROUP BY 1
        HAVING STDDEV(txn_count) > 0
    )
    SELECT 
        h.user_id,
        h.txn_date,
        h.txn_hour,
        h.txn_count,
        ROUND(h.total_amount, 2) AS total_amount,
        ROUND(s.avg_hourly_txns, 2) AS avg_hourly_txns,
        ROUND(s.std_hourly_txns, 2) AS std_hourly_txns,
        ROUND((h.txn_count - s.avg_hourly_txns) / s.std_hourly_txns, 2) AS velocity_z_score,
        ROUND((h.total_amount - s.avg_hourly_amount) / NULLIF(s.std_hourly_amount, 0), 2) AS amount_z_score,
        CASE 
            WHEN (h.txn_count - s.avg_hourly_txns) / s.std_hourly_txns > 3 THEN 'CRITICAL'
            WHEN (h.txn_count - s.avg_hourly_txns) / s.std_hourly_txns > 2 THEN 'HIGH'
            WHEN (h.txn_count - s.avg_hourly_txns) / s.std_hourly_txns > 1.5 THEN 'MEDIUM'
            ELSE 'NORMAL'
        END AS anomaly_severity
    FROM user_hourly h
    JOIN user_stats s ON h.user_id = s.user_id
    WHERE (h.txn_count - s.avg_hourly_txns) / s.std_hourly_txns > 1.5
    ORDER BY velocity_z_score DESC
    """)
    print("[OK] View created: v_velocity_anomalies")
    
    # 6. View: Hourly Transaction Patterns (Heatmap Data)
    con.execute("""
    CREATE OR REPLACE VIEW v_hourly_heatmap AS
    SELECT 
        EXTRACT(DOW FROM CAST(timestamp AS TIMESTAMP)) AS day_of_week,
        CASE EXTRACT(DOW FROM CAST(timestamp AS TIMESTAMP))
            WHEN 0 THEN 'Sunday'
            WHEN 1 THEN 'Monday'
            WHEN 2 THEN 'Tuesday'
            WHEN 3 THEN 'Wednesday'
            WHEN 4 THEN 'Thursday'
            WHEN 5 THEN 'Friday'
            WHEN 6 THEN 'Saturday'
        END AS day_name,
        EXTRACT(HOUR FROM CAST(timestamp AS TIMESTAMP)) AS hour_of_day,
        COUNT(*) AS total_txns,
        COUNT(CASE WHEN status = 'FAILED' THEN 1 END) AS failed_txns,
        ROUND(SUM(amount), 2) AS total_volume,
        ROUND(COUNT(CASE WHEN status = 'FAILED' THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 2) AS failure_rate_pct
    FROM fct_transactions
    WHERE timestamp IS NOT NULL
    GROUP BY 1, 2, 3
    ORDER BY 1, 3
    """)
    print("[OK] View created: v_hourly_heatmap")
    
    # 7. View: City-Level Fraud Analysis
    con.execute("""
    CREATE OR REPLACE VIEW v_city_fraud_analysis AS
    WITH city_txns AS (
        SELECT
            COALESCE(u.city, 'Unknown') AS city,
            COUNT(t.txn_id) AS total_txns,
            SUM(t.amount) AS total_volume,
            COUNT(CASE WHEN t.status = 'FAILED' THEN 1 END) AS failed_txns
        FROM fct_transactions t
        LEFT JOIN dim_users u ON t.user_id = u.user_id
        GROUP BY 1
    ),
    city_disputes AS (
        SELECT
            COALESCE(u.city, 'Unknown') AS city,
            COUNT(c.complaint_id) AS total_disputes,
            SUM(c.disputed_amount) AS total_disputed,
            AVG(c.reporting_delay_days) AS avg_delay
        FROM fct_chargebacks c
        LEFT JOIN dim_users u ON c.user_id = u.user_id
        GROUP BY 1
    )
    SELECT 
        t.city,
        t.total_txns,
        ROUND(t.total_volume, 2) AS total_volume,
        t.failed_txns,
        ROUND(t.failed_txns * 100.0 / NULLIF(t.total_txns, 0), 2) AS failure_rate_pct,
        COALESCE(d.total_disputes, 0) AS total_disputes,
        ROUND(COALESCE(d.total_disputed, 0), 2) AS total_disputed_amount,
        ROUND(COALESCE(d.total_disputed, 0) * 100.0 / NULLIF(t.total_volume, 0), 3) AS dispute_ratio_pct,
        ROUND(COALESCE(d.avg_delay, 0), 1) AS avg_reporting_delay_days
    FROM city_txns t
    LEFT JOIN city_disputes d ON t.city = d.city
    ORDER BY total_disputed_amount DESC
    """)
    print("[OK] View created: v_city_fraud_analysis")
    
    # 8. View: Merchant Status Distribution
    con.execute("""
    CREATE OR REPLACE VIEW v_merchant_status_dist AS
    SELECT 
        merchant_status,
        COUNT(*) AS merchant_count,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM dim_merchants), 2) AS pct_of_total
    FROM dim_merchants
    GROUP BY 1
    ORDER BY merchant_count DESC
    """)
    print("[OK] View created: v_merchant_status_dist")
    
    # 9. View: Chargeback Resolution Analysis
    con.execute("""
    CREATE OR REPLACE VIEW v_resolution_analysis AS
    SELECT 
        reason_code,
        COUNT(*) AS dispute_count,
        ROUND(SUM(disputed_amount), 2) AS total_disputed,
        ROUND(AVG(disputed_amount), 2) AS avg_disputed_amount,
        ROUND(AVG(reporting_delay_days), 1) AS avg_reporting_delay,
        ROUND(AVG(resolution_days), 1) AS avg_resolution_days,
        ROUND(MIN(reporting_delay_days), 1) AS min_delay,
        ROUND(MAX(reporting_delay_days), 1) AS max_delay
    FROM fct_chargebacks
    GROUP BY 1
    ORDER BY avg_resolution_days DESC
    """)
    print("[OK] View created: v_resolution_analysis")
    
    con.close()
    print("[SUCCESS] Analytics Warehouse built successfully at:", DB_PATH)

if __name__ == "__main__":
    build_analytics_warehouse()
