# Source Code Documentation

## E-commerce Conversion & Revenue Funnel Analytics

This document explains the Python source-code architecture used in the project, including what each file does, why it is used, and how the modules work together.

## 1. Source Code Architecture

```text
Raw CSV
   │
   ▼
data_loader.py
   │
   ▼
process_raw_data.py
   │
   ▼
clean_events.csv
   │
   ├───────────────────────┐
   ▼                       ▼
funnel_analysis.py     eda_analysis.py
   │                       │
   ▼                       ├── Category Analysis
user_funnel.csv            ├── Brand Analysis
   │                       └── Price Band Analysis
   │
   ▼
time_analysis.py
   │
   ▼
time_analysis.csv
   │
   ▼
Validation Scripts
   │
   ▼
Power BI / Business Analysis
```

The modules are separated by responsibility so that loading, cleaning, processing, analysis, and validation remain distinct.

## 2. `data_loader.py`

### Purpose

Provides reusable functionality for reading the large raw CSV file in chunks.

### Why it is used

The dataset contains more than 42 million event records. Loading the entire file into memory is inefficient, so the data is read in chunks of 500,000 rows.

### Main responsibility

```text
2019-Oct.csv
     ↓
Read 500,000 rows at a time
     ↓
Return chunk for processing
```

## 3. `data_cleaning.py`

### Purpose

Contains reusable functions for standardizing and cleaning event data.

### Main functions

#### `standardize_dtypes()`

Converts:

- `event_time` to UTC datetime
- `event_type` to categorical
- identifiers to integer
- `price` to floating-point numeric

#### `handle_missing_values()`

Replaces missing values with `Unknown` for:

- `category_code`
- `brand`
- `user_session`

#### `add_datetime_features()`

Creates:

- `event_date`
- `event_hour`
- `day_of_week`
- `day_of_month`

### Flow

```text
Raw chunk
   ↓
Standardize types
   ↓
Handle missing values
   ↓
Add datetime features
   ↓
Clean chunk
```

## 4. `process_raw_data.py`

### Purpose

Acts as the production pipeline for cleaning the raw dataset and creating the event-level processed dataset.

### Main responsibilities

1. Read raw data in chunks.
2. Standardize and clean each chunk.
3. Create fingerprints for complete event records.
4. Detect exact duplicates across the full dataset.
5. Keep the first occurrence of exact duplicates.
6. Write cleaned events to the processed layer.

### Duplicate definition

An exact duplicate uses all original event columns:

```text
event_time
event_type
product_id
category_id
category_code
brand
price
user_id
user_session
```

Only exact duplicates are removed. Legitimate repeated behavior is retained.

### SQLite usage

A SQLite database stores processed-event fingerprints, allowing duplicate detection across chunks without keeping the complete index in memory.

### Outputs

```text
data/processed/clean_events.csv
data/processed/duplicate_index.db
```

## 5. `funnel_analysis.py`

### Purpose

Transforms event-level data into a user-level chronological funnel.

```text
View → Add to Cart → Purchase
```

### Why it is used

Raw data contains individual events, while funnel analysis requires understanding how unique users progress through the purchase journey.

The module maintains funnel state for each user.

### Main fields

```text
user_id
viewed
added_to_cart
purchased
first_view_time
first_cart_time
first_purchase_time
purchase_count
purchase_revenue
```

### Chronological logic

A cart qualifies only after a previous view.

A funnel purchase qualifies only after a previous qualifying cart.

This ensures the funnel represents actual progression rather than simple event counting.

### SQLite usage

The same user can appear in many chunks:

```text
Chunk 1  → User A views
Chunk 20 → User A carts
Chunk 70 → User A purchases
```

SQLite stores previous user state so later chunks can continue from the correct state.

### Main function

`build_user_funnel()`

```text
Read clean events
      ↓
Process chunk
      ↓
Retrieve previous user state
      ↓
Apply chronological logic
      ↓
Update user state
      ↓
Repeat for all chunks
      ↓
Export user funnel
```

### Output

```text
data/processed/user_funnel.csv
```

Supporting state database:

```text
data/processed/user_funnel.db
```

## 6. `eda_analysis.py`

### Purpose

Creates segment-level funnel and revenue analysis for:

- Categories
- Brands
- Price Bands

### Category Analysis

**Grain: User + Category**

Metrics include:

- View users
- Cart users
- Purchase users
- Purchase events
- Revenue
- View → Cart conversion
- Cart → Purchase conversion
- View → Purchase conversion

Output:

```text
data/processed/eda/category_analysis.csv
```

### Brand Analysis

**Grain: User + Brand**

Funnel progression is tracked independently for each user-brand combination.

Output:

```text
data/processed/eda/brand_analysis.csv
```

### Price Band Analysis

Product interactions are grouped into:

```text
$0
$0–$50
$50–$100
$100–$250
$250–$500
$500–$1,000
$1,000–$2,000
$2,000+
```

The `$0` band is kept separate because zero-price records are not treated as normal paid-product prices.

Output:

```text
data/processed/eda/price_band_analysis.csv
```

## 7. `time_analysis.py`

### Purpose

Analyzes funnel performance and actual purchasing activity over time.

