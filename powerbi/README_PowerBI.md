# Power BI Dashboard — E-commerce Conversion & Revenue Analytics

## 1. Overview

This folder contains the **Power BI dashboard** for the E-commerce Conversion & Revenue Analytics project.

The dashboard analyzes customer behavior across the funnel:

**Product View → Add to Cart → Purchase**

The objective is to identify:

- Where users drop out of the purchase funnel
- How efficiently users convert from viewing to purchasing
- Which categories and brands generate the most revenue
- Which product price bands have stronger conversion
- How purchase revenue varies by day and hour
- Categories with high traffic but weak purchase conversion

---

## 2. Dashboard Pages

### Page 1 — Executive Funnel Overview

**Purpose:** Provide a high-level view of e-commerce performance.

#### KPI Cards

- **Total Users**
- **Cart Users**
  - View → Cart Rate
- **Buyers**
  - Cart → Purchase Rate
- **Purchase Revenue**
  - Revenue per Purchasing User

#### Visuals

1. **Purchase Funnel**
   - Viewed
   - Added to Cart
   - Purchased

2. **Top 10 Categories by Revenue**
   - Identifies the categories contributing the most revenue.

3. **View → Purchase Conversion by Price Band**
   - Shows how conversion varies across product price ranges.

4. **Purchase Revenue by Hour (UTC)**
   - Shows the hourly distribution of purchase revenue.

---

### Page 2 — Segment & Opportunity Analysis

**Purpose:** Identify areas where the business can focus for higher conversion and revenue.

#### Visuals

1. **Top Categories by View → Purchase Conversion**
   - Highlights categories with strong conversion performance.

2. **Top 10 Brands by Revenue**
   - Identifies the highest-revenue brands.

3. **Revenue by Price Band**
   - Shows revenue contribution across different price ranges.

4. **Purchase Revenue by Day**
   - Shows the distribution of revenue across weekdays.

5. **High-Traffic / Low-Conversion Categories**
   - Identifies categories receiving significant traffic but producing weak purchase conversion.
   - Conditional formatting is used on the View → Purchase % column to make weak conversion areas easier to identify.

---

## 3. Data Sources

The dashboard is based on the **eCommerce Behavior Data from Multi-Category Store** dataset created by Michael Kechinov and collected by the Open CDP project.

### Primary Raw Dataset

The project uses:

**`2019-Oct.csv` — October 2019**

The October file contains approximately **42.45 million e-commerce event records** and includes:

- `event_time`
- `event_type`
- `product_id`
- `category_id`
- `category_code`
- `brand`
- `price`
- `user_id`
- `user_session`

The dataset contains events such as:

- `view`
- `cart`
- `remove_from_cart`
- `purchase`

**Dataset source:**

https://www.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store

The project specifically uses the **October 2019** data file, not November 2019 data.

---

## 4. Data Used by Power BI

Because the original October dataset is several GB in size, the Power BI model does not rely on uploading the raw CSV directly to GitHub.

The project uses processed datasets generated during the data preparation stage.

### `clean_events.csv`

A cleaned and processed version of the October 2019 event data.

It is used as the basis for event-level analysis and downstream transformations.

### `user_funnel.csv`

A user-level funnel dataset derived from the cleaned event data.

It supports analysis such as:

- Viewed Users
- Cart Users
- Purchasing Users
- View → Cart Conversion
- Cart → Purchase Conversion
- View → Purchase Conversion
- Revenue
- User-level funnel behavior

### Power BI Analysis Tables

The Power BI model also contains prepared analytical tables used by the dashboard, including:

- `funnel`
- `user_funnel`
- `category_analysis`
- `brand_analysis`
- `price_band_analysis`
- `time_analysis`
- `measures_table`

These tables support the dashboard visuals and KPI calculations.

---

## 5. Key Metrics

The dashboard focuses on the following business metrics:

### Funnel Metrics

**View → Cart Rate**

