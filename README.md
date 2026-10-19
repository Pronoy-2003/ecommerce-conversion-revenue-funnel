# E-commerce Conversion & Revenue Funnel Analytics

**A large-scale e-commerce analytics project that processes 42.4 million
events to identify funnel drop-offs, revenue drivers, and conversion
opportunities using Python, SQLite, and Power BI.**

## Table of Contents

- [Overview](#overview)
- [Problem Statement](#problem-statement)
- [Dataset](#dataset)
- [Tools and Technologies](#tools-and-technologies)
- [Methods](#methods)
- [Key Insights](#key-insights)
- [Dashboard / Model / Output](#dashboard--model--output)
  - [Executive Funnel Overview](#1-executive-funnel-overview)
  - [Segment & Opportunity Analysis](#2-segment--opportunity-analysis)
- [How to Run This Project?](#how-to-run-this-project)
  - [Clone the repository](#1-clone-the-repository)
  - [Install dependencies](#2-install-dependencies)
  - [Download the dataset](#3-download-the-dataset)
  - [Run the processing pipeline](#4-run-the-processing-pipeline)
  - [Open the dashboard](#5-open-the-dashboard)
- [Results & Conclusion](#results--conclusion)
- [Future Work](#future-work)
- [GitHub Repository Structure](#github-repository-structure)
- [Author & Contact](#author--contact)


## Overview

This project analyzes the October 2019 customer journey: **Product View
→ Add to Cart → Purchase**. It transforms raw event logs into cleaned
analytical datasets, measures funnel conversion, compares categories,
brands, price bands, and time periods, and presents results in a
two-page Power BI dashboard.

## Problem Statement

E-commerce businesses receive many product interactions, but raw event
data does not clearly show where users abandon the purchase journey or
which segments offer the greatest opportunity. This project measures
funnel conversion, identifies drop-offs, compares segment performance,
analyzes time patterns, and highlights high-traffic categories with
below-benchmark conversion.

## Dataset

**Source:** [eCommerce Behavior Data from Multi-Category Store ---
Kaggle](https://www.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store)

-   **File:** `2019-Oct.csv`
-   **Period:** October 2019
-   **Raw records:** 42,448,764
-   **Cleaned records:** 42,418,544
-   **Unique users:** 3,022,290
-   **Unique products:** 166,794
-   **Raw file size:** Approximately 5.25 GB

The dataset includes event timestamps, event types, product/category
identifiers, category codes, brands, prices, user IDs, and session IDs.
The raw dataset is not included because of its size; download it from
Kaggle.

## Tools and Technologies

-   **Python, Pandas, NumPy:** Data processing, cleaning,
    transformation, and analysis
-   **SQLite:** Persistent duplicate tracking and user/segment state
    across chunks
-   **Power BI and DAX:** KPI calculations, dashboards, and
    visualization
-   **Jupyter Notebook:** Data understanding and exploratory work
-   **Git and GitHub:** Version control and project sharing

## Methods

1.  **Data understanding:** Reviewed schema, event distribution, missing
    values, prices, users, products, and sessions.
2.  **Chunk processing:** Read the large CSV in 500,000-row chunks to
    reduce memory use.
3.  **Data cleaning:** Standardized data types, filled missing
    descriptive values with `Unknown`, and added date, hour, weekday,
    and day-of-month features.
4.  **Duplicate removal:** Created event fingerprints and used a
    persistent SQLite index to detect duplicates within and across
    chunks. Removed 30,220 exact duplicates while retaining legitimate
    repeated behavior.
5.  **Chronological funnel:** Built one row per user and counted
    progression only when the order was View → Cart → Purchase.
6.  **Segment analysis:** Calculated funnel and revenue metrics by
    category, brand, and price band.
7.  **Time analysis:** Analyzed conversion by first-view time and actual
    purchase activity by purchase timestamp.
8.  **Validation:** Checked schemas, duplicate keys, funnel hierarchy,
    conversion calculations, expected buckets, and revenue/count
    consistency.
9.  **Dashboarding:** Created two Power BI pages for executive KPIs and
    segment-level opportunities.

## Key Insights

-   **Overall funnel:** View-to-Cart conversion was **11.14%**,
    Cart-to-Purchase was **58.35%**, and View-to-Purchase was **6.50%**.
    View → Cart was the main drop-off to investigate.
-   **Leading category:** `electronics.smartphone` generated
    approximately **\$157.03 million** in purchase-event revenue and had
    about **9.25%** View-to-Purchase conversion.
-   **Price bands:** The **\$100--\$250** band had the highest
    View-to-Purchase conversion at approximately **5.06%**.
-   **High-priced products:** The **\$2,000+** band had approximately
    **0.24%** View-to-Purchase conversion.
-   **Leading brands:** Apple generated approximately **\$111.2
    million**, Samsung **\$46.4 million**, and Xiaomi **\$9.2 million**
    in purchase-event revenue.
-   **Time patterns:** Tuesday had the strongest weekday first-view
    cohort conversion, while Wednesday recorded the highest weekday
    purchase revenue at approximately **\$37.06 million**.
-   **Revenue:** Total purchase-event revenue was approximately
    **\$229.93 million**.

*Revenue is purchase-event revenue, not order-level average order value
(AOV). Funnel purchasers are users who completed the chronological
funnel; purchase-event counts and revenue also include other purchase
events.*

## Dashboard / Model / Output

The Power BI dashboard contains two pages.

### 1. Executive Funnel Overview

-   Total users, cart users, funnel buyers, and purchase-event revenue
-   Funnel conversion rates
-   Top categories by revenue
-   View-to-Purchase conversion by price band
-   Purchase revenue by hour (UTC)

### 2. Segment & Opportunity Analysis

-   Top categories by View-to-Purchase conversion
-   Top brands by revenue
-   Revenue by price band
-   Purchase revenue by weekday
-   High-traffic / low-conversion category table

**Dashboard previews:**

![Executive Funnel Overview](screenshots/dashboard_overview.png)

![Segment & Opportunity
Analysis](screenshots/dashboard_opportunity_analysis.png)

**Power BI file:** `powerbi/ecommerce_funnel_dashboard.pbix`

**Main analytical outputs:** - `clean_events.csv` --- cleaned
event-level data - `user_funnel.csv` --- one row per user -
`category_analysis.csv` --- category metrics - `brand_analysis.csv` ---
brand metrics - `price_band_analysis.csv` --- price-band metrics -
`time_analysis.csv` --- time-based metrics

Additional documentation is available in `docs/`: `data_dictionary.md`,
`methodology.md`, `code_documentation.md`, and `business_insights.md`.

## How to Run This Project?

### 1. Clone the repository

``` bash
git clone <your-repository-url>
cd ecommerce-conversion-revenue-funnel
```

### 2. Install dependencies

``` bash
pip install -r requirements.txt
```

### 3. Download the dataset

Download `2019-Oct.csv` from the [Kaggle dataset
page](https://www.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store)
and place it in:

``` text
data/raw/2019-Oct.csv
```

The raw dataset is not stored in GitHub because of its size.

### 4. Run the processing pipeline

Run the scripts from the project root in this order, adjusting commands
to match your package layout:

1.  `src/process_raw_data.py`
2.  `src/funnel_analysis.py`
3.  `src/eda_analysis.py`
4.  `src/time_analysis.py`
5.  Run the validation scripts in `src/`.

The processing scripts use relative paths and persistent SQLite
databases. Ensure the expected folders exist and use the documented
working directory. See `docs/code_documentation.md` for implementation
details.

### 5. Open the dashboard

After generating the analytical CSV files, open
`powerbi/ecommerce_funnel_dashboard.pbix` in Power BI Desktop. If
prompted, update data-source paths to the generated CSV files.

## Results & Conclusion

The project converted more than **42.4 million raw events** into
validated user-level and segment-level datasets and a two-page Power BI
dashboard. It identified View → Cart as the main funnel bottleneck,
smartphones as the largest category revenue contributor, and meaningful
differences across price bands and time periods.

Recommended next steps are to investigate product-page and add-to-cart
friction, prioritize high-traffic categories with low conversion, and
test possible barriers for expensive products. These are opportunities
to investigate; observational data does not prove the causes of customer
behavior.

## Future Work

-   Analyze additional months to compare trends and seasonality.
-   Incorporate order IDs, marketing source, device, and customer
    attributes if available.
-   Investigate high-traffic/low-conversion categories in more detail.
-   Test product-page and checkout improvements using controlled
    experiments.
-   Improve automated pipeline orchestration and reporting.

## GitHub Repository Structure

```text
ecommerce-conversion-revenue-funnel/
│
├── data/                                           # Dataset notes and processed analytical outputs
│   ├── raw/                                        # Raw dataset is downloaded locally, not committed
│   │   ├── raw_data_README.md                      # Raw dataset download instructions
│   │   └── .gitkeep                                # Keeps the folder in Git
│   └── processed/
│       ├── eda/                                    # Aggregated analysis outputs
│       │   ├── brand_analysis.csv                  # Brand-level funnel and revenue metrics
│       │   ├── category_analysis.csv               # Category-level funnel and revenue metrics
│       │   ├── overall_funnel.csv                  # Overall funnel metrics
│       │   ├── price_band_analysis.csv             # Price-band funnel and revenue metrics
│       │   └── time_analysis.csv                   # Time-based funnel and purchase metrics
│       └── processed_data_README.md                # Notes about processed data
│
├── docs/                                           # Project documentation and analysis
│   ├── business_insights.md                        # Findings and recommendations
│   ├── code_documentation.md                       # Explanation of implementation
│   ├── data_dictionary.md                          # Dataset fields and definitions
│   ├── methodology.md                              # Processing and analysis methodology
│   └── project_architecture.png                    # Project architecture diagram
│
├── notebooks/                                      # Data exploration and analysis notebooks
│   ├── 01_data_understanding.ipynb                 # Initial data profiling
│   ├── 02_data_cleaning.ipynb                      # Cleaning exploration
│   ├── 03_funnel_construction.ipynb                # Funnel construction exploration
│   └── 04_funnel_eda.ipynb                         # Funnel exploratory analysis
│
├── powerbi/                                        # Power BI documentation and report location
│   └── README_PowerBI.md                           # Power BI report notes
│
├── screenshots/                                    # Dashboard preview images
│   ├── 01_executive_funnel_overview.png            # Executive funnel overview
│   └── 02_segment_&_opportunity_analysis.png       # Segment and opportunity analysis
│
├── src/                                            # Python processing and analysis scripts
│   ├── __init__.py                                 # Python package marker
│   ├── data_cleaning.py                            # Data type, missing-value, and datetime handling
│   ├── data_loader.py                              # Chunk-based raw data loading
│   ├── eda_analysis.py                             # Category, brand, and price-band analysis
│   ├── funnel_analysis.py                          # User-level chronological funnel
│   ├── process_raw_data.py                         # Cleaning and duplicate-removal pipeline
│   ├── time_analysis.py                            # Hourly and weekday analysis
│   ├── validate_brand_analysis.py                  # Brand output validation
│   ├── validate_price_analysis.py                  # Price-band output validation
│   └── validate_time_analysis.py                   # Time output validation
│
├── .gitignore                                      # Files and folders excluded from Git
├── LICENSE                                         # MIT license
├── README.md                                       # Project overview and instructions
└── requirements.txt                                # Python dependencies
```

## Author & Contact

**Pronoy Pryunkush Sonowal**\
Data Analyst Portfolio Project

-   **GitHub:** \[Add your GitHub profile or repository URL\]
-   **LinkedIn:** \[Add your LinkedIn profile URL\]
-   **Email:** \[Add your professional email address\]

------------------------------------------------------------------------

**Note:** The dataset covers October 2019 and uses UTC timestamps.
Results describe this historical dataset and should not be interpreted
as current market performance.
