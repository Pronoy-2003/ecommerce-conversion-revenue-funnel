# Data Dictionary

## Dataset

| Attribute | Value |
|---|---|
| Dataset | eCommerce Behavior Data from Multi-Category Store |
| Period | October 2019 |
| Raw file | `2019-Oct.csv` |
| Source | Kaggle dataset used for this portfolio project |

## Raw Dataset Columns

| Column | Description | Expected Data Type | Business Use |
|---|---|---|---|
| `event_time` | Timestamp when the user event occurred | datetime | Time and funnel analysis |
| `event_type` | Type of e-commerce interaction | categorical | Funnel stage identification |
| `product_id` | Unique identifier for the product | integer | Product-level analysis |
| `category_id` | Unique identifier for the product category | integer | Category analysis |
| `category_code` | Hierarchical product category classification | categorical | Category segmentation |
| `brand` | Product brand | categorical | Brand analysis |
| `price` | Product price associated with the event | numeric | Price and revenue analysis |
| `user_id` | Unique identifier for the user | integer | User-level funnel analysis |
| `user_session` | Identifier for the user's session | string | Session-level analysis |

## Event Types

| Event Type | Business Meaning | Funnel Role |
|---|---|---|
| `view` | User viewed a product | Discovery |
| `cart` | User added a product to cart | Consideration |
| `purchase` | User completed a purchase | Conversion |

## Primary Funnel

```text
View → Cart → Purchase
```

Funnel conversion is calculated using **unique users** rather than raw event counts.

A funnel user must progress chronologically through the required stages.

## Processed Analytical Datasets

| Dataset | Grain | Purpose |
|---|---|---|
| `user_funnel.csv` | User | Overall chronological user-level funnel |
| `category_analysis.csv` | Category | Category funnel and revenue analysis |
| `brand_analysis.csv` | Brand | Brand funnel and revenue analysis |
| `price_band_analysis.csv` | Price Band | Price-level funnel and revenue analysis |
| `time_analysis.csv` | Time Bucket + Analysis Type | Funnel cohort and purchase activity |

### `user_funnel.csv` Fields

| Column | Meaning |
|---|---|
| `user_id` | Unique user identifier |
| `viewed` | Whether the user recorded a qualifying view |
| `added_to_cart` | Whether the user recorded a qualifying cart action after a view |
| `purchased` | Whether the user recorded a qualifying purchase after a cart action |
| `first_view_time` | First qualifying view timestamp |
| `first_cart_time` | First qualifying cart timestamp |
| `first_purchase_time` | First qualifying funnel purchase timestamp |
| `purchase_count` | Total purchase events associated with the user |
| `purchase_revenue` | Total revenue from purchase events associated with the user |

## Price Bands

All monetary values in this project are presented in **USD**.

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

The `$0` band is kept separately because zero-price records are not treated as normal paid-product prices.

## Data Quality Notes

- `category_code` missing values are represented as `Unknown` in processed data.
- `brand` missing values are represented as `Unknown`.
- `user_session` missing values are represented as `Unknown`.
- Zero-price records are retained because they occur in view/cart events and do not generate purchase revenue.
- Exact duplicate event records are removed during production processing.
- Core identifiers contain no missing values in the full dataset.