Measures the percentage of viewed users who added a product to their cart.

**Cart → Purchase Rate**

Measures the percentage of cart users who completed a purchase.

**View → Purchase Rate**

Measures the percentage of viewed users who ultimately purchased.

### Revenue Metrics

**Purchase Revenue**

Total revenue generated from purchase events.

**Revenue per Purchasing User**

Total purchase revenue divided by the number of purchasing users.

### Segmentation Metrics

- Revenue by category
- Revenue by brand
- Revenue by price band
- Conversion by price band
- Conversion by category
- Revenue by weekday
- Revenue by hour

---

## 6. Dashboard Design

The dashboard follows a consistent professional theme:

- Dark navy headings
- Blue as the primary analytical color
- Teal/green used selectively to highlight important results
- Light neutral page background
- White visual containers
- Minimal visual clutter
- Consistent spacing and alignment
- KPI cards with contextual information
- Conditional formatting for opportunity analysis

The design intentionally avoids unnecessary charts so that the dashboard remains easy to interpret for business users.

---

## 7. Business Questions Answered

The dashboard helps answer:

1. How many users entered the e-commerce funnel?
2. How many users added products to their carts?
3. How many users completed purchases?
4. Where is the largest funnel drop-off?
5. What is the View → Cart conversion rate?
6. What is the Cart → Purchase conversion rate?
7. What is the overall View → Purchase conversion rate?
8. Which categories generate the most revenue?
9. Which brands generate the most revenue?
10. Which price bands have the highest purchase conversion?
11. Which price bands generate the most revenue?
12. Which days generate the highest purchase revenue?
13. Which hours generate the highest purchase revenue?
14. Which categories have high traffic but weak conversion?

---

## 8. How to Use the Dashboard

### Requirements

- Power BI Desktop
- The `.pbix` file included in the project release

### Steps

1. Download the Power BI `.pbix` file from the project's GitHub Release.
2. Install/open **Power BI Desktop**.
3. Open the `.pbix` file.
4. Review **Executive Funnel Overview** first.
5. Navigate to **Segment & Opportunity Analysis** for deeper analysis.
6. Use the visuals and cross-filtering features to explore the results.

> The dashboard is designed primarily as an analytical portfolio project. The underlying data represents October 2019 behavior and should not be interpreted as current e-commerce performance.

---

## 9. Repository and Large File Handling

The Power BI `.pbix` file is not stored directly in the normal Git repository because Power BI files can exceed GitHub's regular browser upload limit.

Instead, the `.pbix` file is distributed through a **GitHub Release**.

This keeps the source repository lightweight while still providing a professional download location for the completed dashboard.

### Recommended Release Asset

Example:

`ecommerce-conversion-revenue-analytics-v1.0.0.pbix`

---

## 10. Project Workflow

```text
October 2019 Raw Dataset
        ↓
Data Cleaning & Validation
        ↓
clean_events.csv
        ↓
User Funnel Transformation
        ↓
user_funnel.csv
        ↓
Analytical Tables
        ↓
Power BI Data Model
        ↓
DAX Measures
        ↓
Dashboard
        ↓
Business Insights
```

---

## 11. Related Project Documentation

Refer to the main project repository for:

- Project overview
- Business problem
- Data preparation
- Data cleaning
- EDA
- SQL / analytical transformations
- Code documentation
- Dataset reconstruction instructions
- Project architecture
- Final business insights

---

## 12. Dataset Attribution

The underlying dataset is:

**eCommerce Behavior Data from Multi-Category Store**

Created by **Michael Kechinov** and collected by the **Open CDP project**.

Dataset source:

https://www.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store

Please refer to the original Kaggle dataset page for its documentation, attribution requirements, and licensing information.

---

## 13. Dashboard Version

**Version:** 1.0.0  
**Data Period:** October 2019  
**Tool:** Microsoft Power BI  
**Project Type:** Data Analytics / Business Intelligence  
**Domain:** E-commerce
