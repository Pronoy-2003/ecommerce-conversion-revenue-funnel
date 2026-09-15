"""
validate_time_analysis.py

Purpose:
Validates the time-analysis output before it is used for
downstream analysis and visualization.

Why:
Ensures that all expected time buckets, metrics, funnel relationships,
and conversion-rate calculations are correct.
"""


import pandas as pd
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

TIME_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "eda"
    / "time_analysis.csv"
)


# ============================================================
# EXPECTED VALUES
# ============================================================

EXPECTED_HOURS = {
    f"{hour:02d}"
    for hour in range(24)
}

EXPECTED_DAYS = {
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
}

REQUIRED_COLUMNS = [
    "analysis_type",
    "time_dimension",
    "time_value",
    "view_users",
    "cart_users",
    "purchase_users",
    "purchase_events",
    "revenue",
    "view_to_cart_rate",
    "cart_to_purchase_rate",
    "view_to_purchase_rate",
]


# ============================================================
# LOAD DATA
# ============================================================

print("=" * 70)
print("TIME ANALYSIS VALIDATION")
print("=" * 70)

df = pd.read_csv(TIME_FILE)

print(f"\nRows loaded: {len(df):,}")
print(f"Columns: {len(df.columns)}")


# ============================================================
# 1. COLUMN VALIDATION
# ============================================================

missing_columns = [
    col
    for col in REQUIRED_COLUMNS
    if col not in df.columns
]

if missing_columns:
    print("\n❌ FAIL — Missing columns:")
    print(missing_columns)
else:
    print("\n✅ PASS — All required columns exist")


# ============================================================
# 2. ROW COUNT
# ============================================================

if len(df) == 62:
    print("✅ PASS — Expected 62 rows")
else:
    print(
        f"❌ FAIL — Expected 62 rows, "
        f"found {len(df):,}"
    )


# ============================================================
# 3. ANALYSIS TYPE
# ============================================================

expected_analysis_types = {
    "funnel_cohort",
    "purchase_activity",
}

actual_analysis_types = set(
    df["analysis_type"].dropna().unique()
)

if actual_analysis_types == expected_analysis_types:
    print(
        "✅ PASS — Analysis types are correct"
    )
else:
    print(
        "❌ FAIL — Unexpected analysis types:"
    )
    print(actual_analysis_types)


# ============================================================
# 4. TIME DIMENSIONS
# ============================================================

expected_dimensions = {
    "hour",
    "day_of_week",
}

actual_dimensions = set(
    df["time_dimension"].dropna().unique()
)

if actual_dimensions == expected_dimensions:
    print(
        "✅ PASS — Time dimensions are correct"
    )
else:
    print(
        "❌ FAIL — Unexpected time dimensions:"
    )
    print(actual_dimensions)


# ============================================================
# 5. DUPLICATE CHECK
# ============================================================

duplicate_count = df.duplicated(
    subset=[
        "analysis_type",
        "time_dimension",
        "time_value",
    ]
).sum()

if duplicate_count == 0:
    print(
        "✅ PASS — No duplicate time buckets"
    )
else:
    print(
        f"❌ FAIL — Duplicate time buckets: "
        f"{duplicate_count}"
    )


# ============================================================
# 6. HOURLY BUCKET CHECK
# ============================================================

hour_df = df[
    df["time_dimension"] == "hour"
]

actual_hours = set(
    hour_df["time_value"].astype(str)
)

if actual_hours == EXPECTED_HOURS:
    print(
        "✅ PASS — All 24 hourly buckets exist"
    )
else:
    print("❌ FAIL — Hour buckets incorrect")
    print(
        "Missing:",
        EXPECTED_HOURS - actual_hours
    )
    print(
        "Unexpected:",
        actual_hours - EXPECTED_HOURS
    )


# ============================================================
# 7. DAY-OF-WEEK CHECK
# ============================================================

day_df = df[
    df["time_dimension"] == "day_of_week"
]

actual_days = set(
    day_df["time_value"].dropna().unique()
)

if actual_days == EXPECTED_DAYS:
    print(
        "✅ PASS — All 7 weekdays exist"
    )
else:
    print("❌ FAIL — Weekday buckets incorrect")
    print(
        "Missing:",
        EXPECTED_DAYS - actual_days
    )
    print(
        "Unexpected:",
        actual_days - EXPECTED_DAYS
    )


# ============================================================
# 8. NUMERIC VALIDATION
# ============================================================

numeric_columns = [
    "view_users",
    "cart_users",
    "purchase_users",
    "purchase_events",
    "revenue",
]

negative_counts = (
    df[numeric_columns]
    .lt(0)
    .sum()
)

if negative_counts.sum() == 0:
    print(
        "✅ PASS — No negative metrics"
    )
else:
    print(
        "❌ FAIL — Negative values found:"
    )
    print(
        negative_counts[
            negative_counts > 0
        ]
    )


# ============================================================
# 9. FUNNEL COHORT HIERARCHY
# ============================================================

cohort = df[
    df["analysis_type"] == "funnel_cohort"
].copy()

