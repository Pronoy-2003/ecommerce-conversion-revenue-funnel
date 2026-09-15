"""
time_analysis.py

Purpose:
Analyzes funnel conversion and purchase activity across hours
and days of the week.

Two perspectives are used:
1. Funnel cohort analysis based on the user's first-view time.
2. Purchase activity based on the actual purchase event time.

Why:
These two perspectives answer different business questions:
when users enter the funnel versus when purchases actually occur.
"""


import time
from pathlib import Path

import pandas as pd


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

CLEAN_EVENTS_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "clean_events.csv"
)

FUNNEL_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "user_funnel.csv"
)

EDA_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "eda"
)

TIME_OUTPUT = EDA_DIR / "time_analysis.csv"

CHUNK_SIZE = 500_000


# ============================================================
# EXPECTED COLUMNS
# ============================================================

FUNNEL_COLUMNS = [
    "user_id",
    "viewed",
    "added_to_cart",
    "purchased",
    "first_view_time",
    "first_cart_time",
    "first_purchase_time",
    "purchase_count",
    "purchase_revenue",
]


# ============================================================
# 1. BUILD FUNNEL COHORT ANALYSIS
# ============================================================

def build_funnel_cohort_analysis():
    """
    Calculate true funnel conversion by the user's
    first-view hour and first-view day of week.

    This is cohort-based:
        First View → eventual Cart → eventual Purchase

    This prevents time-bucket leakage where a user views
    at one hour and carts at another hour.
    """

    print("\nLoading user funnel...")

    df = pd.read_csv(
        FUNNEL_FILE,
        usecols=FUNNEL_COLUMNS
    )

    print(f"Users loaded: {len(df):,}")

    # --------------------------------------------------------
    # Validate required columns
    # --------------------------------------------------------

    missing_columns = [
        col for col in FUNNEL_COLUMNS
        if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing funnel columns: {missing_columns}"
        )

    # --------------------------------------------------------
    # Datatypes
    # --------------------------------------------------------

    df["first_view_time"] = pd.to_datetime(
        df["first_view_time"],
        utc=True,
        errors="coerce"
    )

    numeric_columns = [
        "viewed",
        "added_to_cart",
        "purchased",
        "purchase_count",
        "purchase_revenue",
    ]

    for col in numeric_columns:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        ).fillna(0)

    # --------------------------------------------------------
    # Only users who actually viewed
    # --------------------------------------------------------

    viewed_users = df[df["viewed"] == 1].copy()

    print(
        f"Users with first view: "
        f"{len(viewed_users):,}"
    )

    # --------------------------------------------------------
    # First-view time features
    # --------------------------------------------------------

    viewed_users["first_view_hour"] = (
        viewed_users["first_view_time"].dt.hour
    )

    viewed_users["first_view_day"] = (
        viewed_users["first_view_time"].dt.day_name()
    )

    # --------------------------------------------------------
    # Hourly funnel cohort
    # --------------------------------------------------------

    hourly = (
        viewed_users
        .groupby("first_view_hour")
        .agg(
            view_users=("user_id", "nunique"),
            cart_users=("added_to_cart", "sum"),
            purchase_users=("purchased", "sum"),
            purchase_events=("purchase_count", "sum"),
            revenue=("purchase_revenue", "sum"),
        )
        .reset_index()
    )

    hourly["time_dimension"] = "hour"
    hourly["time_value"] = (
        hourly["first_view_hour"]
        .astype(int)
        .map(lambda x: f"{x:02d}")
    )

    # --------------------------------------------------------
    # Daily funnel cohort
    # --------------------------------------------------------

    day_order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]

    daily = (
        viewed_users
        .groupby("first_view_day")
        .agg(
            view_users=("user_id", "nunique"),
            cart_users=("added_to_cart", "sum"),
            purchase_users=("purchased", "sum"),
            purchase_events=("purchase_count", "sum"),
            revenue=("purchase_revenue", "sum"),
        )
        .reset_index()
    )

    daily["time_dimension"] = "day_of_week"
    daily["time_value"] = daily["first_view_day"]

    # --------------------------------------------------------
    # Combine
    # --------------------------------------------------------

    cohort = pd.concat(
        [
            hourly[
                [
                    "time_dimension",
                    "time_value",
                    "view_users",
                    "cart_users",
                    "purchase_users",
                    "purchase_events",
                    "revenue",
                ]
            ],
            daily[
                [
                    "time_dimension",
                    "time_value",
                    "view_users",
                    "cart_users",
                    "purchase_users",
                    "purchase_events",
                    "revenue",
                ]
            ],
        ],
        ignore_index=True
    )

    # --------------------------------------------------------
    # True cohort conversion rates
    # --------------------------------------------------------

    cohort["view_to_cart_rate"] = (
        cohort["cart_users"]
        / cohort["view_users"]
    )

    cohort["cart_to_purchase_rate"] = (
        cohort["purchase_users"]
        / cohort["cart_users"]
    )

    cohort["view_to_purchase_rate"] = (
        cohort["purchase_users"]
        / cohort["view_users"]
    )

    return cohort


