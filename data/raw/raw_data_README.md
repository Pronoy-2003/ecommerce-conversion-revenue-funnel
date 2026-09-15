# Raw Data

## Dataset Used

This project uses the **eCommerce Behavior Data from Multi-Category Store** dataset published on Kaggle by **Michael Kechinov**.

The project uses **only the October 2019 data file (`2019-Oct.csv`)**.

### Dataset Source

- **Dataset:** eCommerce Behavior Data from Multi-Category Store
- **Source:** Kaggle
- **Publisher:** Michael Kechinov
- **Data period used:** October 2019
- **File used:** `2019-Oct.csv`
- **Raw file size:** approximately 5.67 GB on Kaggle
- **Raw records:** 42,448,764

**Kaggle dataset page:**

https://www.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store

**October 2019 data file:**

https://www.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store?select=2019-Oct.csv

> **Important:** Use `2019-Oct.csv` for this project. Do **not** use `2019-Nov.csv`. The project analysis, metrics, and dashboard are based exclusively on October 2019 data.

## About the Dataset

The dataset contains user behavior events from a large multi-category online store. Each row represents an event associated with a user, product, and session.

The available event types include:

- `view` — user viewed a product
- `cart` — user added a product to the shopping cart
- `remove_from_cart` — user removed a product from the shopping cart
- `purchase` — user purchased a product

The October 2019 file contains **42,448,764 event records** across **9 columns**.

## Raw Columns

| Column | Description |
|---|---|
| `event_time` | Timestamp when the event occurred, in UTC |
| `event_type` | Type of user event |
| `product_id` | Product identifier |
| `category_id` | Product category identifier |
| `category_code` | Product category taxonomy/code, when available |
| `brand` | Brand name, when available |
| `price` | Product price at the time of the event |
| `user_id` | Permanent user identifier |
| `user_session` | Temporary session identifier |

## Data Source and Attribution

The dataset was collected by the **Open CDP project** and is published on Kaggle by Michael Kechinov. The Kaggle dataset documentation requests that users mention the dataset source and **REES46 Marketing Platform** when using the data in their work.

Source:

https://www.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store

## Why the Raw File Is Not Included in This Repository

The `2019-Oct.csv` file is several gigabytes in size, so the raw dataset is **not uploaded to GitHub**.

Instead, this folder contains this `README.md` so that anyone cloning the project can:

1. Open the Kaggle dataset link.
2. Download `2019-Oct.csv`.
3. Place it in:
   `data/raw/2019-Oct.csv`
4. Run the project processing pipeline.

## Expected Raw Data Location

```text
data/
└── raw/
    ├── README.md
    └── 2019-Oct.csv
```

## Dataset Scope for This Project

The analysis is restricted to:

**October 1, 2019 → October 31, 2019**

The project does not use November 2019 or any later monthly files.

The raw October dataset is processed using chunk-based Python/Pandas workflows because of its large size.

## Project Funnel

The raw event data is transformed into a chronological e-commerce funnel:

```text
Product View
      ↓
Add to Cart
      ↓
Purchase
```

The project focuses on:

- Funnel conversion
- Funnel drop-off
- Category performance
- Brand performance
- Price-band conversion
- Revenue analysis
- Time-based conversion and purchase activity

## Citation / Reference

If you reuse this project or dataset, please refer to the original Kaggle dataset:

https://www.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store

This repository does not redistribute the original raw dataset.
