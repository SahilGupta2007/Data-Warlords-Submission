# Data Dictionary: Enterprise UPI Fraud & Merchant Analytics
**Datathon Track:** Track 1 - FinTech & BFSI  
**Project:** AgentIQ UPI Fraud Ring & Merchant Risk Intelligence  
**Organization:** TransOrg Analytics & Pickl.AI Datathon  

This document serves as the formal **Data Dictionary** mandated by **Gate 1 (Compliance & Sanity Check)**. It defines every raw attribute, data corruption trap identified, cleaning transformation applied, and analytical fields engineered for the Star-Schema Data Warehouse.

---

## 1. UPI Transactions Table (`fct_transactions`)
**Source File:** `track1_fintech_dataset_files/track1_upi_transactions.csv`  
**Processed File:** `data/processed/clean_transactions.parquet` / `.csv`  
**Description:** High-velocity core payment records between customers and merchants.

| Column Name | Raw Data Type | Clean Data Type | Description | Cleaning & Transformation Strategy |
| :--- | :--- | :--- | :--- | :--- |
| `txn_id` | String | VARCHAR (PK) | Unique Transaction Reference ID | Stripped leading/trailing whitespace; uppercase normalized. Enforced uniqueness. |
| `timestamp` | Mixed Strings / Ints | TIMESTAMP (UTC) | Exact time payment occurred | Disambiguated mixed Unix epoch seconds, ISO-8601, 12-hour AM/PM (`03-10-2026 09:27:31 PM`), and slashed dates (`DD/MM/YYYY`). |
| `user_id` | Corrupted String | VARCHAR (FK) | Unique Customer Identifier | Standardized noisy representations (`usr12345`, `USR 12345`, `12345`) to canonical `USR00000` format (5-digit padded). |
| `merchant_id` | Corrupted String | VARCHAR (FK) | Unique Merchant Identifier | Standardized noisy representations (`mch1234`, `MCH 1234`, `1234`) to canonical `MCH0000` format (4-digit padded). |
| `amount` | Corrupted String | DECIMAL(12,2) | Transaction amount in INR | Stripped symbols (`₹`, `Rs.`, `INR`), thousands commas, and whitespace. Nulls imputed with overall median transaction value. |
| `is_reversal` | *Engineered* | BOOLEAN | Payment reversal indicator | Flagged `True` if original raw amount contained negative values (`-23820.57`), preserving absolute amount for velocity analysis. |
| `utr` | Corrupted String | VARCHAR | 12-digit Unique Transaction Reference | Harmonized whitespace (`UTR 2787678319` ➔ `UTR2787678319`). Preserved without dropping rows; set to `MISSING_UTR` if null. |
| `is_missing_utr` | *Engineered* | BOOLEAN | Flag for missing/corrupt UTR | Flagged `True` when UTR was unpopulated by upstream banking gateway. |
| `mcc` | Corrupted String / Float | VARCHAR(4) | Merchant Category Code | Stripped `MCC-`, removed float decimals (`5311.0` ➔ `5311`), padded to 4 digits. Missing values cross-reconciled from Merchant Master. |
| `status` | Corrupted String | VARCHAR(10) | Final Transaction State | Standardized noisy strings (`SUCCESS`, `S`, `COMPLETED`, `TXN_SUCCESS`, `FAILED`, `Declined`, `Initiated`) into canonical enum: `SUCCESS`, `FAILED`, `PENDING`. |

---

## 2. Customer KYC Master (`dim_users`)
**Source File:** `track1_fintech_dataset_files/track1_kyc_records.csv`  
**Processed File:** `data/processed/clean_kyc.parquet` / `.csv`  
**Description:** Identity, demographic, and compliance records for transacting customers.