# ============================================================
# 2. PURCHASE ACTIVITY BY ACTUAL EVENT TIME
# ============================================================

def aggregate_purchase_activity(max_chunks=None):
    """
    Aggregate actual purchase events by:
        - hour of day
        - day of week

    Unlike funnel cohort analysis, this uses the actual
    purchase event timestamp.

    Purchase users = distinct users making purchases
    Purchase events = every purchase event
    Revenue = sum of purchase prices
    """

    print("\nStarting purchase activity analysis...")

    # --------------------------------------------------------
    # Containers
    # --------------------------------------------------------

    hour_users = {
        hour: set()
        for hour in range(24)
    }

    day_users = {
        day: set()
        for day in [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
    }

    hour_events = {
        hour: 0
        for hour in range(24)
    }

    hour_revenue = {
        hour: 0.0
        for hour in range(24)
    }

    day_events = {
        day: 0
        for day in day_users
    }

    day_revenue = {
        day: 0.0
        for day in day_users
    }

    # --------------------------------------------------------
    # Read only required columns
    # --------------------------------------------------------

    usecols = [
        "event_time",
        "event_type",
        "price",
        "user_id",
    ]

    total_rows = 0
    purchase_rows = 0

    start_time = time.time()

    reader = pd.read_csv(
        CLEAN_EVENTS_FILE,
        usecols=usecols,
        chunksize=CHUNK_SIZE
    )

    for chunk_number, df in enumerate(reader, start=1):

        if max_chunks is not None and chunk_number > max_chunks:
            break

        total_rows += len(df)

        # ----------------------------------------------------
        # Keep only purchase events
        # ----------------------------------------------------

        purchases = df[
            df["event_type"] == "purchase"
        ].copy()

        if purchases.empty:
            continue

        purchase_rows += len(purchases)

        # ----------------------------------------------------
        # Datatypes
        # ----------------------------------------------------

        purchases["event_time"] = pd.to_datetime(
            purchases["event_time"],
            utc=True,
            errors="coerce"
        )

        purchases["price"] = pd.to_numeric(
            purchases["price"],
            errors="coerce"
        ).fillna(0)

        purchases["event_hour"] = (
            purchases["event_time"].dt.hour
        )

        purchases["day_of_week"] = (
            purchases["event_time"].dt.day_name()
        )

        # ----------------------------------------------------
        # Hourly activity
        # ----------------------------------------------------

        for hour, group in purchases.groupby("event_hour"):

            hour = int(hour)

            hour_users[hour].update(
                group["user_id"].unique()
            )

            hour_events[hour] += len(group)

            hour_revenue[hour] += (
                group["price"].sum()
            )

        # ----------------------------------------------------
        # Daily activity
        # ----------------------------------------------------

        for day, group in purchases.groupby(
            "day_of_week"
        ):

            day_users[day].update(
                group["user_id"].unique()
            )

            day_events[day] += len(group)

            day_revenue[day] += (
                group["price"].sum()
            )

        # ----------------------------------------------------
        # Progress
        # ----------------------------------------------------

        if chunk_number % 10 == 0:

            elapsed = time.time() - start_time

            print(
                f"Chunk {chunk_number:,} | "
                f"Rows: {total_rows:,} | "
                f"Purchases: {purchase_rows:,} | "
                f"Time: {elapsed:.1f}s"
            )

    # --------------------------------------------------------
    # Build hourly output
    # --------------------------------------------------------

    hourly_rows = []

    for hour in range(24):

        hourly_rows.append(
            {
                "analysis_type": "purchase_activity",
                "time_dimension": "hour",
                "time_value": f"{hour:02d}",
                "view_users": None,
                "cart_users": None,
                "purchase_users": len(
                    hour_users[hour]
                ),
                "purchase_events": hour_events[hour],
                "revenue": hour_revenue[hour],
                "view_to_cart_rate": None,
                "cart_to_purchase_rate": None,
                "view_to_purchase_rate": None,
            }
        )

    # --------------------------------------------------------
    # Build daily output
    # --------------------------------------------------------

    day_order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]

    daily_rows = []

    for day in day_order:

        daily_rows.append(
            {
                "analysis_type": "purchase_activity",
                "time_dimension": "day_of_week",
                "time_value": day,
                "view_users": None,
                "cart_users": None,
                "purchase_users": len(
                    day_users[day]
                ),
                "purchase_events": day_events[day],
                "revenue": day_revenue[day],
                "view_to_cart_rate": None,
                "cart_to_purchase_rate": None,
                "view_to_purchase_rate": None,
            }
        )

    return pd.DataFrame(
        hourly_rows + daily_rows
    )


