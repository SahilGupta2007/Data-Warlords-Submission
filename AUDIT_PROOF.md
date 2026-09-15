# Audit Proof: Data Rescue & Governance Verification
**Datathon Track:** Track 1 - FinTech & BFSI  
**Project:** AgentIQ UPI Fraud Ring & Merchant Risk Intelligence  
**Organization:** TransOrg Analytics & Pickl.AI Datathon  

This document fulfills the mandatory **Gate 1 Proof of Data Cleaning** and **Gate 2 Data Rescue & Reproducibility** evaluation requirements.

---

## 1. Executive Summary & Verification Matrix

The Data Rescue Pipeline (`pipeline/clean_pipeline.py`) was developed under a **Zero-Lazy-Drop Policy**. In accordance with enterprise banking standards, missing or corrupt fields were rescued through:
1. **Deterministic Regex Standardization** (IDs, PAN, Aadhaar, MCC).
2. **Multi-Format Datetime Parsing** (handling Epoch, ISO-8601, slashed, and 12-hour AM/PM formats).
3. **Occupation-Specific Median Imputation** (Monthly Income).
4. **Category-Specific Median Imputation** (Declared Ticket Size).
5. **Cross-Table Foreign Key Reconciliation** (reconciling missing chargeback dispute amounts and transaction MCCs directly from linked tables).

### Ingestion vs. Retention Audit Table

| Dataset | Raw Ingested Rows | Clean Retained Rows | Exact Duplicates Removed | Unjustified Rows Dropped | Net Data Retention Rate |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`track1_upi_transactions.csv`** | 20,400 | 20,000 | 400 (Deduplicated on `txn_id`) | **0 (0.00%)** | **98.04%** |
| **`track1_kyc_records.csv`** | 36,400 | 28,920 | 7,480 (Deduplicated on `user_id`) | **0 (0.00%)** | **79.45%** (100% of unique users) |
| **`track1_merchants_master.csv`** | 6,210 | 4,343 | 1,867 (Deduplicated on `merchant_id`) | **0 (0.00%)** | **69.94%** (100% of unique merchants) |
| **`track1_chargebacks.json`** | 2,884 | 2,800 | 84 (Deduplicated on `complaint_id`) | **0 (0.00%)** | **97.09%** |
| **Consolidated Total** | **65,894** | **56,063** | **9,831** | **0 (0.00%)** | **85.08%** (100% of unique entities) |

> [!IMPORTANT]
> **Data Retention Compliance**: 100% of unique non-duplicate transactions, registered merchants, KYC customer profiles, and dispute records were preserved. Exactly 0 rows were dropped due to format corruptions, currency symbols, or timestamp variations. Deduplication removed redundant records that would otherwise artificially inflate transaction counts and skew risk ratios.

---

## 2. Table-by-Table Data Rescue Strategies & Justifications

### A. Core UPI Transactions (`track1_upi_transactions.csv`)
- **Raw Challenge**:
  - `amount`: Embedded symbols (`₹`, `Rs.`, `INR`), thousands commas (`"₹16,466.93"`, `"INR 13,312"`), and negative values (`-23820.57`).
  - `timestamp`: Chaos of formats — Unix epoch integers (`1770063471`), ISO strings (`2026-01-15 00:11:30`), AM/PM representations (`03-10-2026 09:27:31 PM`), and slashed dates (`25/02/2026`).
  - `utr`: Trailing and embedded spaces (`UTR 2787678319`), empty strings, and missing identifiers.
  - `status`: 9 variations (`SUCCESS`, `Success`, `TXN_SUCCESS`, `COMPLETED`, `S`, `FAILED`, `Fail`, `Declined`, `Pending`, `Initiated`).
- **Rescue Strategy**:
  - **Amounts**: Stripped all currency tokens via regex `[^\d.]`. Created an explicit flag `is_reversal = True` for negative values while capturing `abs(amount)` to preserve financial velocity without distorting volume aggregates.
  - **Timestamps**: Implemented a multi-tier fallback parser detecting Unix timestamps by string length (`\d{10}`) and parsing slashed strings using intelligent day-first heuristics. Unparseable count: **0**.
  - **UTR**: Harmonized into unified `UTR##########`. Null values were retained and tagged with `is_missing_utr = True` rather than dropped, uncovering a vital business insight: *transactions with missing UTRs experience a 4.2x higher dispute rate*.
  - **Status**: Mapped all 9 variants into canonical 3-state enum: `SUCCESS`, `FAILED`, `PENDING`.
  - **MCC Backfill**: Where `mcc` was blank, the pipeline joined against `track1_merchants_master.csv` to backfill the merchant's registered MCC code.

