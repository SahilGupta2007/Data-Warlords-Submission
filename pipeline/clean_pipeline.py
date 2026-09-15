"""
Enterprise Data Rescue Pipeline - TransOrg AgentIQ Datathon (Track 1)
Author: Team Antigravity
Description:
    Production-grade ETL pipeline to clean, standardize, and reconcile raw fintech logs:
    - UPI Transactions (timestamps, currency normalization, UTR standardizing, status canonicalization)
    - KYC Records (PAN/Aadhaar validation, occupation-based median income imputation, city normalization)
    - Merchant Master (MCC padding, category harmonization, ticket size cleaning)
    - Chargeback Logs (Dispute amount reconciliation with transaction amounts, delay calculations)
    - Emits a comprehensive audit report for Gate 1 & 2 Knockout compliance.
"""

import os
import sys
import re
import json
import logging
from datetime import datetime, timezone
import pandas as pd
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DataRescuePipeline")

# Setup Directory Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DATA_DIR = os.path.join(BASE_DIR, "data", "raw")
PROCESSED_DATA_DIR = os.path.join(BASE_DIR, "data", "processed")
os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)

# Canonical Dictionaries
CITY_NORMALIZATION_MAP = {
    "blr": "Bengaluru",
    "bangalore": "Bengaluru",
    "jpr": "Jaipur",
    "jaipur": "Jaipur",
    "hyd": "Hyderabad",
    "hyderabad": "Hyderabad",
    "bombay": "Mumbai",
    "mumbai": "Mumbai",
    "calcutta": "Kolkata",
    "kolkata": "Kolkata",
    "dilli": "Delhi",
    "delhi": "Delhi",
    "new delhi": "Delhi",
    "asr": "Amritsar",
    "amritsar": "Amritsar",
    "jalandar": "Jalandhar",
    "jalandhar": "Jalandhar",
    "madras": "Chennai",
    "chennai": "Chennai",
    "lucknow": "Lucknow",
    "ludhiana": "Ludhiana",
    "pune": "Pune",
}

STATUS_MAP_TRANSACTIONS = {
    "SUCCESS": "SUCCESS",
    "TXN_SUCCESS": "SUCCESS",
    "COMPLETED": "SUCCESS",
    "S": "SUCCESS",
    "SUCCESS": "SUCCESS",
    "FAILED": "FAILED",
    "TXN_FAILED": "FAILED",
    "FAIL": "FAILED",
    "DECLINED": "FAILED",
    "PENDING": "PENDING",
    "PROCESSING": "PENDING",
    "INITIATED": "PENDING",
}

STATUS_MAP_KYC = {
    "DONE": "VERIFIED",
    "VERIFIED": "VERIFIED",
    "APPROVED": "VERIFIED",
    "KYC_DONE": "VERIFIED",
    "V": "VERIFIED",
    "PENDING": "PENDING",
    "REJECT": "REJECTED",
    "REJECTED": "REJECTED",
}

STATUS_MAP_MERCHANT = {
    "ACTIVE": "ACTIVE",
    "A": "ACTIVE",
    "LIVE": "ACTIVE",
    "ENABLED": "ACTIVE",
    "SUSPENDED": "SUSPENDED",
    "HOLD": "SUSPENDED",
    "INACTIVE": "INACTIVE",
    "DISABLED": "INACTIVE",
    "I": "INACTIVE",
}

def clean_user_id(val):
    """Standardizes user IDs to format USR00000 (5 digits)"""
    if pd.isna(val):
        return None
    val_str = str(val).strip()
    digits = re.findall(r"\d+", val_str)
    if digits:
        return f"USR{int(digits[0]):05d}"
    return val_str.upper()

def clean_merchant_id(val):
    """Standardizes merchant IDs to format MCH0000 (4 digits)"""
    if pd.isna(val):
        return None
    val_str = str(val).strip()
    digits = re.findall(r"\d+", val_str)
    if digits:
        return f"MCH{int(digits[0]):04d}"
    return val_str.upper()

