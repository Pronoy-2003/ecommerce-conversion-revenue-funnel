# Data Dictionary

## Dataset

**Dataset:** eCommerce Behavior Data from Multi-Category Store

**Period:** October 2019

**File:** `2019-Oct.csv`

## Columns

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

## Funnel

The primary funnel for this project is:

`View → Cart → Purchase`

Funnel conversion rates will be calculated using unique users rather than raw event counts.

## Data Quality Notes

- `category_code` contains missing values.
- `brand` contains missing values.
- `user_session` contains a very small number of missing values.
- `price` contains zero-price records.
- Duplicate records require further validation.
- Core identifiers such as `user_id`, `product_id`, and `category_id` contain no missing values in the full dataset.
