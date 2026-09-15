# 🧠 Complete Project Explanation — For Beginners

> **If you're not from a Data Science background, this document is written specifically for you.**
> It explains everything — what the hackathon is, what the data means, what problems exist in the data, and exactly how we solved them — in plain English.

---

## 📌 Table of Contents

1. [What Is This Hackathon?](#-what-is-this-hackathon)
2. [The Real-World Problem We're Solving](#-the-real-world-problem-were-solving)
3. [What Data Did We Get?](#-what-data-did-we-get-the-4-files)
4. [Why Is The Data So Messy?](#-why-is-the-data-so-messy)
5. [How Are The Files Connected?](#-how-are-the-files-connected)
6. [What Were We Expected To Do?](#-what-were-we-expected-to-do-the-task)
7. [How We Solved It — Step By Step](#-how-we-solved-it--step-by-step)
8. [What The Dashboard Shows](#-what-the-dashboard-shows)
9. [Key Discoveries We Made](#-key-discoveries-we-made)
10. [Tools & Technologies Used](#-tools--technologies-used)
11. [Project File Structure](#-project-file-structure)
12. [Scoring & Evaluation Criteria](#-scoring--evaluation-criteria)

---

## 🏆 What Is This Hackathon?

This is the **TransOrg AgentIQ Datathon** — a data science competition organized by TransOrg Analytics and Pickl.AI. Think of it like a coding contest, but instead of writing algorithms, you're given **real-world messy data** and asked to:

1. **Clean it up** (make it usable)
2. **Analyze it** (find patterns and insights)
3. **Build a dashboard** (visualize findings)
4. **Build an AI agent** (bonus: answer questions in plain English)

We chose **Track 1: FinTech & BFSI** — which focuses on **UPI digital payments, fraud detection, and merchant risk analysis** for an imaginary National Payments Authority (like NPCI in India).

---

## 🏦 The Real-World Problem We're Solving

### Imagine you run India's payment system (like UPI/Google Pay/PhonePe)...

Every day, millions of people send money to merchants (shops, restaurants, online stores). But bad things happen:

### 🔴 Problem 1: Fraud Rings
Some criminals create **fake customer accounts** (with fake PAN cards, fake Aadhaar numbers) and use them to send money to **fake merchant accounts** they also control. They move money in circles to launder it:

```
Fake User A → Fake Merchant 1 → Fake User B → Fake Merchant 2 → Back to Fake User A
```

This makes dirty money look clean. It's called **circular money laundering**.

### 🔴 Problem 2: Rogue Merchants
A merchant signs up saying they're a small grocery shop with average transactions of ₹500. But suddenly, they start processing huge transactions of ₹25,000 each. Then customers start complaining: "I never made this payment!" or "I paid but never received the product!"

These are **compromised or rogue merchants**.

### 🔴 Problem 3: Chargebacks & Disputes
When a customer says "this transaction was fraud" or "I didn't get my product", they file a **chargeback** (complaint). The bank has to investigate and potentially return the money. If a merchant has lots of chargebacks, they're probably doing something shady.

### 🔴 Problem 4: Fake Identities (KYC Fraud)
**KYC** stands for "Know Your Customer" — it's a verification process where you prove who you are (using PAN card, Aadhaar, etc.). Some criminals create accounts with **fake or incomplete KYC**, use them for fraud, and disappear.

### Our Job:
Build a system that can **detect all of these problems** by analyzing payment data, customer records, merchant records, and complaint records.

---

## 📁 What Data Did We Get? (The 4 Files)

We received 4 data files simulating real payment system logs. Here's what each one contains:

---

### File 1: `track1_upi_transactions.csv` — The Payment Records
**What it is:** A log of every UPI payment that happened. Think of it like a bank statement for the entire payment network.

**20,400 rows** (each row = one payment transaction)

| Column | What It Means | Example (Raw) |
|:-------|:-------------|:--------------|
| `txn_id` | Unique ID for each payment | `TXN00011869` |
| `timestamp` | When the payment happened | `2026-01-15 00:11:30` or `1770063471` (messy!) |
| `user_id` | Who sent the money (customer) | `USR45826` |
| `merchant_id` | Who received the money (shop/business) | `MCH7045` |
| `amount` | How much money (in ₹) | `15722.34` or `Rs. 6362.9` or `₹16,466.93` (messy!) |
| `utr` | Unique Transaction Reference — a tracking number from the bank | `UTR6498104698` |
| `mcc` | Merchant Category Code — what type of business (grocery, hotel, etc.) | `5411` or `05411` (messy!) |
| `status` | Did the payment succeed or fail? | `SUCCESS`, `COMPLETED`, `S`, `TXN_FAILED`, `Declined` (messy!) |

**Why it matters:** This is the core data. Every analysis we do starts here — how much money is flowing, where it's going, what's failing, what's suspicious.

---

### File 2: `track1_kyc_records.csv` — Customer Identity Records
**What it is:** Information about every customer (person) who uses the payment system. This is their identity verification data.

**36,400 rows** (each row = one customer)

| Column | What It Means | Example (Raw) |
|:-------|:-------------|:--------------|
| `user_id` | Customer's unique ID | `USR16112` or `USR 45454` or `usr22494` (messy!) |
| `full_name` | Customer's name | `Dhriti Deshmukh` |
| `pan` | PAN card number (tax ID in India) | `SEJAA8194O` or `CACWZ 2722 S` (messy!) |
| `aadhaar` | Aadhaar number (national ID) | `715658320763` or `XXXX-XXXX-5406` (masked) |
| `date_of_birth` | When they were born | Various formats |
| `city` | Where they live | `Bombay`, `BLR`, `kolkata`, `Dilli` (messy!) |
| `state` | Their state | `Maharashtra` |
| `monthly_income` | How much they earn monthly | `35119` or `27.3k` or `₹11,214` (messy!) |
| `occupation` | Their job | `Retired`, `Student`, `Salaried` |
| `kyc_status` | Are they verified? | `Verified`, `Done`, `Pending`, `APPROVED` (messy!) |
| `risk_segment` | How risky are they? | `LOW`, `medium`, `High` (messy casing!) |

**Why it matters:** If a customer has a **rejected KYC** (meaning their identity couldn't be verified), and they're involved in lots of disputed transactions, they're likely a fraudster using a fake identity.

---

### File 3: `track1_merchants_master.csv` — Business/Shop Records
**What it is:** A registry of every merchant (business) that accepts payments through the system.

**6,210 rows** (each row = one business)

| Column | What It Means | Example |
|:-------|:-------------|:--------|
| `merchant_id` | Merchant's unique ID | `MCH2849` or `mch2849` or `MCH-2637` (messy!) |
| `merchant_name` | Business name | `Sharma Electronics` |
| `mcc` | Category code | `5411` or `MCC-7011` (messy!) |
| `merchant_category` | What kind of business | `Grocery`, `Hotel Lodging` |
| `business_type` | How big is the business | `Small`, `Large`, `Enterprise` |
| `city` / `state` | Location | `Mumbai`, `Maharashtra` |
| `merchant_status` | Are they active? | `Active`, `A`, `Live`, `SUSPENDED`, `Hold` (messy!) |
| `declared_avg_ticket_size` | What they *said* their average transaction would be | `₹500` |
| `onboarding_date` | When they joined the platform | Various formats |

**Why it matters:** If a merchant declared their average transaction would be ₹500, but they're actually processing ₹25,000 transactions — **that's a red flag**. They may be processing fraudulent transactions.

---

### File 4: `track1_chargebacks.json` — Customer Complaints
**What it is:** Every complaint filed by a customer saying "this payment was wrong". This is in JSON format (a different data format than CSV).

**2,884 complaint records**

| Field | What It Means | Example |
|:------|:-------------|:--------|
| `complaint_id` | Unique ID for the complaint | `CBK0002082` |
| `txn_id` | Which transaction is being disputed | `TXN00004325` |
| `user_id` | Who filed the complaint | `usr97580` (messy!) |
| `merchant_id` | Which merchant is accused | `mch1127` (messy!) |
| `disputed_amount` | How much money is disputed | `""` (empty!), `Rs. 7,039` (messy!) |
| `reason_code` | Why they're complaining | `Merchant Not Delivered`, `Unauthorized Transaction` |
| `complaint_text` | Their description | `"Customer says amount was debited twice."` |
| `resolution_status` | Has it been resolved? | `CLOSED`, `OPEN`, `In Progress` |
| `severity` | How serious is it? | `Critical`, `High`, `Medium` |
| `reported_timestamp` | When they complained | `02-01-2026` |
| `bank_response_timestamp` | When the bank responded | `2026-02-10 03:19:10` |

**Why it matters:** Chargebacks cost money. If a merchant has 50 chargebacks but only 100 transactions, that's a **50% complaint rate** — clearly something is very wrong with that merchant.

---

## 🤯 Why Is The Data So Messy?

**This is on purpose!** In the real world, data is never clean. Different systems, different people, and different time periods create inconsistencies. The hackathon intentionally made the data messy to test if you can handle real-world challenges:

### Examples of Mess in Our Data:

| Problem | What It Looks Like | What It Should Be |
|:--------|:-------------------|:------------------|
| **Same user, different formats** | `USR16112`, `USR 45454`, `usr22494`, `usr_64308` | All should be `USR16112` format |
| **Same merchant, different formats** | `MCH2849`, `mch2849`, `MCH-2637`, `MCH 2430` | All should be `MCH2849` format |
| **Money with symbols** | `Rs. 6362.9`, `₹16,466.93`, `INR 13,312`, `27.3k` | Just the number: `6362.9` |
| **Dates in 5+ formats** | `2026-01-15 00:11:30`, `1770063471` (Unix timestamp!), `03-10-2026 09:27:31 PM`, `25/02/2026` | One consistent format |
| **Status means the same thing** | `SUCCESS`, `Success`, `COMPLETED`, `S`, `TXN_SUCCESS` | All should be `SUCCESS` |
| **City name variations** | `Bombay` vs `Mumbai`, `BLR` vs `Bangalore`, `Dilli` vs `Delhi` | One standard name |
| **Empty/missing values** | Disputed amount = `""` (empty string) | Need to look it up from the transaction |
| **Duplicates** | Same transaction appearing 2-3 times | Keep only one copy |

### The Golden Rule:
> **You CANNOT just delete messy rows.** The judges specifically said: *"Dropping a large percentage of data without justification should be penalized."* You must **fix** the data, not throw it away.

---

## 🔗 How Are The Files Connected?

The 4 files are **linked together** through shared IDs (like a relational database):

```
                    ┌──────────────────────┐
                    │   KYC RECORDS        │
                    │   (Customer Info)    │
                    │   Key: user_id       │
                    └──────────┬───────────┘
                               │
                               │ user_id
                               ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  CHARGEBACKS     │◄───│  TRANSACTIONS    │───►│  MERCHANTS       │
│  (Complaints)    │    │  (Payments)      │    │  (Businesses)    │
│  Key: complaint_id│   │  Key: txn_id     │    │  Key: merchant_id│
│  Links: txn_id,  │    │  Links: user_id, │    │                  │
│  user_id,        │    │  merchant_id     │    │                  │
│  merchant_id     │    │                  │    │                  │
└──────────────────┘    └──────────────────┘    └──────────────────┘
```

**Example of how they connect:**
- Transaction `TXN00004325` was made by user `USR97580` to merchant `MCH1127`
- To know if `USR97580` is verified, we look them up in the KYC records
- To know if `MCH1127` is a suspicious merchant, we check the merchant records
- Complaint `CBK0002082` references `TXN00004325`, so we can link the complaint back to the user, merchant, and original transaction

**But there's a catch:** The IDs in different files don't always match! The chargeback file might say `usr97580` (lowercase) while the KYC file says `USR97580` (uppercase). So we first need to **standardize all IDs** before we can link the files.

---

## 📋 What Were We Expected To Do? (The Task)

The hackathon had **4 evaluation gates** (stages):

### Gate 1: Documentation (10 points + 10 bonus)
- Write a clear `README.md` explaining the project
- Create a `DATA_DICTIONARY.md` explaining every field
- Show proof that you cleaned the data properly (`AUDIT_PROOF.md`)
- Show raw vs. clean row counts — prove you didn't just delete data

### Gate 2: Data Cleaning & Rescue (30 points + 10 bonus)
- Fix all the messy data (IDs, dates, currencies, statuses)
- Handle missing values intelligently (don't just delete!)
- Remove duplicates
- Make sure the 4 files can be properly linked together
- Make the pipeline reproducible (anyone can re-run it)

### Gate 3: Dashboard & Visualization (40 points + 10 bonus)
- Build an interactive dashboard showing:
  - How many transactions happened? How much money flowed?
  - What's the failure rate? Which merchants are risky?
  - Network graphs showing suspicious connections
  - KYC compliance analysis

### Gate 4: Architecture & AI Agent (30 points + 30 bonus)
- Use a proper data warehouse (DuckDB) with organized tables
- Detect fraud rings using graph/network analysis
- **Bonus:** Build an AI agent that can answer questions in plain English and create charts automatically

**Total possible score: 140 points** (100 base + 40 bonus)

---

## 🛠️ How We Solved It — Step By Step

### Step 1: Set Up the Environment
We set up Python (3.10 or newer) and installed all required libraries via `requirements.txt`.

### Step 2: Data Rescue Pipeline (`pipeline/clean_pipeline.py`)
This is the biggest and most important script. It reads all 4 raw data files and fixes every problem:

**For Transactions:**
- Stripped currency symbols (`₹`, `Rs.`, `INR`, commas) from amounts → got pure numbers
- Converted `27.3k` → `27300`
- Parsed 5 different date formats into one standard format
- Normalized 9 status variations into 3: `SUCCESS`, `FAILED`, `PENDING`
- Standardized all user IDs to `USR#####` and merchant IDs to `MCH####`
- Flagged negative amounts as reversals instead of deleting them
- Flagged missing UTR values (turns out these correlate with fraud!)
- Removed 400 exact duplicates

**For KYC Records:**
- Standardized user IDs (removed spaces, underscores, fixed casing)
- Cleaned PAN and Aadhaar formats
- Expanded `27.3k` → `27300` for income
- Mapped city aliases (`Bombay` → `Mumbai`, `BLR` → `Bangalore`)
- For missing incomes: used the **median income of their occupation** (e.g., if a Student's income was missing, we used the median income of all Students)
- Removed 7,480 duplicate records

**For Merchants:**
- Standardized merchant IDs
- Cleaned MCC codes (removed `MCC-` prefix, fixed decimals)
- Normalized status: `Active`/`A`/`Live`/`Enabled` → `ACTIVE`
- For missing ticket sizes: used the **median ticket of their category**
- Removed 1,867 duplicates

**For Chargebacks:**
- Parsed JSON format
- Standardized IDs to match other tables
- When disputed amount was empty, **looked it up from the transaction table**
- Calculated `reporting_delay_days` (how long the customer waited to complain)
- Removed 84 duplicates

**Result:** 65,894 raw rows → 56,063 clean rows. **Zero unjustified drops.** Every single row was either kept and cleaned, or removed only because it was an exact duplicate.

### Step 3: Analytics Warehouse (`pipeline/analytics_store.py`)
Loaded all clean data into **DuckDB** (a fast in-memory database) and created pre-computed analytical views:

- **Daily Trends:** Transaction volume, success/failure counts per day
- **Category Summary:** Which merchant categories have the most chargebacks?
- **Merchant Risk Scorecard:** A 0-100 risk score for every merchant combining chargeback ratio, failure rate, and dispute frequency
- **KYC Risk Analysis:** How do verified vs. unverified customers compare in terms of fraud?
- **Hourly Heatmap:** When (hour and day) do failures and fraud spike?
- **City Analysis:** Which cities have the most fraud?
- **Velocity Anomalies:** Users with suspiciously high transaction frequency (Z-score detection)
- **Resolution Analysis:** How long does it take to resolve different types of complaints?

### Step 4: Fraud Ring Detection (`pipeline/graph_detector.py`)
Built a **network graph** where:
- Each **customer** is a dot (node)
- Each **merchant** is a dot (node)
- Each **transaction** is a line connecting them (edge)

Then analyzed the network to find:
- **High-centrality merchants** receiving money from many disputed/unverified users → likely fraud hubs
- **Connected clusters** of suspicious accounts operating together → fraud rings
- Result: Found **15 high-risk merchant hubs** and **5 fraud clusters**

### Step 5: Interactive Dashboard (`dashboard/app.py`)
Built a web-based dashboard using **Streamlit** with 6 tabs showing all our findings interactively.

### Step 6: AI Agent (`dashboard/agent/graph_agent.py`)
Built an AI agent that understands 12 different types of questions in plain English and automatically:
1. Translates the question into a SQL query
2. Picks the best chart type (Bar, Line, Donut, Scatter)
3. Creates the chart
4. Writes an executive summary of the finding

---

## 📊 What The Dashboard Shows

The dashboard at `http://localhost:8501` has **6 tabs**:

### Tab 1: Executive KPIs
- **5 big metric cards** showing: Total Volume (₹25 Cr), Average Ticket (₹12,500), Failure Rate (8.05%), Disputed Volume (₹88.9 Lakh), Chargeback Loss Ratio (3.56%)
- **Red Risk Alert** banner (triggered because failure rate > 7% and chargeback ratio > 3%)
- **Line charts** showing daily transaction volume trends
- **Heatmap** showing which hours and days have the most failures (useful to detect automated bot attacks that happen at night)
- **Anomaly Detection** scatter plot flagging users with abnormal transaction speed

### Tab 2: Merchant Risk Center
- **Scatter plot** comparing what merchants *declared* their average ticket would be vs. what they *actually* processed (merchants above the diagonal line are suspicious)
- **Bar chart** showing which business categories have the most chargebacks
- **League table** ranking the 25 riskiest merchants with their composite risk scores

### Tab 3: Fraud Ring Graph
- **Interactive network visualization** — you can hover over nodes to see details
- Color-coded: blue = normal user, red = disputed user, orange = merchant, dark red = disputed merchant
- Shows the connections between suspicious accounts
- Table of the **15 most suspicious merchant hubs**

### Tab 4: KYC & Identity Risk
- Charts comparing **verified vs. unverified customers** — unverified ones have 3.8x more disputes!
- Table of the **top 20 most repeatedly disputed customers**

### Tab 5: AI Agent (Bonus)
- **12 preset questions** you can click
- Free-text input for your own questions
- Automatically generates a chart + written analysis
- Shows the SQL query it used (transparency)

### Tab 6: Audit Proof
- Visual **Data Quality Scorecard** proving all our cleaning was successful
- Bar charts showing retention rate and null reduction per table
- Expandable sections showing every transformation applied to each table

---

## 🔍 Key Discoveries We Made

1. **Missing UTR = Fraud Signal:** Transactions without a UTR (bank tracking number) have a **4.2x higher dispute rate**. This makes sense — if the bank didn't generate a tracking number, the transaction likely failed silently and was disputed.

2. **Ticket Size Inflation:** Rogue merchants declared low average tickets (₹500-1,000) during onboarding but processed burst transactions of ₹15,000-25,000. These merchants account for **over 70% of total disputed volume**.

3. **Unverified KYC = Higher Fraud:** Customers with rejected or pending KYC verification have a dispute ratio **3.8x higher** than verified customers.

4. **Delayed Reporting = Account Takeover:** Complaints about unauthorized access have an average reporting delay of **9.4 days** — by the time the victim notices, the fraudster has already withdrawn the money.

5. **Late-Night Fraud Window:** The temporal heatmap reveals higher failure rates between 00:00-05:00 — this is when automated fraud bots are most active.

---

## 🔧 Tools & Technologies Used

| Tool | What It Does | Why We Used It |
|:-----|:-------------|:---------------|
| **Python 3.10** | Programming language | Industry standard for data science |
| **Pandas** | Data manipulation library | Reads CSVs, cleans data, transforms tables |
| **NumPy** | Math library | Statistical calculations |
| **DuckDB** | In-memory analytical database | Runs SQL queries on our data blazingly fast |
| **Plotly** | Interactive chart library | Creates beautiful, hoverable charts |
| **Streamlit** | Dashboard framework | Turns Python scripts into web apps with zero HTML |
| **NetworkX** | Graph analysis library | Builds and analyzes the fraud ring network |
| **Python** | Runtime & Package Ecosystem | Standard Python runtime using pip for dependency management |

---

## 📂 Project File Structure

```
Data/
│
├── data/raw/                         ← The original RAW data (untouched)
│   ├── track1_upi_transactions.csv
│   ├── track1_kyc_records.csv
│   ├── track1_merchants_master.csv
│   ├── track1_chargebacks.json
│   └── track1_dataset_notes.txt
│
├── pipeline/                          ← The data processing scripts
│   ├── clean_pipeline.py              ← STEP 2: Cleans all 4 raw files
│   ├── analytics_store.py             ← STEP 3: Builds DuckDB warehouse + views
│   └── graph_detector.py              ← STEP 4: Detects fraud rings
│
├── dashboard/                         ← The web dashboard
│   ├── app.py                         ← STEP 5: The main dashboard (6 tabs)
│   └── agent/
│       └── graph_agent.py             ← STEP 6: The AI question-answering agent
│
├── data/processed/                    ← Clean output data
│   ├── clean_transactions.parquet     ← Cleaned payment records
│   ├── clean_kyc.parquet              ← Cleaned customer records
│   ├── clean_merchants.parquet        ← Cleaned merchant records
│   ├── clean_chargebacks.parquet      ← Cleaned complaint records
│   ├── fintech_warehouse.duckdb      ← The analytical database
│   ├── fraud_rings.json               ← Fraud network analysis results
│   └── audit_proof.json               ← Automated audit log
│
├── run_all.py                         ← One-click: runs Step 2+3+4 automatically
├── requirements.txt                   ← List of Python packages needed
├── README.md                          ← Professional project documentation
├── DATA_DICTIONARY.md                 ← Explains every data field
├── AUDIT_PROOF.md                     ← Proves our data cleaning was thorough
├── tests/                             ← Test suite & verify_dashboard.py
└── docs/                              ← Documentation & problem statement PDF
```

### How to Run Everything:
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the entire data pipeline (clean → warehouse → fraud detection)
python run_all.py

# 3. Launch the dashboard
streamlit run dashboard/app.py
```

---

## 📝 Scoring & Evaluation Criteria

| Gate | What They Judge | Max Points | Our Claim |
|:-----|:---------------|:-----------|:----------|
| **Gate 1** | README, Data Dictionary, Audit Proof | 10 + 10 bonus | ✅ Full compliance |
| **Gate 2** | Data cleaning quality, no lazy drops, reproducibility | 30 + 10 bonus | ✅ 85% retention, 0 lazy drops |
| **Gate 3** | Interactive dashboard, business insights, storytelling | 40 + 10 bonus | ✅ 6 tabs, dark mode, heatmaps, anomaly detection |
| **Gate 4** | Architecture (DuckDB), graph intelligence, AI agent | 30 + 30 bonus | ✅ 9 views, fraud ring detector, 12 agent intents |
| **Total** | | **140** | **Target: 140/140** |

### Critical Rules We Followed:
- ❌ Never deleted data just because it was messy
- ✅ Fixed every format issue with regex and intelligent parsing
- ✅ Used median imputation (not deletion) for missing values
- ✅ Documented every transformation in the audit proof
- ✅ Made everything reproducible with a single `python run_all.py` command

---

> **Bottom Line:** We took 4 chaotic, messy data files from a simulated payment system. We cleaned every mess without losing a single valid record. We built a database, detected fraud networks, created a beautiful interactive dashboard, and added an AI agent that can answer business questions — all in one cohesive, reproducible system.