def clean_currency_amount(val):
    """
    Cleans messy currency strings: 'Rs. 6362.9', '₹16,466.93', 'INR 13,312', '27.3k', negative values.
    Returns (cleaned_amount, is_reversal)
    """
    if pd.isna(val):
        return np.nan, False
    s = str(val).strip()
    if not s:
        return np.nan, False
    
    # Check if 'k' or 'K' multiplier exists
    is_k = bool(re.search(r"[kK]$", s))
    
    # Check negative sign
    is_negative = bool(re.search(r"-\s*[\d,.]+|[\d,.]+\s*-", s)) or s.startswith("-")
    
    # Extract only numbers and dot
    clean_str = re.sub(r"[^\d.]", "", s)
    if not clean_str:
        return np.nan, is_negative
    try:
        amt = float(clean_str)
        if is_k:
            amt *= 1000.0
        return amt, is_negative
    except ValueError:
        return np.nan, is_negative

def parse_robust_timestamp(val):
    """
    Parses messy timestamps: Unix epoch, ISO, DD/MM/YYYY, MM-DD-YYYY AM/PM, etc.
    Returns standard pandas Timestamp.
    """
    if pd.isna(val):
        return pd.NaT
    s = str(val).strip()
    if not s:
        return pd.NaT
    
    # Check Unix epoch (10 digits approx)
    if re.fullmatch(r"\d{9,12}(\.\d+)?", s):
        try:
            return pd.to_datetime(float(s), unit="s")
        except:
            pass
            
    # Try mixed string parsing with dayfirst heuristic
    try:
        return pd.to_datetime(s, format="mixed", dayfirst=True)
    except Exception:
        try:
            return pd.to_datetime(s)
        except Exception:
            return pd.NaT

def clean_city(val):
    """Normalizes Indian cities from abbreviations and historical names."""
    if pd.isna(val):
        return "Unknown"
    cleaned = str(val).strip().lower()
    return CITY_NORMALIZATION_MAP.get(cleaned, str(val).strip().title())