| Column Name | Raw Data Type | Clean Data Type | Description | Cleaning & Transformation Strategy |
| :--- | :--- | :--- | :--- | :--- |
| `user_id` | Corrupted String | VARCHAR (PK) | Unique Customer Identifier | Normalized to `USR00000`. Deduplicated keeping latest profile. |
| `full_name` | String | VARCHAR | Full legal name of customer | Normalized excess whitespace; converted to Proper Case. |
| `pan` | Corrupted String | VARCHAR(10) | Permanent Account Number (India) | Stripped spaces and hyphens (`CACWZ 2722 S` ➔ `CACWZ2722S`), uppercase. |
| `is_valid_pan` | *Engineered* | BOOLEAN | Regulatory PAN checksum flag | Validated against Indian Income Tax regex: `^[A-Z]{5}[0-9]{4}[A-Z]$`. |
| `aadhaar` | Corrupted String | VARCHAR | 12-digit Unique Identification | Stripped spaces/hyphens. Handled masked numbers (`XXXX-XXXX-5406`). |
| `is_valid_aadhaar` | *Engineered* | BOOLEAN | 12-digit format flag | Evaluated if cleaned Aadhaar consists of valid 12 digits. |
| `is_masked_aadhaar` | *Engineered* | BOOLEAN | Masked compliance flag | Identifies privacy-masked Aadhaar tokens. |
| `date_of_birth` | Mixed Strings / Epoch | TIMESTAMP | Customer Date of Birth | Unified dates with timestamps, epoch timestamps, and variable date formats. |
| `city` | Corrupted String | VARCHAR | City of residence | Normalized Indian city aliases (`BLR` ➔ `Bengaluru`, `Bombay` ➔ `Mumbai`, `Hyd` ➔ `Hyderabad`, `Dilli` ➔ `Delhi`, `ASR` ➔ `Amritsar`). |
| `state` | String | VARCHAR | State / UT of residence | Trimmed whitespace and converted to Title Case. |
| `monthly_income` | Corrupted String | DECIMAL(12,2) | Monthly reported income (INR) | Cleansed currency prefixes (`₹`, `INR`), handled `27.3k` shorthand multiplier (`27,300`). Missing values imputed using **Occupation-Specific Median Income**. |
| `occupation` | String | VARCHAR | Customer employment sector | Standardized casing; missing records marked as `Other`. |
| `signup_timestamp` | Mixed Strings | TIMESTAMP | Account creation timestamp | Parsed multi-format timestamps; nulls defaulted to conservative epoch. |
| `kyc_status` | Corrupted String | VARCHAR(10) | Verification compliance state | Standardized (`Done`, `Verified`, `V`, `KYC_DONE`, `Approved` ➔ `VERIFIED`; `Reject` ➔ `REJECTED`; `Pending` ➔ `PENDING`). |
| `risk_segment` | String | VARCHAR(10) | Customer risk tier | Normalized to `LOW`, `MEDIUM`, `HIGH`. Missing values classified based on KYC verification. |

---

## 3. Merchant Master Table (`dim_merchants`)
**Source File:** `track1_fintech_dataset_files/track1_merchants_master.csv`  
**Processed File:** `data/processed/clean_merchants.parquet` / `.csv`  
**Description:** Registered merchant profiles, industry categories, and declared ticket parameters.

| Column Name | Raw Data Type | Clean Data Type | Description | Cleaning & Transformation Strategy |
| :--- | :--- | :--- | :--- | :--- |
| `merchant_id` | Corrupted String | VARCHAR (PK) | Unique Merchant Identifier | Normalized to `MCH0000` (4-digit zero-padded). Deduplicated. |
| `merchant_name` | Corrupted String | VARCHAR | Business trading name | Cleansed special characters, collapsed whitespace, Title Case. |
| `mcc` | Corrupted String / Float | VARCHAR(4) | Merchant Category Code | Stripped `MCC-`, removed float zeros (`7011.0` ➔ `7011`), zero-padded. Defaulted missing to `9999`. |
| `merchant_category`| Corrupted String | VARCHAR | Business sector classification | Standardized underscores and mixed casing (`hotel_lodging` ➔ `Hotel Lodging`, `MEDICAL_STORE` ➔ `Medical Store`). |
| `business_type` | Corrupted String | VARCHAR | Legal entity structure | Harmonized into `{PRIVATE_LIMITED, SOLE_PROPRIETOR, PARTNERSHIP, INDIVIDUAL}`. |
| `city` | Corrupted String | VARCHAR | Operating city | Normalized via canonical Indian city mapping dictionary. |
| `state` | String | VARCHAR | Operating state | Cleaned whitespace and formatted to Title Case. |
| `onboarding_date` | Mixed Strings / Epoch | TIMESTAMP | Merchant onboarding date | Parsed multi-format timestamps. Missing values filled with earliest cohort date. |
| `settlement_account`| Corrupted String | VARCHAR | Payout bank account number | Retained masked (`XXXX9523`) and explicit bank account identifiers. |
| `merchant_status` | Corrupted String | VARCHAR(10) | Merchant operational state | Harmonized (`Active`, `A`, `Live`, `Enabled` ➔ `ACTIVE`; `Hold`, `SUSPENDED` ➔ `SUSPENDED`; `Disabled`, `I` ➔ `INACTIVE`). |
| `declared_avg_ticket_size` | Corrupted String | DECIMAL(10,2) | Declared average ticket (INR) | Removed currency symbols and negative signs. Missing values imputed via **Category-Specific Median Ticket Size**. |