# ============================================================
# 3. FINAL TIME ANALYSIS
# ============================================================

def run_time_analysis(max_chunks=None):
    """
    Build the complete time analysis dataset.

    max_chunks:
        Used only for purchase activity testing.
        Leave as None for production.
    """

    start_time = time.time()

    print("=" * 70)
    print("TIME ANALYSIS")
    print("=" * 70)

    # --------------------------------------------------------
    # Funnel cohort analysis
    # --------------------------------------------------------

    cohort = build_funnel_cohort_analysis()

    cohort.insert(
        0,
        "analysis_type",
        "funnel_cohort"
    )

    # --------------------------------------------------------
    # Purchase activity
    # --------------------------------------------------------

    activity = aggregate_purchase_activity(
        max_chunks=max_chunks
    )

    # --------------------------------------------------------
    # Combine
    # --------------------------------------------------------

    final_df = pd.concat(
        [
            cohort,
            activity,
        ],
        ignore_index=True
    )

    # --------------------------------------------------------
    # Column order
    # --------------------------------------------------------

    final_columns = [
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

    final_df = final_df[
        final_columns
    ]

    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    dimension_order = {
        "hour": 1,
        "day_of_week": 2,
    }

    day_order = {
        "Monday": 1,
        "Tuesday": 2,
        "Wednesday": 3,
        "Thursday": 4,
        "Friday": 5,
        "Saturday": 6,
        "Sunday": 7,
    }

    final_df["sort_order"] = (
        final_df["time_value"]
        .map(day_order)
    )

    hour_numeric = pd.to_numeric(
        final_df["time_value"],
        errors="coerce"
    )

    final_df["sort_order"] = (
        final_df["sort_order"]
        .fillna(hour_numeric)
    )

    final_df["dimension_order"] = (
        final_df["time_dimension"]
        .map(dimension_order)
    )

    final_df = (
        final_df
        .sort_values(
            [
                "analysis_type",
                "dimension_order",
                "sort_order",
            ]
        )
        .drop(
            columns=[
                "dimension_order",
                "sort_order",
            ]
        )
        .reset_index(drop=True)
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    EDA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    final_df.to_csv(
        TIME_OUTPUT,
        index=False
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    elapsed = time.time() - start_time

    print("\n" + "=" * 70)
    print("TIME ANALYSIS COMPLETE")
    print("=" * 70)

    print(
        f"Output rows : {len(final_df):,}"
    )

    print(
        f"Output file : {TIME_OUTPUT}"
    )

    print(
        f"Processing time: {elapsed:.2f} seconds"
    )

    print("\nAnalysis types:")
    print(
        final_df["analysis_type"]
        .value_counts()
    )

    print("\nTime dimensions:")
    print(
        final_df["time_dimension"]
        .value_counts()
    )

    return final_df


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    run_time_analysis()