def clean_transactions(raw_df, merchants_df=None):
    """Rescues and standardizes track1_upi_transactions.csv"""
    logger.info(f"Rescuing Transactions Data: Raw rows = {len(raw_df)}")
    audit = {
        "raw_rows": len(raw_df),
        "raw_nulls": int(raw_df.isnull().sum().sum()),
        "transformations": []
    }
    
    df = raw_df.copy()
    
    # 1. Clean IDs
    df["txn_id"] = df["txn_id"].astype(str).str.strip().str.upper()
    df["user_id"] = df["user_id"].apply(clean_user_id)
    df["merchant_id"] = df["merchant_id"].apply(clean_merchant_id)
    audit["transformations"].append("Standardized user_id (USR00000) and merchant_id (MCH0000) via regex integer normalization")
    
    # 2. Clean timestamps
    df["timestamp"] = df["timestamp"].apply(parse_robust_timestamp)
    unparseable_ts = df["timestamp"].isna().sum()
    audit["transformations"].append(f"Parsed mixed timestamps (Epoch, ISO, AM/PM, Slashed). Unparseable = {unparseable_ts}")
    
    # 3. Clean amounts
    cleaned_amts = df["amount"].apply(clean_currency_amount)
    df["amount_clean"] = [x[0] for x in cleaned_amts]
    df["is_reversal"] = [x[1] for x in cleaned_amts]
    
    # Median imputation if any amount missing (enterprise standard)
    if df["amount_clean"].isna().sum() > 0:
        overall_median = df["amount_clean"].median()
        df["amount_clean"] = df["amount_clean"].fillna(overall_median)
        audit["transformations"].append(f"Imputed missing amounts using median transaction size: ₹{overall_median:.2f}")
    
    df["amount"] = df["amount_clean"]
    df.drop(columns=["amount_clean"], inplace=True)
    audit["transformations"].append("Cleaned currency symbols (₹, Rs., INR, commas) and isolated reversal flags")
    
    # 4. Clean UTR
    def fix_utr(u):
        if pd.isna(u) or str(u).strip() == "" or str(u).strip().lower() == "nan":
            return "MISSING_UTR"
        u_str = re.sub(r"\s+", "", str(u).strip().upper())
        if not u_str.startswith("UTR"):
            u_str = "UTR" + u_str
        return u_str

    df["utr"] = df["utr"].apply(fix_utr)
    df["is_missing_utr"] = df["utr"] == "MISSING_UTR"
    audit["transformations"].append("Harmonized UTR values; flagged missing UTRs without dropping records")
    
    # 5. Clean MCC & Status
    def fix_mcc(m):
        if pd.isna(m) or str(m).strip() == "" or str(m).strip().lower() == "nan":
            return None
        m_str = str(m).replace("MCC-", "").replace(".0", "").strip()
        digits = re.findall(r"\d+", m_str)
        if digits:
            return f"{int(digits[0]):04d}"
        return None

    df["mcc"] = df["mcc"].apply(fix_mcc)
    
    # If merchant master provided, backfill missing MCC
    if merchants_df is not None:
        mcc_lookup = merchants_df.set_index("merchant_id")["mcc"].to_dict()
        df["mcc"] = df["mcc"].fillna(df["merchant_id"].map(mcc_lookup))
        audit["transformations"].append("Cross-reconciled missing MCC codes against Merchant Master table")
    
    # Default MCC fallback if still null
    df["mcc"] = df["mcc"].fillna("9999")
    
    df["status"] = df["status"].astype(str).str.strip().str.upper().map(
        lambda s: STATUS_MAP_TRANSACTIONS.get(s, "PENDING")
    )
    audit["transformations"].append("Harmonized transaction status values into canonical enum (SUCCESS, FAILED, PENDING)")
    
    # 6. Deduplication
    initial_count = len(df)
    df.drop_duplicates(subset=["txn_id"], keep="first", inplace=True)
    duplicates_removed = initial_count - len(df)
    audit["duplicates_removed"] = duplicates_removed
    audit["clean_rows"] = len(df)
    audit["clean_nulls"] = int(df.isnull().sum().sum())
    
    logger.info(f"Transactions Cleaned: Final rows = {len(df)}, Duplicates removed = {duplicates_removed}")
    return df, audit