---

## 4. Customer Disputes & Chargebacks (`fct_chargebacks`)
**Source File:** `track1_fintech_dataset_files/track1_chargebacks.json`  
**Processed File:** `data/processed/clean_chargebacks.parquet` / `.csv`  
**Description:** Consumer complaints, fraud claims, and payment reversal requests.

| Column Name | Raw Data Type | Clean Data Type | Description | Cleaning & Transformation Strategy |
| :--- | :--- | :--- | :--- | :--- |
| `complaint_id` | String | VARCHAR (PK) | Dispute Ticket Identifier | Normalized to uppercase; stripped whitespace. Deduplicated. |
| `txn_id` | String | VARCHAR (FK) | Disputed Transaction ID | Normalized to uppercase `TXN00000000`. |
| `user_id` | Corrupted String | VARCHAR (FK) | Disputing User Identifier | Normalized to `USR00000`. |
| `merchant_id` | Corrupted String | VARCHAR (FK) | Disputed Merchant Identifier | Normalized to `MCH0000` (e.g. raw integer `"3835"` ➔ `MCH3835`). |
| `transaction_timestamp` | Mixed Strings | TIMESTAMP | Original transaction time | Parsed across slashed, ISO, and epoch formats. |
| `reported_timestamp` | Mixed Strings / Epoch | TIMESTAMP | Dispute registration time | Parsed robustly into standard UTC Timestamp. |
| `bank_response_timestamp` | Mixed Strings | TIMESTAMP | Bank settlement response time| Parsed into standard UTC Timestamp. |
| `reporting_delay_days` | *Engineered* | FLOAT | Dispute latency (Days) | Calculated as `(reported_timestamp - transaction_timestamp) / 86400.0`. |
| `resolution_days` | *Engineered* | FLOAT | Bank resolution latency (Days)| Calculated as `(bank_response_timestamp - reported_timestamp) / 86400.0`. |
| `disputed_amount` | Corrupted String / Empty | DECIMAL(12,2) | Disputed sum in INR | Currency cleaned. Empty strings (`""`) cross-reconciled **directly from UPI Transactions amount**. |
| `reason_code` | Corrupted String | VARCHAR | Formal complaint taxonomy | Standardized into `{Merchant Not Delivered, Account Takeover / Compromised, Duplicate Debit, Unauthorized Transaction, Payment Denied by Merchant, Other Complaint}`. |
| `complaint_text` | String | TEXT | Raw narrative submitted by user | Preserved for context and NLP keyword extraction. |
| `severity` | Corrupted String | VARCHAR(10) | Urgency / loss classification | Harmonized (`Critical`, `Crit` ➔ `CRITICAL`; `H`, `High` ➔ `HIGH`; `Medium` ➔ `MEDIUM`; `Low` ➔ `LOW`). |
| `channel` | String | VARCHAR | Dispute filing channel | Normalized values (`IVR`, `Call Center`, `Web`, `Mobile App`). |
| `resolution_status` | Corrupted String | VARCHAR(15) | Case outcome | Standardized into `{CLOSED, IN_PROGRESS, PENDING, REJECTED}`. |

---

## 5. Analytical Views & Derived Risk Metrics

### A. Merchant Risk Scorecard (`v_merchant_risk_scorecard`)
- **`chargeback_volume_ratio_pct`**: $\frac{\text{Total Disputed Amount}}{\text{Total Processed Volume}} \times 100$
- **`dispute_rate_pct`**: $\frac{\text{Total Disputes}}{\text{Total Transactions}} \times 100$
- **`failure_rate_pct`**: $\frac{\text{Failed Transactions}}{\text{Total Transactions}} \times 100$
- **`composite_risk_score`**: Normalized index from 0 to 100 derived from:
  $$\text{Composite Risk} = \min\left(100.0, \; 0.4 \times \text{Chargeback Vol Ratio} + 0.3 \times \text{Failure Rate} + 0.3 \times \min(\text{Disputes}, 50)\right)$$

### B. Network Topology Graph (`fraud_rings.json`)
- **`degree_centrality`**: Relative connectedness of merchant or user nodes in transaction space.
- **`hub_risk_score`**: Identification of merchant aggregator hubs receiving disproportionate fund inflows from unverified KYC and disputed accounts.
