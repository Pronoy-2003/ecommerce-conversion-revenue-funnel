# Processed Data

This folder contains the **processed analytical datasets** generated from the October 2019 e-commerce event data.

The project does **not** commit the large processed CSV files to GitHub. Instead, this README documents what each file contains and exactly how to regenerate it.

> **Important:** The raw dataset used by this project is `2019-Oct.csv`. Do not use the November dataset.

---

## Files in This Folder

### 1. `clean_events.csv`

**Purpose:** Cleaned event-level dataset used as the foundation for downstream analysis.

The file contains the cleaned version of the October 2019 event data after the production data-processing pipeline has:

- Removed exact duplicate events
- Standardized relevant fields
- Preserved valid user behavior
- Retained missing descriptive values for appropriate downstream handling
- Prepared the dataset for funnel and EDA processing

Because this is an event-level dataset containing more than 42 million records, the resulting CSV is several GB in size.

**Repository status:** Not committed to GitHub because of its large size.

---

### 2. `user_funnel.csv`

**Purpose:** User-level chronological funnel dataset used for overall funnel analysis and Power BI.

Each row represents one user.

The main funnel states are:

```text
View
  ↓
Add to Cart
  ↓
Purchase
```

The dataset contains user-level metrics such as:

- `user_id`
- `viewed`
- `added_to_cart`
- `purchased`
- `purchase_count`
- `purchase_revenue`

The funnel is chronological, meaning a user must progress through the required earlier stage before being counted in the next stage.

The file is approximately 160 MB and is therefore also excluded from the GitHub repository.

---

# 🔄 How to Generate the Files

The processed files are generated from the raw October 2019 dataset through the project's Python processing pipeline.

## Step 1 — Download the Raw Dataset

Download:

**`2019-Oct.csv`**

from the original Kaggle dataset:

https://www.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store

October-specific file:

https://www.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store?select=2019-Oct.csv

Place the file at:

```text
data/raw/2019-Oct.csv
```

---

## Step 2 — Generate `clean_events.csv`

Run the production raw-data processing module from the project root:

```bash
python -m src.process_raw_data
```

This runs the large-scale processing workflow and generates the cleaned event-level dataset.

Expected output:

```text
data/processed/clean_events.csv
```

The processing is performed in chunks so that the several-GB raw dataset does not need to be loaded completely into memory.

---

## Step 3 — Generate `user_funnel.csv`

After `clean_events.csv` has been generated, run:

```bash
python -m src.funnel_analysis
```

This constructs the chronological user-level funnel and generates:

```text
data/processed/user_funnel.csv
```

The output is then used by the EDA notebooks and downstream analysis.

---

# 🧭 Processing Flow

```text
Kaggle
2019-Oct.csv
      │
      ▼
src.process_raw_data
      │
      ▼
clean_events.csv
      │
      ▼
src.funnel_analysis
      │
      ▼
user_funnel.csv
      │
      ▼
EDA / Validation / Power BI
```

---

# 📊 Why These Files Are Not Included on GitHub

GitHub recommends keeping repositories small. GitHub warns for files larger than **50 MiB** in normal Git repositories and blocks individual files larger than **100 MiB**; Git LFS is the supported approach for files that need to be tracked beyond the normal limit. citeturn0search0turn0search2

For this portfolio project, committing the generated CSVs is unnecessary because they are **reproducible outputs** of the processing pipeline.

Keeping them outside Git also makes the repository:

- Faster to clone
- Easier for recruiters to browse
- Smaller and cleaner
- Focused on code, analysis, documentation, and dashboard work

The recommended GitHub approach is therefore:

```text
GitHub
│
├── Source code
├── Notebooks
├── Documentation
├── Power BI dashboard
├── Screenshots
└── Small analytical outputs
```

while the large generated datasets remain local.

---

# 📁 Expected Local Structure

After running the pipeline:

```text
data/
│
├── raw/
│   ├── README.md
│   └── 2019-Oct.csv
│
└── processed/
    ├── clean_events.csv
    ├── user_funnel.csv
    └── eda/
        ├── overall_funnel.csv
        ├── category_analysis.csv
        ├── brand_analysis.csv
        ├── price_band_analysis.csv
        └── time_analysis.csv
```

---

# ⚠️ Git Configuration

The large generated files should be excluded from Git tracking.

Add the following to the project's `.gitignore`:

```gitignore
# Large processed datasets
data/processed/clean_events.csv
data/processed/user_funnel.csv

# Raw dataset
data/raw/2019-Oct.csv
```

This prevents accidental commits of the multi-GB raw/processed datasets.

---

# 🔁 Reproducibility

A recruiter or another developer can reproduce the missing CSV files by:

1. Downloading the original `2019-Oct.csv`.
2. Placing it in `data/raw/`.
3. Running:

```bash
python -m src.process_raw_data
```

4. Then running:

```bash
python -m src.funnel_analysis
```

The same processing pipeline used for this project will recreate:

```text
clean_events.csv
user_funnel.csv
```

The generated files are therefore **derived data**, not manually maintained project assets.