def clean_merchants(raw_df):
    """Rescues and standardizes track1_merchants_master.csv"""
    logger.info(f"Rescuing Merchants Data: Raw rows = {len(raw_df)}")
    audit = {
        "raw_rows": len(raw_df),
        "raw_nulls": int(raw_df.isnull().sum().sum()),
        "transformations": []
    }
    
    df = raw_df.copy()
    
    # 1. Clean merchant_id
    df["merchant_id"] = df["merchant_id"].apply(clean_merchant_id)
    
    # 2. Clean names
    df["merchant_name"] = df["merchant_name"].astype(str).str.strip().apply(
        lambda n: re.sub(r"\s+", " ", n).title()
    )
    
    # 3. Clean MCC & Category
    def fix_mcc(m):
        if pd.isna(m) or str(m).strip() == "":
            return "9999"
        m_str = str(m).replace("MCC-", "").replace(".0", "").strip()
        digits = re.findall(r"\d+", m_str)
        if digits:
            return f"{int(digits[0]):04d}"
        return "9999"
        
    df["mcc"] = df["mcc"].apply(fix_mcc)
    
    def clean_category(c):
        if pd.isna(c) or str(c).strip() == "":
            return "General Retail"
        c_str = str(c).replace("_", " ").strip().title()
        return c_str
        
    df["merchant_category"] = df["merchant_category"].apply(clean_category)
    
    # 4. Clean Business Type
    def fix_biz_type(b):
        if pd.isna(b):
            return "INDIVIDUAL"
        b_clean = re.sub(r"[\s\-_]+", "_", str(b).strip().upper())
        if "PRIV" in b_clean:
            return "PRIVATE_LIMITED"
        elif "SOLE" in b_clean or "PROP" in b_clean:
            return "SOLE_PROPRIETOR"
        elif "PARTNER" in b_clean:
            return "PARTNERSHIP"
        return "INDIVIDUAL"
        
    df["business_type"] = df["business_type"].apply(fix_biz_type)
    
    # 5. Clean City & State
    df["city"] = df["city"].apply(clean_city)
    df["state"] = df["state"].astype(str).str.strip().str.title()
    
    # 6. Clean Onboarding Date
    df["onboarding_date"] = df["onboarding_date"].apply(parse_robust_timestamp)
    # Forward-fill missing onboarding dates with default minimum date
    df["onboarding_date"] = df["onboarding_date"].fillna(pd.Timestamp("2023-01-01"))
    
    # 7. Clean Merchant Status
    df["merchant_status"] = df["merchant_status"].astype(str).str.strip().str.upper().map(
        lambda s: STATUS_MAP_MERCHANT.get(s, "ACTIVE")
    )
    
    # 8. Clean Declared Average Ticket Size
    ticket_cleaned = df["declared_avg_ticket_size"].apply(clean_currency_amount)
    df["declared_avg_ticket_size"] = [x[0] for x in ticket_cleaned]
    category_median_ticket = df.groupby("merchant_category")["declared_avg_ticket_size"].transform("median")
    df["declared_avg_ticket_size"] = df["declared_avg_ticket_size"].fillna(category_median_ticket).fillna(1000.0)
    
    # Deduplicate on merchant_id
    initial_count = len(df)
    df.drop_duplicates(subset=["merchant_id"], keep="first", inplace=True)
    duplicates_removed = initial_count - len(df)
    
    audit["duplicates_removed"] = duplicates_removed
    audit["clean_rows"] = len(df)
    audit["clean_nulls"] = int(df.isnull().sum().sum())
    audit["transformations"].append("Standardized merchant IDs, categories, and business types")
    audit["transformations"].append("Imputed missing ticket size using Category Medians")
    
    logger.info(f"Merchants Cleaned: Final rows = {len(df)}, Duplicates removed = {duplicates_removed}")
    return df, audit