### Funnel Cohort Analysis

Users are grouped by the time of their **first product view**.

Source:

```text
user_funnel.csv
```

This measures eventual funnel conversion for users entering the funnel at different times.

### Purchase Activity Analysis

Actual purchase events are grouped by their **purchase timestamp**.

Source:

```text
clean_events.csv
```

Metrics include:

- Purchasing users
- Purchase events
- Revenue

### Important distinction

```text
First View Time
      ↓
Funnel Cohort Conversion

Purchase Time
      ↓
Actual Purchase Activity & Revenue
```

The two perspectives answer different business questions.

### Output

```text
data/processed/eda/time_analysis.csv
```

The final dataset contains 24 hourly funnel cohorts, 24 hourly purchase-activity buckets, 7 daily funnel cohorts, and 7 daily purchase-activity buckets: **62 rows total**.

## 8. Validation Scripts

Validation scripts provide quality control before analytical outputs are used in Power BI.

### `validate_brand_analysis.py`

Checks:

- required columns
- duplicate brands
- missing brands
- negative metrics
- funnel hierarchy
- conversion-rate calculations
- revenue consistency
- zero-cart cases

Required hierarchy:

```text
Purchase Users ≤ Cart Users ≤ View Users
```

### `validate_price_analysis.py`

Checks:

- expected price bands
- missing/unexpected bands
- duplicate bands
- negative metrics
- funnel hierarchy
- conversion rates
- revenue consistency
- zero-price behavior

### `validate_time_analysis.py`

Checks:

- required columns
- analysis types
- expected hourly/daily buckets
- duplicate time buckets
- negative metrics
- funnel hierarchy
- conversion-rate calculations
- reconciliation with overall funnel totals
- reconciliation with purchase-event totals

## 9. Why Chunk-Based Processing Is Used

The source dataset contains more than 42 million records.

Instead of loading everything into memory:

```text
42M+ rows
    ↓
Memory
```

the project processes:

```text
500K rows
    ↓
Process
    ↓
Store required state
    ↓
Next 500K rows
    ↓
Process
    ↓
Repeat
```

## 10. Why SQLite Is Used

SQLite acts as a temporary persistent state store during large-scale processing.

```text
duplicate_index.db
    → Processed event fingerprints

user_funnel.db
    → User funnel state

category_funnel.db
    → User-category state

brand_funnel.db
    → User-brand state

price_band_funnel.db
    → User-price-band state
```

These databases support processing and are not the final business-analysis layer.

## 11. Final Analytical Data Layer

| Dataset | Grain | Purpose |
|---|---|---|
| `clean_events.csv` | Event | Cleaned event-level data |
| `user_funnel.csv` | User | Overall user-level funnel |
| `category_analysis.csv` | Category | Category funnel and revenue |
| `brand_analysis.csv` | Brand | Brand funnel and revenue |
| `price_band_analysis.csv` | Price Band | Price-level funnel and revenue |
| `time_analysis.csv` | Time Bucket | Funnel cohort and purchase activity |

## 12. Complete Source-Code Flow

```text
2019-Oct.csv
     │
     ▼
data_loader.py
     │
     ▼
process_raw_data.py
     │
     ├── data_cleaning.py
     │
     ▼
clean_events.csv
     │
     ├─────────────────────────┐
     ▼                         ▼
funnel_analysis.py         eda_analysis.py
     │                         │
     ▼                         ├── Category
user_funnel.csv                ├── Brand
     │                         └── Price Band
     │
     ▼
time_analysis.py
     │
     ▼
time_analysis.csv
     │
     ▼
Validation Scripts
     │
     ▼
Python EDA / Power BI
```

## 13. Source-Code Responsibility Map

| File | Responsibility |
|---|---|
| `data_loader.py` | Read the large raw dataset in chunks |
| `data_cleaning.py` | Reusable data-cleaning functions |
| `process_raw_data.py` | Production cleaning and global deduplication |
| `funnel_analysis.py` | Build the chronological user-level funnel |
| `eda_analysis.py` | Create category, brand, and price-band analysis |
| `time_analysis.py` | Create funnel-cohort and purchase-activity time analysis |
| `validate_brand_analysis.py` | Validate brand analysis |
| `validate_price_analysis.py` | Validate price-band analysis |
| `validate_time_analysis.py` | Validate time analysis |

## 14. Design Principles

- **Modularity:** Each file has a clear responsibility.
- **Memory efficiency:** Large data is processed in chunks.
- **Persistent state:** SQLite maintains state across chunks.
- **Chronological accuracy:** Funnel stages follow the required event sequence.
- **Validation:** Analytical outputs are checked before downstream use.
- **Separation of concerns:** Processing, analysis, and visualization are kept separate.

## 15. Final Summary

The Python source code forms a complete data-processing pipeline:

```text
Load
  ↓
Clean
  ↓
Deduplicate
  ↓
Build User Funnel
  ↓
Create Segment Analysis
  ↓
Create Time Analysis
  ↓
Validate
  ↓
Analyze in Python / Power BI
```

This structure makes the project easier to understand, reproduce, maintain, and present as a professional Data Analyst portfolio project.