cart_greater_than_view = (
    cohort["cart_users"]
    > cohort["view_users"]
).sum()

purchase_greater_than_cart = (
    cohort["purchase_users"]
    > cohort["cart_users"]
).sum()

if cart_greater_than_view == 0:
    print(
        "✅ PASS — Cart users never exceed view users"
    )
else:
    print(
        f"❌ FAIL — {cart_greater_than_view} "
        f"cohorts have Cart > View"
    )

if purchase_greater_than_cart == 0:
    print(
        "✅ PASS — Purchase users never exceed cart users"
    )
else:
    print(
        f"❌ FAIL — {purchase_greater_than_cart} "
        f"cohorts have Purchase > Cart"
    )


# ============================================================
# 10. RATE VALIDATION
# ============================================================

rate_errors = 0

for _, row in cohort.iterrows():

    view_users = row["view_users"]
    cart_users = row["cart_users"]
    purchase_users = row["purchase_users"]

    expected_vc = (
        cart_users / view_users
        if view_users > 0
        else 0
    )

    expected_cp = (
        purchase_users / cart_users
        if cart_users > 0
        else 0
    )

    expected_vp = (
        purchase_users / view_users
        if view_users > 0
        else 0
    )

    if abs(
        row["view_to_cart_rate"]
        - expected_vc
    ) > 1e-10:
        rate_errors += 1

    if abs(
        row["cart_to_purchase_rate"]
        - expected_cp
    ) > 1e-10:
        rate_errors += 1

    if abs(
        row["view_to_purchase_rate"]
        - expected_vp
    ) > 1e-10:
        rate_errors += 1


if rate_errors == 0:
    print(
        "✅ PASS — All funnel conversion rates are correct"
    )
else:
    print(
        f"❌ FAIL — Rate calculation errors: "
        f"{rate_errors}"
    )


# ============================================================
# 11. FUNNEL COHORT RECONCILIATION
# ============================================================

total_view_users = cohort[
    cohort["time_dimension"] == "hour"
]["view_users"].sum()

total_cart_users = cohort[
    cohort["time_dimension"] == "hour"
]["cart_users"].sum()

total_purchase_users = cohort[
    cohort["time_dimension"] == "hour"
]["purchase_users"].sum()

print("\nFunnel cohort reconciliation:")

print(
    f"Hourly first-view users : "
    f"{total_view_users:,.0f}"
)

print(
    f"Hourly cohort cart users: "
    f"{total_cart_users:,.0f}"
)

print(
    f"Hourly cohort purchases : "
    f"{total_purchase_users:,.0f}"
)

if total_view_users == 3_022_130:
    print(
        "✅ PASS — View users reconcile"
    )
else:
    print(
        "❌ FAIL — View users do not reconcile"
    )

if total_cart_users == 336_764:
    print(
        "✅ PASS — Cart users reconcile"
    )
else:
    print(
        "❌ FAIL — Cart users do not reconcile"
    )

if total_purchase_users == 196_488:
    print(
        "✅ PASS — Purchase users reconcile"
    )
else:
    print(
        "❌ FAIL — Purchase users do not reconcile"
    )


# ============================================================
# 12. PURCHASE ACTIVITY RECONCILIATION
# ============================================================

activity = df[
    df["analysis_type"] == "purchase_activity"
].copy()

activity_purchase_events = activity[
    activity["time_dimension"] == "hour"
]["purchase_events"].sum()

activity_revenue = activity[
    activity["time_dimension"] == "hour"
]["revenue"].sum()

print("\nPurchase activity reconciliation:")

print(
    f"Purchase events: "
    f"{activity_purchase_events:,.0f}"
)

print(
    f"Revenue: "
    f"₹{activity_revenue:,.2f}"
)

EXPECTED_PURCHASE_EVENTS = 742_773
EXPECTED_REVENUE = 229_933_212.63

if activity_purchase_events == EXPECTED_PURCHASE_EVENTS:
    print(
        "✅ PASS — Purchase events reconcile"
    )
else:
    print(
        "❌ FAIL — Purchase events do not reconcile"
    )

if abs(
    activity_revenue - EXPECTED_REVENUE
) < 0.01:
    print(
        "✅ PASS — Revenue reconciles"
    )
else:
    print(
        "❌ FAIL — Revenue does not reconcile"
    )


# ============================================================
# 13. MISSING VALUES
# ============================================================

print("\nMissing values:")

missing_summary = df.isna().sum()

print(
    missing_summary[
        missing_summary > 0
    ]
)

# For purchase_activity rows, funnel conversion
# fields are intentionally blank.
expected_activity_nulls = (
    activity[
        [
            "view_users",
            "cart_users",
            "view_to_cart_rate",
            "cart_to_purchase_rate",
            "view_to_purchase_rate",
        ]
    ]
    .isna()
    .all()
    .all()
)

if expected_activity_nulls:
    print(
        "✅ PASS — Purchase-activity funnel fields "
        "are intentionally blank"
    )
else:
    print(
        "❌ FAIL — Unexpected values in "
        "purchase-activity funnel fields"
    )


# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("VALIDATION COMPLETE")
print("=" * 70)