def clean_kyc(raw_df):
    """Rescues and standardizes track1_kyc_records.csv"""
    logger.info(f"Rescuing KYC Data: Raw rows = {len(raw_df)}")
    audit = {
        "raw_rows": len(raw_df),
        "raw_nulls": int(raw_df.isnull().sum().sum()),
        "transformations": []
    }
    
    df = raw_df.copy()
    
    # 1. Clean user_id
    df["user_id"] = df["user_id"].apply(clean_user_id)
    
    # 2. Clean Name
    df["full_name"] = df["full_name"].astype(str).str.strip().apply(
        lambda n: re.sub(r"\s+", " ", n).title()
    )
    
    # 3. Clean PAN & Validation
    def clean_pan(p):
        if pd.isna(p):
            return "UNKNOWN_PAN", False
        p_clean = re.sub(r"[\s\-_]+", "", str(p).strip().upper())
        is_valid = bool(re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", p_clean))
        return (p_clean if p_clean else "UNKNOWN_PAN"), is_valid
        
    pan_results = df["pan"].apply(clean_pan)
    df["pan"] = [x[0] for x in pan_results]
    df["is_valid_pan"] = [x[1] for x in pan_results]
    
    # 4. Clean Aadhaar
    def clean_aadhaar(a):
        if pd.isna(a):
            return "UNKNOWN_AADHAAR", False, False
        a_str = str(a).strip()
        is_masked = "X" in a_str.upper()
        a_clean = re.sub(r"[\s\-_]+", "", a_str)
        is_valid = bool(re.match(r"^\d{12}$", a_clean))
        return a_clean, is_valid, is_masked
        
    aadhaar_results = df["aadhaar"].apply(clean_aadhaar)
    df["aadhaar"] = [x[0] for x in aadhaar_results]
    df["is_valid_aadhaar"] = [x[1] for x in aadhaar_results]
    df["is_masked_aadhaar"] = [x[2] for x in aadhaar_results]
    
    # 5. Clean City & State
    df["city"] = df["city"].apply(clean_city)
    df["state"] = df["state"].astype(str).str.strip().str.title()
    
    # 6. Clean Income & Enterprise Imputation
    incomes = df["monthly_income"].apply(clean_currency_amount)
    df["monthly_income_clean"] = [x[0] for x in incomes]
    
    # Impute missing income by occupation median
    df["occupation"] = df["occupation"].astype(str).str.strip().str.title().replace({"Nan": "Other", "": "Other"})
    occ_median = df.groupby("occupation")["monthly_income_clean"].transform("median")
    overall_inc_median = df["monthly_income_clean"].median()
    df["monthly_income"] = df["monthly_income_clean"].fillna(occ_median).fillna(overall_inc_median)
    df.drop(columns=["monthly_income_clean"], inplace=True)
    
    # 7. Clean KYC Status & Risk Segment
    df["kyc_status"] = df["kyc_status"].astype(str).str.strip().str.upper().map(
        lambda s: STATUS_MAP_KYC.get(s, "PENDING")
    )
    
    def clean_risk(r):
        if pd.isna(r):
            return "MEDIUM"
        r_str = str(r).strip().upper()
        if r_str in ["LOW", "MEDIUM", "HIGH"]:
            return r_str
        return "MEDIUM"
        
    df["risk_segment"] = df["risk_segment"].apply(clean_risk)
    
    # 8. Clean Timestamps
    df["date_of_birth"] = df["date_of_birth"].apply(parse_robust_timestamp)
    df["signup_timestamp"] = df["signup_timestamp"].apply(parse_robust_timestamp)
    df["signup_timestamp"] = df["signup_timestamp"].fillna(pd.Timestamp("2024-01-01"))
    
    # Deduplicate on user_id
    initial_count = len(df)
    df.drop_duplicates(subset=["user_id"], keep="first", inplace=True)
    duplicates_removed = initial_count - len(df)
    
    audit["duplicates_removed"] = duplicates_removed
    audit["clean_rows"] = len(df)
    audit["clean_nulls"] = int(df.isnull().sum().sum())
    audit["transformations"].append("Parsed PAN and Aadhaar; created validation flags (is_valid_pan, is_valid_aadhaar)")
    audit["transformations"].append("Imputed missing incomes using Occupation Medians")
    audit["transformations"].append("Standardized city aliases (BLR -> Bengaluru, Hyd -> Hyderabad, etc.)")
    
    logger.info(f"KYC Cleaned: Final rows = {len(df)}, Duplicates removed = {duplicates_removed}")
    return df, audit

def clean_chargebacks(raw_data, txn_df=None):
    """Rescues and standardizes track1_chargebacks.json"""
    logger.info("Rescuing Chargeback Complaints JSON data...")
    if isinstance(raw_data, list):
        df = pd.DataFrame(raw_data)
    else:
        df = raw_data.copy()
        
    audit = {
        "raw_rows": len(df),
        "raw_nulls": int(df.isnull().sum().sum()),
        "transformations": []
    }
    
    # 1. Clean IDs
    df["complaint_id"] = df["complaint_id"].astype(str).str.strip().str.upper()
    df["txn_id"] = df["txn_id"].astype(str).str.strip().str.upper()
    df["user_id"] = df["user_id"].apply(clean_user_id)
    df["merchant_id"] = df["merchant_id"].apply(clean_merchant_id)
    
    # 2. Clean Timestamps
    df["transaction_timestamp"] = df["transaction_timestamp"].apply(parse_robust_timestamp)
    df["reported_timestamp"] = df["reported_timestamp"].apply(parse_robust_timestamp)
    df["bank_response_timestamp"] = df["bank_response_timestamp"].apply(parse_robust_timestamp)
    
    # Calculate operational delay metrics
    df["reporting_delay_days"] = (
        (df["reported_timestamp"] - df["transaction_timestamp"]).dt.total_seconds() / 86400.0
    ).clip(lower=0).round(1)
    
    df["resolution_days"] = (
        (df["bank_response_timestamp"] - df["reported_timestamp"]).dt.total_seconds() / 86400.0
    ).clip(lower=0).round(1)
    
    # 3. Clean Disputed Amount & Cross-Reconcile
    disp_clean = df["disputed_amount"].apply(clean_currency_amount)
    df["disputed_amount_clean"] = [x[0] for x in disp_clean]
    
    # Enterprise cross-reconciliation: If disputed_amount is missing or NaN, look up amount from transactions!
    if txn_df is not None:
        txn_amt_map = txn_df.set_index("txn_id")["amount"].to_dict()
        missing_count = df["disputed_amount_clean"].isna().sum()
        df["disputed_amount_clean"] = df["disputed_amount_clean"].fillna(df["txn_id"].map(txn_amt_map))
        reconciled_count = missing_count - df["disputed_amount_clean"].isna().sum()
        audit["transformations"].append(f"Cross-reconciled {reconciled_count} missing disputed amounts directly from UPI Transactions table")
        
    overall_disp_median = df["disputed_amount_clean"].median()
    df["disputed_amount"] = df["disputed_amount_clean"].fillna(overall_disp_median).fillna(1500.0)
    df.drop(columns=["disputed_amount_clean"], inplace=True)
    
    # 4. Standardize Reason Code
    def clean_reason(r):
        if pd.isna(r):
            return "Other Complaint"
        r_str = str(r).strip()
        r_lower = r_str.lower()
        if "delivered" in r_lower or "goods" in r_lower:
            return "Merchant Not Delivered"
        elif "compromise" in r_lower or "hack" in r_lower or "takeover" in r_lower:
            return "Account Takeover / Compromised"
        elif "twice" in r_lower or "double" in r_lower or "duplicate" in r_lower:
            return "Duplicate Debit"
        elif "fraud" in r_lower or "unauthorized" in r_lower:
            return "Unauthorized Transaction"
        elif "denies" in r_lower or "denied" in r_lower:
            return "Payment Denied by Merchant"
        return r_str.title()
        
    df["reason_code"] = df["reason_code"].apply(clean_reason)
    
    # 5. Standardize Severity
    def clean_severity(s):
        if pd.isna(s):
            return "MEDIUM"
        s_str = str(s).strip().upper()
        if s_str in ["CRITICAL", "CRIT"]:
            return "CRITICAL"
        elif s_str in ["H", "HIGH"]:
            return "HIGH"
        elif s_str in ["L", "LOW"]:
            return "LOW"
        return "MEDIUM"
        
    df["severity"] = df["severity"].apply(clean_severity)
    
    # 6. Standardize Resolution Status
    def clean_res_status(st):
        if pd.isna(st):
            return "PENDING"
        st_str = str(st).strip().upper()
        if "CLOSE" in st_str or "RESOLV" in st_str:
            return "CLOSED"
        elif "PROGRESS" in st_str or "INVESTIGAT" in st_str:
            return "IN_PROGRESS"
        elif "REJECT" in st_str:
            return "REJECTED"
        return "PENDING"
        
    df["resolution_status"] = df["resolution_status"].apply(clean_res_status)
    
    # Deduplicate complaint_id
    initial_count = len(df)
    df.drop_duplicates(subset=["complaint_id"], keep="first", inplace=True)
    duplicates_removed = initial_count - len(df)
    
    audit["duplicates_removed"] = duplicates_removed
    audit["clean_rows"] = len(df)
    audit["clean_nulls"] = int(df.isnull().sum().sum())
    audit["transformations"].append("Calculated dispute delay and bank resolution turnaround times")
    audit["transformations"].append("Standardized complaint severity, reason taxonomy, and resolution status")
    
    logger.info(f"Chargebacks Cleaned: Final rows = {len(df)}, Duplicates removed = {duplicates_removed}")
    return df, audit

def run_pipeline():
    """Runs the full end-to-end data rescue pipeline and generates audit proof."""
    print("\n=======================================================")
    print("   TRANSSORG AGENTIQ DATATHON - DATA RESCUE PIPELINE   ")
    print("=======================================================\n")
    
    # Load raw data
    merchants_raw = pd.read_csv(os.path.join(RAW_DATA_DIR, "track1_merchants_master.csv"))
    kyc_raw = pd.read_csv(os.path.join(RAW_DATA_DIR, "track1_kyc_records.csv"))
    transactions_raw = pd.read_csv(os.path.join(RAW_DATA_DIR, "track1_upi_transactions.csv"))
    
    with open(os.path.join(RAW_DATA_DIR, "track1_chargebacks.json"), "r", encoding="utf-8") as f:
        chargebacks_raw = json.load(f)
        
    # Process sequentially with foreign-key reconciliation
    merchants_clean, audit_merchants = clean_merchants(merchants_raw)
    kyc_clean, audit_kyc = clean_kyc(kyc_raw)
    txn_clean, audit_txn = clean_transactions(transactions_raw, merchants_df=merchants_clean)
    cb_clean, audit_cb = clean_chargebacks(chargebacks_raw, txn_df=txn_clean)
    
    # Save processed outputs in CSV and Parquet
    merchants_clean.to_parquet(os.path.join(PROCESSED_DATA_DIR, "clean_merchants.parquet"), index=False)
    merchants_clean.to_csv(os.path.join(PROCESSED_DATA_DIR, "clean_merchants.csv"), index=False)
    
    kyc_clean.to_parquet(os.path.join(PROCESSED_DATA_DIR, "clean_kyc.parquet"), index=False)
    kyc_clean.to_csv(os.path.join(PROCESSED_DATA_DIR, "clean_kyc.csv"), index=False)
    
    txn_clean.to_parquet(os.path.join(PROCESSED_DATA_DIR, "clean_transactions.parquet"), index=False)
    txn_clean.to_csv(os.path.join(PROCESSED_DATA_DIR, "clean_transactions.csv"), index=False)
    
    cb_clean.to_parquet(os.path.join(PROCESSED_DATA_DIR, "clean_chargebacks.parquet"), index=False)
    cb_clean.to_csv(os.path.join(PROCESSED_DATA_DIR, "clean_chargebacks.csv"), index=False)
    
    # Build complete Audit Report
    full_audit = {
        "execution_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "datasets": {
            "track1_upi_transactions": audit_txn,
            "track1_kyc_records": audit_kyc,
            "track1_merchants_master": audit_merchants,
            "track1_chargebacks": audit_cb
        },
        "summary": {
            "total_raw_records": audit_txn["raw_rows"] + audit_kyc["raw_rows"] + audit_merchants["raw_rows"] + audit_cb["raw_rows"],
            "total_clean_records": audit_txn["clean_rows"] + audit_kyc["clean_rows"] + audit_merchants["clean_rows"] + audit_cb["clean_rows"],
            "total_duplicates_removed": audit_txn["duplicates_removed"] + audit_kyc["duplicates_removed"] + audit_merchants["duplicates_removed"] + audit_cb["duplicates_removed"],
            "data_retention_rate_pct": round(
                (audit_txn["clean_rows"] + audit_kyc["clean_rows"] + audit_merchants["clean_rows"] + audit_cb["clean_rows"]) /
                (audit_txn["raw_rows"] + audit_kyc["raw_rows"] + audit_merchants["raw_rows"] + audit_cb["raw_rows"]) * 100.0, 2
            )
        }
    }
    
    audit_path = os.path.join(PROCESSED_DATA_DIR, "audit_proof.json")
    with open(audit_path, "w", encoding="utf-8") as f:
        json.dump(full_audit, f, indent=2)
        
    print(f"\n Pipeline Completed Successfully!")
    print(f"Total Raw Records:    {full_audit['summary']['total_raw_records']}")
    print(f"Total Clean Records:  {full_audit['summary']['total_clean_records']}")
    print(f"Data Retention Rate:  {full_audit['summary']['data_retention_rate_pct']}% (Zero unjustified row drops!)")
    print(f"Clean Data Exported:  {PROCESSED_DATA_DIR}")
    print(f"Audit Proof Saved:    {audit_path}\n")

if __name__ == "__main__":
    run_pipeline()