### B. Customer Identity & KYC (`track1_kyc_records.csv`)
- **Raw Challenge**:
  - `user_id`: Inconsistent casing and prefixes (`USR16112`, `USR 45454`, `usr22494`, `usr_64308`).
  - `monthly_income`: Corrupt formats (`"27.3k"`, `"₹11,214"`, negative values `-8083`).
  - `city`: High variation in naming (`BLR` vs `Bengaluru`, `Bombay` vs `Mumbai`, `Hyd` vs `Hyderabad`, `Dilli` vs `Delhi`, `ASR` vs `Amritsar`).
  - `pan` & `aadhaar`: Spaces in PAN (`CACWZ 2722 S`), lowercase characters, masked Aadhaar (`XXXX-XXXX-5406`).
- **Rescue Strategy**:
  - **Entity ID**: Extracted integer suffix `(\d+)` and standardized to `USR` + zero-padded 5 digits (`USR45454`, `USR22494`, `USR64308`).
  - **Income Imputation**: Expanded multiplier `k` (`27.3k` ➔ `27,300`). Negative values converted to positive. Null incomes were imputed using the **median monthly income for the user's specific occupation** (e.g. Salaried, Gig Worker, Retired, Student), preventing artificial skews.
  - **City Harmonization**: Standardized through a canonical dictionary mapping historical and abbreviated Indian city names to official metropolitan designations.
  - **Regulatory Flags**: Cleaned PAN and Aadhaar into alphanumeric strings. Appended audit flags `is_valid_pan` (Income Tax regex checksum) and `is_masked_aadhaar` to quantify compliance risk without violating data privacy.

### C. Merchant Master (`track1_merchants_master.csv`)
- **Raw Challenge**:
  - `merchant_id`: Inconsistent prefixes (`mch2849`, `MCH-2637`, `MCH 2430`).
  - `mcc`: Prefix pollution (`MCC-7011`), trailing decimals (`5311.0`), missing MCCs.
  - `merchant_status`: Redundant state strings (`Active`, `A`, `Live`, `Enabled`, `SUSPENDED`, `Hold`, `Disabled`, `I`).
  - `declared_avg_ticket_size`: Embedded currency symbols and negative values.
- **Rescue Strategy**:
  - **IDs**: Standardized to `MCH` + 4 zero-padded digits (`MCH2849`, `MCH2637`, `MCH2430`).
  - **MCC & Categories**: Cleaned floats and prefixes to 4-digit strings. Formatted category strings to Title Case (`Hotel Lodging`, `Medical Store`).
  - **Status Harmonization**: Mapped to canonical 3-state enum: `ACTIVE`, `SUSPENDED`, `INACTIVE`.
  - **Declared Ticket Size**: Stripped symbols. Missing entries imputed using the **median ticket size of that merchant's specific category**.

### D. Chargebacks & Disputes (`track1_chargebacks.json`)
- **Raw Challenge**:
  - `merchant_id`: Raw integer IDs (`"3835"`) disconnected from merchant master schema.
  - `disputed_amount`: Empty strings (`""`), nulls, currency strings (`"Rs. 7,039"`).
  - `reason_code`: Uncontrolled text entries (`"Customer says amount was debited twice."`).
- **Rescue Strategy**:
  - **Foreign Key Healing**: Converted numeric merchant references to `MCH` + 4-digit format (`"3835"` ➔ `MCH3835`).
  - **Dispute Amount Reconciliation**: Where `disputed_amount` was empty or missing, the pipeline performed a **foreign key lookup against the UPI transactions table (`txn_id`)** to recover the exact transacted amount.
  - **Delay Metric Derivation**: Engineered `reporting_delay_days` and `resolution_days` to measure customer reporting latency and banking response performance.

---

## 3. Automated Reproducibility

Evaluators can verify the data rescue and reproduce all cleaned Parquet, CSV, and JSON audit artifacts with a single command:
```bash
python pipeline/clean_pipeline.py
```
Outputs are automatically placed into `data/processed/audit_proof.json`.
