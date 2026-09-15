# Methodology

## 1. Project Overview

This project analyzes e-commerce user behavior using the funnel:

```text
Product View → Add to Cart → Purchase
```

The objective is to identify funnel bottlenecks, understand conversion differences across business segments, quantify revenue contribution, and identify actionable opportunities.

Python is used for large-scale processing and Power BI is used for business visualization.

## 2. Dataset

The project uses the October 2019 file from the **eCommerce Behavior Data from Multi-Category Store** dataset.

Full dataset scale:

- Event records: **42,448,764**
- Unique users: **3,022,290**
- Unique products: **166,794**
- Unique categories: **624**
- Period: **October 2019**

The raw CSV is approximately 5.25 GB and is processed in chunks rather than loaded completely into memory.

## 3. Data Loading Strategy

The raw dataset is read using Pandas in chunks of **500,000 rows**.

```text
Raw CSV
   ↓
500K-row chunk
   ↓
Process
   ↓
Next 500K-row chunk
   ↓
Repeat until complete
```

## 4. Data Cleaning

The cleaning process includes:

- `event_time` → UTC datetime
- `event_type` → categorical
- identifiers → integer
- `price` → floating-point numeric

Missing descriptive values are represented as `Unknown` for:

- `category_code`
- `brand`
- `user_session`

Rows are not removed solely because descriptive fields are missing.

## 5. Zero-Price Records

There were **68,673** zero-price records in the raw dataset:

- 68,523 views
- 150 cart events
- 0 purchases

They are retained in the event data but separated into the `$0` price band for price analysis.

## 6. Duplicate Handling

Exact duplicates are removed using all original event columns:

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

Only exact duplicates are removed. Legitimate repeated user behavior is retained.

Production result:

| Metric | Result |
|---|---:|
| Input rows | 42,448,764 |
| Output rows | 42,418,544 |
| Duplicates removed | 30,220 |
| Duplicate removal rate | 0.0712% |

A disk-backed SQLite index tracks event fingerprints across chunks.

## 7. Funnel Definition

The primary funnel is:

```text
View → Add to Cart → Purchase
```

Funnel conversion is based on **unique users**, not raw event counts.

A cart qualifies only after a previous view.

A funnel purchase qualifies only after a previous qualifying cart.

This prevents events from being counted as funnel progression when the required chronological sequence did not occur.

## 8. User-Level Funnel Construction

The raw event data is transformed into one consolidated state per user.

The user-level output contains:

- first view timestamp
- first qualifying cart timestamp
- first qualifying purchase timestamp
- funnel-stage flags
- total purchase-event count
- total purchase-event revenue

SQLite is used as a persistent state store because the same user can appear in multiple processing chunks.

## 9. Revenue Definition

The project distinguishes between **funnel progression** and **purchase-event revenue**.

`purchased` represents a qualifying chronological funnel purchase.

`purchase_count` and `purchase_revenue` represent all purchase events associated with the user, including users who may not satisfy the complete View → Cart → Purchase sequence.

Therefore, purchase revenue is reported as **purchase-event revenue**, not as a formally defined order-level AOV.

## 10. Category Analysis

Category analysis evaluates:

- View users
- Cart users
- Purchase users
- View → Cart conversion
- Cart → Purchase conversion
- View → Purchase conversion
- Purchase events
- Revenue

`category_code` is the primary category dimension.

A user may interact with multiple categories, so category-level user totals should not be summed to reproduce the overall unique-user total.

## 11. Brand Analysis

Brand analysis tracks funnel state at the **user + brand** level because a user can interact with multiple brands.

Metrics include:

- View users
- Cart users
- Purchase users
- Conversion rates
- Purchase events
- Revenue

## 12. Price Band Analysis

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

A user can appear in multiple price bands if they interact with products across different price ranges.

## 13. Time Analysis

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

Metrics include purchasing users, purchase events, and revenue.

These perspectives answer different business questions and are not treated as interchangeable.

## 14. Validation

Analytical outputs are validated before Power BI use.

Validation includes:

- required-column checks
- missing-value checks
- duplicate checks
- negative-metric checks
- funnel hierarchy checks
- conversion-rate calculations
- revenue consistency
- expected time buckets
- expected price bands
- reconciliation with overall totals

Required funnel hierarchy:

```text
Purchase Users ≤ Cart Users ≤ View Users
```

## 15. Analytical Outputs

```text
clean_events.csv
user_funnel.csv
category_analysis.csv
brand_analysis.csv
price_band_analysis.csv
time_analysis.csv
```

## 16. Power BI

The analytical outputs remain separate because they represent different grains:

```text
user_funnel          → User
category_analysis    → Category
brand_analysis       → Brand
price_band_analysis  → Price Band
time_analysis        → Time Bucket
```

They are used as separate analytical tables in the dashboard.

## 17. Overall Processing Flow

```text
Raw Dataset
    ↓
Chunk-Based Loading
    ↓
Data Cleaning
    ↓
Global Exact-Duplicate Removal
    ↓
Clean Event Dataset
    ↓
User Funnel Construction
    ↓
Category / Brand / Price Analysis
    ↓
Time Analysis
    ↓
Validation
    ↓
Power BI Dashboard
    ↓
Business Insights & Recommendations
```

## 18. Limitations

- The analysis covers October 2019 only.
- Observational data does not establish causality.
- High-traffic/low-conversion segments identify opportunities but do not prove why conversion is low.
- Price is analyzed at the event level, so users may appear in multiple price bands.
- `category_code` and `brand` contain missing values represented as `Unknown`.
- Time analysis uses UTC timestamps.
- Purchase-event revenue is not treated as formally defined order-level AOV because the project does not establish a unique order identifier.

## 19. Methodology Summary

The methodology prioritizes scalable processing, chronological funnel accuracy, transparent metric definitions, persistent state across chunks, validation before visualization, and separation of technical processing from business reporting.
