"""
eda_analysis.py

Purpose:
Builds funnel and revenue analysis at category, brand, and price-band
levels using the cleaned event dataset.

Why:
The overall user funnel shows aggregate performance, while this file
identifies which product categories, brands, and price segments
perform differently.
"""


import sqlite3
from pathlib import Path
import time
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

CLEAN_EVENTS_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "clean_events.csv"
)

EDA_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "eda"
)

CATEGORY_DB = EDA_DIR / "category_funnel.db"

CATEGORY_OUTPUT = EDA_DIR / "category_analysis.csv"

BRAND_DB = EDA_DIR / "brand_funnel.db"

BRAND_OUTPUT = EDA_DIR / "brand_analysis.csv"

PRICE_DB = EDA_DIR / "price_band_funnel.db"

PRICE_OUTPUT = EDA_DIR / "price_band_analysis.csv"



# ============================================================
# SETTINGS
# ============================================================

CHUNK_SIZE = 500_000


# ============================================================
# CREATE DATABASE
# ============================================================

def create_category_database(db_path):
    """
    Create persistent user-category funnel state.
    """

    connection = sqlite3.connect(db_path)

    cursor = connection.cursor()

    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.execute("PRAGMA temp_store=FILE;")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_category_state (

            user_id INTEGER NOT NULL,

            category_code TEXT NOT NULL,

            viewed INTEGER NOT NULL DEFAULT 0,

            added_to_cart INTEGER NOT NULL DEFAULT 0,

            purchased INTEGER NOT NULL DEFAULT 0,

            first_view_time TEXT,

            first_cart_time TEXT,

            first_purchase_time TEXT,

            purchase_count INTEGER NOT NULL DEFAULT 0,

            purchase_revenue REAL NOT NULL DEFAULT 0,

            PRIMARY KEY (
                user_id,
                category_code
            )
        );
        """
    )

    connection.commit()

    return connection


# ============================================================
# PROCESS ONE CHUNK
# ============================================================

def process_category_chunk(df, connection):
    """
    Process one event chunk and update user-category funnel state.

    Funnel logic:

        View
          ↓
        Add to Cart
          ↓
        Purchase

    The sequence must occur chronologically and must work
    correctly across chunk boundaries.
    """

    # ========================================================
    # PREPARE DATA
    # ========================================================

    df = df.copy()

    df["event_time"] = pd.to_datetime(
        df["event_time"],
        utc=True
    )

    df["category_code"] = (
        df["category_code"]
        .fillna("Unknown")
        .astype(str)
    )

    df["event_type"] = df["event_type"].astype(str)

    # ========================================================
    # SORT CHRONOLOGICALLY
    # ========================================================

    df = df.sort_values(
        [
            "user_id",
            "category_code",
            "event_time"
        ]
    )

    # ========================================================
    # EVENT FLAGS
    # ========================================================

    df["is_view"] = (
        df["event_type"] == "view"
    )

    df["is_cart"] = (
        df["event_type"] == "cart"
    )

    df["is_purchase"] = (
        df["event_type"] == "purchase"
    )

    # ========================================================
    # GET CURRENT USER-CATEGORY KEYS
    # ========================================================

    keys = (
        df[
            [
                "user_id",
                "category_code"
            ]
        ]
        .drop_duplicates()
    )

    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TEMP TABLE IF NOT EXISTS
        current_category_users (

            user_id INTEGER,

            category_code TEXT,

            PRIMARY KEY (
                user_id,
                category_code
            )
        );
        """
    )

    cursor.execute(
        "DELETE FROM current_category_users"
    )

    cursor.executemany(
        """
        INSERT OR IGNORE INTO
        current_category_users
        (
            user_id,
            category_code
        )
        VALUES (?, ?)
        """,
        [
            (
                int(row.user_id),
                row.category_code
            )
            for row in keys.itertuples(index=False)
        ]
    )

    connection.commit()

    # ========================================================
    # GET PREVIOUS STATES
    # ========================================================

    previous = pd.read_sql_query(
        """
        SELECT

            s.user_id,

            s.category_code,

            s.viewed AS viewed_previous,

            s.added_to_cart AS cart_previous,

            s.purchased AS purchased_previous,

            s.first_view_time AS first_view_previous,

            s.first_cart_time AS first_cart_previous,

            s.first_purchase_time
                AS first_purchase_previous,

            s.purchase_count
                AS purchase_count_previous,

            s.purchase_revenue
                AS revenue_previous

        FROM user_category_state AS s

        INNER JOIN current_category_users AS u

            ON s.user_id = u.user_id

            AND s.category_code =
                u.category_code
        """,
        connection
    )

    # ========================================================
    # MERGE PREVIOUS STATE INTO EVENTS
    # ========================================================

    df = df.merge(
        previous[
            [
                "user_id",
                "category_code",
                "viewed_previous",
                "cart_previous",
                "purchased_previous"
            ]
        ],
        on=[
            "user_id",
            "category_code"
        ],
        how="left"
    )

    # Fill previous funnel flags

    for column in [
        "viewed_previous",
        "cart_previous",
        "purchased_previous"
    ]:

        df[column] = (
            pd.to_numeric(
                df[column],
                errors="coerce"
            )
            .fillna(0)
            .astype("int8")
        )

    # ========================================================
    # VIEW STAGE
    # ========================================================

    view_count = (
        df["is_view"]
        .groupby(
            [
                df["user_id"],
                df["category_code"]
            ]
        )
        .cumsum()
    )

    df["view_seen"] = (
        (view_count > 0)
        |
        (df["viewed_previous"] == 1)
    )

    # ========================================================
    # CART STAGE
    # ========================================================

    df["qualifying_cart"] = (
        df["is_cart"]
        &
        df["view_seen"]
    )

    cart_count = (
        df["qualifying_cart"]
        .groupby(
            [
                df["user_id"],
                df["category_code"]
            ]
        )
        .cumsum()
    )

    df["cart_seen"] = (
        (cart_count > 0)
        |
        (df["cart_previous"] == 1)
    )

    # ========================================================
    # PURCHASE STAGE
    # ========================================================

    df["qualifying_purchase"] = (
        df["is_purchase"]
        &
        df["cart_seen"]
    )

    # ========================================================
    # TIMESTAMPS
    # ========================================================

    df["view_time"] = df["event_time"].where(
        df["is_view"]
    )

    df["cart_time"] = df["event_time"].where(
        df["qualifying_cart"]
    )

    df["purchase_time"] = df["event_time"].where(
        df["qualifying_purchase"]
    )

    # ========================================================
    # CURRENT CHUNK AGGREGATION
    # ========================================================

    summary = (
        df.groupby(
            [
                "user_id",
                "category_code"
            ],
            sort=False
        )
        .agg(

            any_view=(
                "is_view",
                "any"
            ),

            any_cart=(
                "qualifying_cart",
                "any"
            ),

            any_purchase=(
                "qualifying_purchase",
                "any"
            ),

            first_view_time=(
                "view_time",
                "min"
            ),

            first_cart_time=(
                "cart_time",
                "min"
            ),

            first_purchase_time=(
                "purchase_time",
                "min"
            ),

            purchase_count=(
                "is_purchase",
                "sum"
            ),

            purchase_revenue=(
                "price",
                lambda x: x[
                    df.loc[
                        x.index,
                        "is_purchase"
                    ]
                ].sum()
            )
        )
        .reset_index()
    )

    # ========================================================
    # MERGE PREVIOUS COMPLETE STATE
    # ========================================================

    result = summary.merge(
        previous,
        on=[
            "user_id",
            "category_code"
        ],
        how="left"
    )

    # ========================================================
    # NUMERIC PREVIOUS VALUES
    # ========================================================

    numeric_columns = [
        "viewed_previous",
        "cart_previous",
        "purchased_previous",
        "purchase_count_previous",
        "revenue_previous"
    ]

    for column in numeric_columns:

        result[column] = (
            pd.to_numeric(
                result[column],
                errors="coerce"
            )
            .fillna(0)
        )

    # ========================================================
    # FINAL FUNNEL FLAGS
    # ========================================================

    result["viewed"] = (
        result["viewed_previous"].astype(bool)
        |
        result["any_view"].astype(bool)
    ).astype("int8")

    result["added_to_cart"] = (
        result["cart_previous"].astype(bool)
        |
        result["any_cart"].astype(bool)
    ).astype("int8")

    result["purchased"] = (
        result["purchased_previous"].astype(bool)
        |
        result["any_purchase"].astype(bool)
    ).astype("int8")

    # ========================================================
    # PURCHASE METRICS
    # ========================================================

    result["purchase_count"] = (
        result["purchase_count_previous"]
        +
        result["purchase_count"]
    ).astype("int64")

    result["purchase_revenue"] = (
        result["revenue_previous"]
        +
        result["purchase_revenue"]
    ).astype("float64")

    # ========================================================
    # TIMESTAMP CONVERSION
    # ========================================================

    timestamp_columns = [
        "first_view_previous",
        "first_cart_previous",
        "first_purchase_previous",
        "first_view_time",
        "first_cart_time",
        "first_purchase_time"
    ]

    for column in timestamp_columns:

        result[column] = pd.to_datetime(
            result[column],
            utc=True,
            errors="coerce"
        )

    # ========================================================
    # FIRST VIEW
    # ========================================================

    result["first_view_time"] = (
        result[
            [
                "first_view_previous",
                "first_view_time"
            ]
        ]
        .min(axis=1)
    )

    # ========================================================
    # FIRST CART
    # ========================================================

    result["first_cart_time"] = (
        result[
            [
                "first_cart_previous",
                "first_cart_time"
            ]
        ]
        .min(axis=1)
    )

    # ========================================================
    # FIRST PURCHASE
    # ========================================================

    result["first_purchase_time"] = (
        result[
            [
                "first_purchase_previous",
                "first_purchase_time"
            ]
        ]
        .min(axis=1)
    )

    # ========================================================
    # FINAL COLUMNS
    # ========================================================

    result = result[
        [
            "user_id",
            "category_code",
            "viewed",
            "added_to_cart",
            "purchased",
            "first_view_time",
            "first_cart_time",
            "first_purchase_time",
            "purchase_count",
            "purchase_revenue"
        ]
    ]

    # ========================================================
    # SAVE UPDATED STATES
    # ========================================================

    records = []

    for row in result.itertuples(index=False):

        records.append(
            (
                int(row.user_id),
                row.category_code,
                int(row.viewed),
                int(row.added_to_cart),
                int(row.purchased),

                (
                    row.first_view_time.isoformat()
                    if pd.notna(row.first_view_time)
                    else None
                ),

                (
                    row.first_cart_time.isoformat()
                    if pd.notna(row.first_cart_time)
                    else None
                ),

                (
                    row.first_purchase_time.isoformat()
                    if pd.notna(row.first_purchase_time)
                    else None
                ),

                int(row.purchase_count),

                float(row.purchase_revenue)
            )
        )

    cursor.executemany(
        """
        INSERT INTO user_category_state (

            user_id,
            category_code,
            viewed,
            added_to_cart,
            purchased,
            first_view_time,
            first_cart_time,
            first_purchase_time,
            purchase_count,
            purchase_revenue

        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

        ON CONFLICT(
            user_id,
            category_code
        )

        DO UPDATE SET

            viewed = excluded.viewed,

            added_to_cart =
                excluded.added_to_cart,

            purchased =
                excluded.purchased,

            first_view_time =
                excluded.first_view_time,

            first_cart_time =
                excluded.first_cart_time,

            first_purchase_time =
                excluded.first_purchase_time,

            purchase_count =
                excluded.purchase_count,

            purchase_revenue =
                excluded.purchase_revenue
        """,
        records
    )

    connection.commit()


# ============================================================
# BUILD CATEGORY ANALYSIS
# ============================================================

def build_category_analysis(
    input_file=CLEAN_EVENTS_FILE,
    db_file=CATEGORY_DB,
    output_file=CATEGORY_OUTPUT,
    chunk_size=CHUNK_SIZE,
    max_chunks=None
):

    input_file = Path(input_file)
    db_file = Path(db_file)
    output_file = Path(output_file)

    if not input_file.exists():

        raise FileNotFoundError(
            f"Clean events file not found:\n"
            f"{input_file.resolve()}"
        )

    # Remove previous test database
    if db_file.exists():
        db_file.unlink()

    if output_file.exists():
        output_file.unlink()

    connection = create_category_database(
        db_file
    )

    chunks = pd.read_csv(
        input_file,
        chunksize=chunk_size
    )

    total_rows = 0
    chunk_number = 0

    try:

        for df in chunks:

            chunk_number += 1

            print("\n" + "=" * 70)
            print(
                f"Processing category chunk "
                f"{chunk_number}"
            )
            print("=" * 70)

            print(
                f"Rows: {len(df):,}"
            )

            total_rows += len(df)

            process_category_chunk(
                df,
                connection
            )

            category_pairs = connection.execute(
                """
                SELECT COUNT(*)
                FROM user_category_state
                """
            ).fetchone()[0]

            print(
                f"User-category pairs tracked: "
                f"{category_pairs:,}"
            )

            if (
                max_chunks is not None
                and chunk_number >= max_chunks
            ):

                print(
                    f"\nStopping after "
                    f"{max_chunks} chunk(s) "
                    f"for testing."
                )

                break

        # ----------------------------------------------------
        # Create category summary
        # ----------------------------------------------------

        category_summary = pd.read_sql_query(
            """
            SELECT
                category_code,

                SUM(viewed) AS view_users,

                SUM(added_to_cart)
                    AS cart_users,

                SUM(purchased)
                    AS purchase_users,

                SUM(purchase_count)
                    AS purchase_events,

                SUM(purchase_revenue)
                    AS revenue

            FROM user_category_state

            GROUP BY category_code

            ORDER BY revenue DESC
            """,
            connection
        )

        # ----------------------------------------------------
        # Conversion rates
        # ----------------------------------------------------

        category_summary[
            "view_to_cart_rate"
        ] = (
            category_summary["cart_users"]
            /
            category_summary["view_users"]
        )

        category_summary[
            "cart_to_purchase_rate"
        ] = (
            category_summary["purchase_users"]
            /
            category_summary["cart_users"]
        )

        category_summary[
            "view_to_purchase_rate"
        ] = (
            category_summary["purchase_users"]
            /
            category_summary["view_users"]
        )

        # ----------------------------------------------------
        # Handle divisions by zero
        # ----------------------------------------------------

        category_summary[
            [
                "view_to_cart_rate",
                "cart_to_purchase_rate",
                "view_to_purchase_rate"
            ]
        ] = (
            category_summary[
                [
                    "view_to_cart_rate",
                    "cart_to_purchase_rate",
                    "view_to_purchase_rate"
                ]
            ]
            .replace(
                [float("inf"), -float("inf")],
                pd.NA
            )
        )

        # ----------------------------------------------------
        # Save
        # ----------------------------------------------------

        category_summary.to_csv(
            output_file,
            index=False
        )

        print("\n" + "=" * 70)
        print("CATEGORY ANALYSIS COMPLETE")
        print("=" * 70)

        print(
            f"Chunks processed : "
            f"{chunk_number:,}"
        )

        print(
            f"Event rows read  : "
            f"{total_rows:,}"
        )

        print(
            f"Categories       : "
            f"{len(category_summary):,}"
        )

        print(
            "\nOutput file:"
        )

        print(
            output_file.resolve()
        )

        return category_summary

    finally:

        connection.close()



# ============================================================
# CREATE DATABASE
# ============================================================

def create_brand_database(db_path):
    """
    Create persistent user-brand funnel state.
    """

    connection = sqlite3.connect(db_path)

    cursor = connection.cursor()

    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.execute("PRAGMA temp_store=FILE;")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_brand_state (

            user_id INTEGER NOT NULL,

            brand TEXT NOT NULL,

            viewed INTEGER NOT NULL DEFAULT 0,

            added_to_cart INTEGER NOT NULL DEFAULT 0,

            purchased INTEGER NOT NULL DEFAULT 0,

            first_view_time TEXT,

            first_cart_time TEXT,

            first_purchase_time TEXT,

            purchase_count INTEGER NOT NULL DEFAULT 0,

            purchase_revenue REAL NOT NULL DEFAULT 0,

            PRIMARY KEY (
                user_id,
                brand
            )
        );
        """
    )

    connection.commit()

    return connection



# ============================================================
# BRAND CHUNK PROCESSING
# ============================================================

def process_brand_chunk(df, connection):
    """
    Process one event chunk and update
    user-brand funnel state.
    """

    df = df.copy()

    # ========================================================
    # PREPARE DATA
    # ========================================================

    df["event_time"] = pd.to_datetime(
        df["event_time"],
        utc=True
    )

    df["brand"] = (
        df["brand"]
        .fillna("Unknown")
        .astype(str)
    )

    df["event_type"] = (
        df["event_type"]
        .astype(str)
    )

    # ========================================================
    # SORT
    # ========================================================

    df = df.sort_values(
        [
            "user_id",
            "brand",
            "event_time"
        ]
    )

    # ========================================================
    # EVENT FLAGS
    # ========================================================

    df["is_view"] = (
        df["event_type"] == "view"
    )

    df["is_cart"] = (
        df["event_type"] == "cart"
    )

    df["is_purchase"] = (
        df["event_type"] == "purchase"
    )

    # ========================================================
    # CURRENT USER-BRAND KEYS
    # ========================================================

    keys = (
        df[
            [
                "user_id",
                "brand"
            ]
        ]
        .drop_duplicates()
    )

    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TEMP TABLE IF NOT EXISTS
        current_brand_users (

            user_id INTEGER,

            brand TEXT,

            PRIMARY KEY (
                user_id,
                brand
            )
        );
        """
    )

    cursor.execute(
        "DELETE FROM current_brand_users"
    )

    cursor.executemany(
        """
        INSERT OR IGNORE INTO
        current_brand_users
        (
            user_id,
            brand
        )
        VALUES (?, ?)
        """,
        [
            (
                int(row.user_id),
                row.brand
            )
            for row in keys.itertuples(index=False)
        ]
    )

    connection.commit()

    # ========================================================
    # PREVIOUS STATES
    # ========================================================

    previous = pd.read_sql_query(
        """
        SELECT

            s.user_id,

            s.brand,

            s.viewed AS viewed_previous,

            s.added_to_cart
                AS cart_previous,

            s.purchased
                AS purchased_previous,

            s.first_view_time
                AS first_view_previous,

            s.first_cart_time
                AS first_cart_previous,

            s.first_purchase_time
                AS first_purchase_previous,

            s.purchase_count
                AS purchase_count_previous,

            s.purchase_revenue
                AS revenue_previous

        FROM user_brand_state AS s

        INNER JOIN current_brand_users AS u

            ON s.user_id = u.user_id

            AND s.brand = u.brand
        """,
        connection
    )

    # ========================================================
    # MERGE PREVIOUS STATE INTO EVENTS
    # ========================================================

    df = df.merge(
        previous[
            [
                "user_id",
                "brand",
                "viewed_previous",
                "cart_previous",
                "purchased_previous"
            ]
        ],
        on=[
            "user_id",
            "brand"
        ],
        how="left"
    )

    # ========================================================
    # PREVIOUS FLAGS
    # ========================================================

    for column in [
        "viewed_previous",
        "cart_previous",
        "purchased_previous"
    ]:

        df[column] = (
            pd.to_numeric(
                df[column],
                errors="coerce"
            )
            .fillna(0)
            .astype("int8")
        )

    # ========================================================
    # VIEW
    # ========================================================

    view_count = (
        df["is_view"]
        .groupby(
            [
                df["user_id"],
                df["brand"]
            ]
        )
        .cumsum()
    )

    df["view_seen"] = (
        (view_count > 0)
        |
        (df["viewed_previous"] == 1)
    )

    # ========================================================
    # CART
    # ========================================================

    df["qualifying_cart"] = (
        df["is_cart"]
        &
        df["view_seen"]
    )

    cart_count = (
        df["qualifying_cart"]
        .groupby(
            [
                df["user_id"],
                df["brand"]
            ]
        )
        .cumsum()
    )

    df["cart_seen"] = (
        (cart_count > 0)
        |
        (df["cart_previous"] == 1)
    )

    # ========================================================
    # PURCHASE
    # ========================================================

    df["qualifying_purchase"] = (
        df["is_purchase"]
        &
        df["cart_seen"]
    )

    # ========================================================
    # TIMESTAMPS
    # ========================================================

    df["view_time"] = df["event_time"].where(
        df["is_view"]
    )

    df["cart_time"] = df["event_time"].where(
        df["qualifying_cart"]
    )

    df["purchase_time"] = df["event_time"].where(
        df["qualifying_purchase"]
    )

    # ========================================================
    # AGGREGATION
    # ========================================================

    summary = (
        df.groupby(
            [
                "user_id",
                "brand"
            ],
            sort=False
        )
        .agg(

            any_view=(
                "is_view",
                "any"
            ),

            any_cart=(
                "qualifying_cart",
                "any"
            ),

            any_purchase=(
                "qualifying_purchase",
                "any"
            ),

            first_view_time=(
                "view_time",
                "min"
            ),

            first_cart_time=(
                "cart_time",
                "min"
            ),

            first_purchase_time=(
                "purchase_time",
                "min"
            ),

            purchase_count=(
                "is_purchase",
                "sum"
            ),

            purchase_revenue=(
                "price",
                lambda x: x[
                    df.loc[
                        x.index,
                        "is_purchase"
                    ]
                ].sum()
            )
        )
        .reset_index()
    )

    # ========================================================
    # MERGE PREVIOUS COMPLETE STATE
    # ========================================================

    result = summary.merge(
        previous,
        on=[
            "user_id",
            "brand"
        ],
        how="left"
    )

    # ========================================================
    # NUMERIC PREVIOUS VALUES
    # ========================================================

    for column in [
        "viewed_previous",
        "cart_previous",
        "purchased_previous",
        "purchase_count_previous",
        "revenue_previous"
    ]:

        result[column] = (
            pd.to_numeric(
                result[column],
                errors="coerce"
            )
            .fillna(0)
        )

    # ========================================================
    # FINAL FLAGS
    # ========================================================

    result["viewed"] = (
        result["viewed_previous"].astype(bool)
        |
        result["any_view"].astype(bool)
    ).astype("int8")

    result["added_to_cart"] = (
        result["cart_previous"].astype(bool)
        |
        result["any_cart"].astype(bool)
    ).astype("int8")

    result["purchased"] = (
        result["purchased_previous"].astype(bool)
        |
        result["any_purchase"].astype(bool)
    ).astype("int8")

    # ========================================================
    # PURCHASE METRICS
    # ========================================================

    result["purchase_count"] = (
        result["purchase_count_previous"]
        +
        result["purchase_count"]
    ).astype("int64")

    result["purchase_revenue"] = (
        result["revenue_previous"]
        +
        result["purchase_revenue"]
    ).astype("float64")

    # ========================================================
    # TIMESTAMPS
    # ========================================================

    timestamp_columns = [
        "first_view_previous",
        "first_cart_previous",
        "first_purchase_previous",
        "first_view_time",
        "first_cart_time",
        "first_purchase_time"
    ]

    for column in timestamp_columns:

        result[column] = pd.to_datetime(
            result[column],
            utc=True,
            errors="coerce"
        )

    result["first_view_time"] = (
        result[
            [
                "first_view_previous",
                "first_view_time"
            ]
        ]
        .min(axis=1)
    )

    result["first_cart_time"] = (
        result[
            [
                "first_cart_previous",
                "first_cart_time"
            ]
        ]
        .min(axis=1)
    )

    result["first_purchase_time"] = (
        result[
            [
                "first_purchase_previous",
                "first_purchase_time"
            ]
        ]
        .min(axis=1)
    )

    # ========================================================
    # FINAL COLUMNS
    # ========================================================

    result = result[
        [
            "user_id",
            "brand",
            "viewed",
            "added_to_cart",
            "purchased",
            "first_view_time",
            "first_cart_time",
            "first_purchase_time",
            "purchase_count",
            "purchase_revenue"
        ]
    ]

    # ========================================================
    # SAVE
    # ========================================================

    records = []

    for row in result.itertuples(index=False):

        records.append(
            (
                int(row.user_id),
                row.brand,
                int(row.viewed),
                int(row.added_to_cart),
                int(row.purchased),

                (
                    row.first_view_time.isoformat()
                    if pd.notna(row.first_view_time)
                    else None
                ),

                (
                    row.first_cart_time.isoformat()
                    if pd.notna(row.first_cart_time)
                    else None
                ),

                (
                    row.first_purchase_time.isoformat()
                    if pd.notna(row.first_purchase_time)
                    else None
                ),

                int(row.purchase_count),

                float(row.purchase_revenue)
            )
        )

    cursor.executemany(
        """
        INSERT INTO user_brand_state (

            user_id,
            brand,
            viewed,
            added_to_cart,
            purchased,
            first_view_time,
            first_cart_time,
            first_purchase_time,
            purchase_count,
            purchase_revenue

        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

        ON CONFLICT(
            user_id,
            brand
        )

        DO UPDATE SET

            viewed = excluded.viewed,

            added_to_cart =
                excluded.added_to_cart,

            purchased =
                excluded.purchased,

            first_view_time =
                excluded.first_view_time,

            first_cart_time =
                excluded.first_cart_time,

            first_purchase_time =
                excluded.first_purchase_time,

            purchase_count =
                excluded.purchase_count,

            purchase_revenue =
                excluded.purchase_revenue
        """,
        records
    )

    connection.commit()



def run_brand_analysis(max_chunks=None):
    """
    Build brand-level chronological funnel analysis.

    Parameters
    ----------
    max_chunks : int or None
        Number of chunks to process.
        None = process the complete dataset.
    """

    EDA_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------
    # REMOVE PREVIOUS TEST / PRODUCTION FILES
    # ------------------------------------------------------------

    if BRAND_DB.exists():
        BRAND_DB.unlink()

    if BRAND_OUTPUT.exists():
        BRAND_OUTPUT.unlink()

    # ------------------------------------------------------------
    # CREATE DATABASE
    # ------------------------------------------------------------

    conn = create_brand_database(BRAND_DB)

    total_rows = 0
    chunks_processed = 0

    start_time = time.time()

    try:

        # --------------------------------------------------------
        # READ CLEAN EVENTS IN CHUNKS
        # --------------------------------------------------------

        chunks = pd.read_csv(
            CLEAN_EVENTS_FILE,
            chunksize=CHUNK_SIZE
        )

        for df in chunks:

            chunks_processed += 1

            print("\n" + "=" * 70)
            print(
                f"Processing brand chunk "
                f"{chunks_processed}"
            )
            print("=" * 70)

            print(
                f"Rows: {len(df):,}"
            )

            total_rows += len(df)

            # ----------------------------------------------------
            # PROCESS CHUNK
            # ----------------------------------------------------

            process_brand_chunk(
                df,
                conn
            )

            # ----------------------------------------------------
            # SHOW CURRENT STATE SIZE
            # ----------------------------------------------------

            brand_pairs = conn.execute(
                """
                SELECT COUNT(*)
                FROM user_brand_state
                """
            ).fetchone()[0]

            print(
                f"User-brand pairs tracked: "
                f"{brand_pairs:,}"
            )

            # ----------------------------------------------------
            # TEST STOP
            # ----------------------------------------------------

            if (
                max_chunks is not None
                and chunks_processed >= max_chunks
            ):

                print(
                    f"\nStopping after "
                    f"{max_chunks} chunk(s) "
                    f"for testing."
                )

                break

        # --------------------------------------------------------
        # BUILD BRAND SUMMARY
        # --------------------------------------------------------

        brand_summary = pd.read_sql_query(
            """
            SELECT
                brand,

                SUM(viewed) AS view_users,

                SUM(added_to_cart)
                    AS cart_users,

                SUM(purchased)
                    AS purchase_users,

                SUM(purchase_count)
                    AS purchase_events,

                SUM(purchase_revenue)
                    AS revenue

            FROM user_brand_state

            GROUP BY brand

            ORDER BY revenue DESC
            """,
            conn
        )

        # --------------------------------------------------------
        # CONVERSION RATES
        # --------------------------------------------------------

        brand_summary[
            "view_to_cart_rate"
        ] = (
            brand_summary["cart_users"]
            /
            brand_summary["view_users"]
        )

        brand_summary[
            "cart_to_purchase_rate"
        ] = (
            brand_summary["purchase_users"]
            /
            brand_summary["cart_users"]
        )

        brand_summary[
            "view_to_purchase_rate"
        ] = (
            brand_summary["purchase_users"]
            /
            brand_summary["view_users"]
        )

        # --------------------------------------------------------
        # HANDLE DIVISION BY ZERO
        # --------------------------------------------------------

        rate_columns = [
            "view_to_cart_rate",
            "cart_to_purchase_rate",
            "view_to_purchase_rate"
        ]

        brand_summary[rate_columns] = (
            brand_summary[rate_columns]
            .replace(
                [float("inf"), -float("inf")],
                pd.NA
            )
        )

        # --------------------------------------------------------
        # SAVE OUTPUT
        # --------------------------------------------------------

        brand_summary.to_csv(
            BRAND_OUTPUT,
            index=False
        )

        elapsed = time.time() - start_time

        # --------------------------------------------------------
        # FINAL MESSAGE
        # --------------------------------------------------------

        print("\n" + "=" * 70)
        print("BRAND ANALYSIS COMPLETE")
        print("=" * 70)

        print(
            f"Chunks processed : "
            f"{chunks_processed:,}"
        )

        print(
            f"Event rows read  : "
            f"{total_rows:,}"
        )

        print(
            f"Brands           : "
            f"{len(brand_summary):,}"
        )

        print(
            f"Processing time  : "
            f"{elapsed:.2f} seconds"
        )

        print(
            f"\nOutput file:"
        )

        print(
            BRAND_OUTPUT.resolve()
        )

        return brand_summary

    finally:

        conn.close()



# ============================================================
# CREATE PRICE DATABASE
# ============================================================

def create_price_database(db_path):
    """
    Create persistent user-price-band funnel state.
    """

    connection = sqlite3.connect(db_path)

    cursor = connection.cursor()

    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.execute("PRAGMA temp_store=FILE;")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_price_state (

            user_id INTEGER NOT NULL,

            price_band TEXT NOT NULL,

            viewed INTEGER NOT NULL DEFAULT 0,

            added_to_cart INTEGER NOT NULL DEFAULT 0,

            purchased INTEGER NOT NULL DEFAULT 0,

            first_view_time TEXT,

            first_cart_time TEXT,

            first_purchase_time TEXT,

            purchase_count INTEGER NOT NULL DEFAULT 0,

            purchase_revenue REAL NOT NULL DEFAULT 0,

            PRIMARY KEY (
                user_id,
                price_band
            )
        );
        """
    )

    connection.commit()

    return connection



# ============================================================
# PRICE BAND
# ============================================================

def assign_price_band(price):
    """
    Assign an event price to a predefined USD price band.
    """

    if pd.isna(price):
        return "Unknown"

    if price == 0:
        return "$0"

    if price <= 50:
        return "$0–$50"

    if price <= 100:
        return "$50–$100"

    if price <= 250:
        return "$100–$250"

    if price <= 500:
        return "$250–$500"

    if price <= 1000:
        return "$500–$1,000"

    if price <= 2000:
        return "$1,000–$2,000"

    return "$2,000+"



# ============================================================
# PROCESS PRICE CHUNK
# ============================================================

def process_price_chunk(df, connection):
    """
    Process one event chunk and update
    user-price-band funnel state.

    Funnel:

    View
      ↓
    Add to Cart
      ↓
    Purchase
    """

    df = df.copy()

    # --------------------------------------------------------
    # PREPARE DATA
    # --------------------------------------------------------

    df["event_time"] = pd.to_datetime(
        df["event_time"],
        utc=True
    )

    df["event_type"] = (
        df["event_type"]
        .astype(str)
    )

    df["price"] = pd.to_numeric(
        df["price"],
        errors="coerce"
    )

    df["price_band"] = (
        df["price"]
        .apply(assign_price_band)
    )

    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------

    df = df.sort_values(
        [
            "user_id",
            "price_band",
            "event_time"
        ]
    )

    # --------------------------------------------------------
    # EVENT FLAGS
    # --------------------------------------------------------

    df["is_view"] = (
        df["event_type"] == "view"
    )

    df["is_cart"] = (
        df["event_type"] == "cart"
    )

    df["is_purchase"] = (
        df["event_type"] == "purchase"
    )

    # --------------------------------------------------------
    # CURRENT USER-PRICE KEYS
    # --------------------------------------------------------

    keys = (
        df[
            [
                "user_id",
                "price_band"
            ]
        ]
        .drop_duplicates()
    )

    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TEMP TABLE IF NOT EXISTS
        current_price_users (

            user_id INTEGER,

            price_band TEXT,

            PRIMARY KEY (
                user_id,
                price_band
            )
        );
        """
    )

    cursor.execute(
        "DELETE FROM current_price_users"
    )

    cursor.executemany(
        """
        INSERT OR IGNORE INTO
        current_price_users
        (
            user_id,
            price_band
        )

        VALUES (?, ?)
        """,
        [
            (
                int(row.user_id),
                row.price_band
            )
            for row in keys.itertuples(
                index=False
            )
        ]
    )

    connection.commit()

    # --------------------------------------------------------
    # GET PREVIOUS STATES
    # --------------------------------------------------------

    previous = pd.read_sql_query(
        """
        SELECT

            s.user_id,

            s.price_band,

            s.viewed
                AS viewed_previous,

            s.added_to_cart
                AS cart_previous,

            s.purchased
                AS purchased_previous,

            s.first_view_time
                AS first_view_previous,

            s.first_cart_time
                AS first_cart_previous,

            s.first_purchase_time
                AS first_purchase_previous,

            s.purchase_count
                AS purchase_count_previous,

            s.purchase_revenue
                AS revenue_previous

        FROM user_price_state AS s

        INNER JOIN current_price_users AS u

            ON s.user_id = u.user_id

            AND s.price_band =
                u.price_band
        """,
        connection
    )

    # --------------------------------------------------------
    # MERGE PREVIOUS STATE
    # --------------------------------------------------------

    df = df.merge(
        previous[
            [
                "user_id",
                "price_band",
                "viewed_previous",
                "cart_previous",
                "purchased_previous"
            ]
        ],
        on=[
            "user_id",
            "price_band"
        ],
        how="left"
    )

    # --------------------------------------------------------
    # PREVIOUS FLAGS
    # --------------------------------------------------------

    for column in [
        "viewed_previous",
        "cart_previous",
        "purchased_previous"
    ]:

        df[column] = (
            pd.to_numeric(
                df[column],
                errors="coerce"
            )
            .fillna(0)
            .astype("int8")
        )

    # --------------------------------------------------------
    # VIEW
    # --------------------------------------------------------

    view_count = (
        df["is_view"]
        .groupby(
            [
                df["user_id"],
                df["price_band"]
            ]
        )
        .cumsum()
    )

    df["view_seen"] = (
        (view_count > 0)
        |
        (df["viewed_previous"] == 1)
    )

    # --------------------------------------------------------
    # CART
    # --------------------------------------------------------

    df["qualifying_cart"] = (
        df["is_cart"]
        &
        df["view_seen"]
    )

    cart_count = (
        df["qualifying_cart"]
        .groupby(
            [
                df["user_id"],
                df["price_band"]
            ]
        )
        .cumsum()
    )

    df["cart_seen"] = (
        (cart_count > 0)
        |
        (df["cart_previous"] == 1)
    )

    # --------------------------------------------------------
    # PURCHASE
    # --------------------------------------------------------

    df["qualifying_purchase"] = (
        df["is_purchase"]
        &
        df["cart_seen"]
    )

    # --------------------------------------------------------
    # TIMESTAMPS
    # --------------------------------------------------------

    df["view_time"] = (
        df["event_time"]
        .where(df["is_view"])
    )

    df["cart_time"] = (
        df["event_time"]
        .where(df["qualifying_cart"])
    )

    df["purchase_time"] = (
        df["event_time"]
        .where(df["qualifying_purchase"])
    )

    # --------------------------------------------------------
    # AGGREGATION
    # --------------------------------------------------------

    summary = (
        df.groupby(
            [
                "user_id",
                "price_band"
            ],
            sort=False
        )
        .agg(

            any_view=(
                "is_view",
                "any"
            ),

            any_cart=(
                "qualifying_cart",
                "any"
            ),

            any_purchase=(
                "qualifying_purchase",
                "any"
            ),

            first_view_time=(
                "view_time",
                "min"
            ),

            first_cart_time=(
                "cart_time",
                "min"
            ),

            first_purchase_time=(
                "purchase_time",
                "min"
            ),

            purchase_count=(
                "is_purchase",
                "sum"
            ),

            purchase_revenue=(
                "price",
                lambda x: x[
                    df.loc[
                        x.index,
                        "is_purchase"
                    ]
                ].sum()
            )
        )
        .reset_index()
    )

    # --------------------------------------------------------
    # MERGE PREVIOUS COMPLETE STATE
    # --------------------------------------------------------

    result = summary.merge(
        previous,
        on=[
            "user_id",
            "price_band"
        ],
        how="left"
    )

    # --------------------------------------------------------
    # NUMERIC PREVIOUS VALUES
    # --------------------------------------------------------

    for column in [
        "viewed_previous",
        "cart_previous",
        "purchased_previous",
        "purchase_count_previous",
        "revenue_previous"
    ]:

        result[column] = (
            pd.to_numeric(
                result[column],
                errors="coerce"
            )
            .fillna(0)
        )

    # --------------------------------------------------------
    # FINAL FLAGS
    # --------------------------------------------------------

    result["viewed"] = (
        result["viewed_previous"].astype(bool)
        |
        result["any_view"].astype(bool)
    ).astype("int8")

    result["added_to_cart"] = (
        result["cart_previous"].astype(bool)
        |
        result["any_cart"].astype(bool)
    ).astype("int8")

    result["purchased"] = (
        result["purchased_previous"].astype(bool)
        |
        result["any_purchase"].astype(bool)
    ).astype("int8")

    # --------------------------------------------------------
    # PURCHASE METRICS
    # --------------------------------------------------------

    result["purchase_count"] = (
        result["purchase_count_previous"]
        +
        result["purchase_count"]
    ).astype("int64")

    result["purchase_revenue"] = (
        result["revenue_previous"]
        +
        result["purchase_revenue"]
    ).astype("float64")

    # --------------------------------------------------------
    # TIMESTAMPS
    # --------------------------------------------------------

    timestamp_columns = [
        "first_view_previous",
        "first_cart_previous",
        "first_purchase_previous",
        "first_view_time",
        "first_cart_time",
        "first_purchase_time"
    ]

    for column in timestamp_columns:

        result[column] = pd.to_datetime(
            result[column],
            utc=True,
            errors="coerce"
        )

    result["first_view_time"] = (
        result[
            [
                "first_view_previous",
                "first_view_time"
            ]
        ]
        .min(axis=1)
    )

    result["first_cart_time"] = (
        result[
            [
                "first_cart_previous",
                "first_cart_time"
            ]
        ]
        .min(axis=1)
    )

    result["first_purchase_time"] = (
        result[
            [
                "first_purchase_previous",
                "first_purchase_time"
            ]
        ]
        .min(axis=1)
    )

    # --------------------------------------------------------
    # SAVE STATE
    # --------------------------------------------------------

    records = []

    for row in result.itertuples(index=False):

        records.append(
            (
                int(row.user_id),
                row.price_band,
                int(row.viewed),
                int(row.added_to_cart),
                int(row.purchased),

                (
                    row.first_view_time.isoformat()
                    if pd.notna(
                        row.first_view_time
                    )
                    else None
                ),

                (
                    row.first_cart_time.isoformat()
                    if pd.notna(
                        row.first_cart_time
                    )
                    else None
                ),

                (
                    row.first_purchase_time.isoformat()
                    if pd.notna(
                        row.first_purchase_time
                    )
                    else None
                ),

                int(row.purchase_count),

                float(row.purchase_revenue)
            )
        )

    cursor.executemany(
        """
        INSERT INTO user_price_state (

            user_id,
            price_band,
            viewed,
            added_to_cart,
            purchased,
            first_view_time,
            first_cart_time,
            first_purchase_time,
            purchase_count,
            purchase_revenue
        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

        ON CONFLICT(
            user_id,
            price_band
        )

        DO UPDATE SET

            viewed =
                excluded.viewed,

            added_to_cart =
                excluded.added_to_cart,

            purchased =
                excluded.purchased,

            first_view_time =
                excluded.first_view_time,

            first_cart_time =
                excluded.first_cart_time,

            first_purchase_time =
                excluded.first_purchase_time,

            purchase_count =
                excluded.purchase_count,

            purchase_revenue =
                excluded.purchase_revenue
        """,
        records
    )

    connection.commit()



# ============================================================
# RUN PRICE BAND ANALYSIS
# ============================================================

def run_price_analysis(max_chunks=None):
    """
    Build price-band chronological funnel analysis.

    Parameters
    ----------
    max_chunks : int or None
        Number of chunks to process.
        None = process the complete dataset.
    """

    EDA_DIR.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------
    # REMOVE PREVIOUS TEST / PRODUCTION FILES
    # --------------------------------------------------------

    if PRICE_DB.exists():
        PRICE_DB.unlink()

    if PRICE_OUTPUT.exists():
        PRICE_OUTPUT.unlink()

    # --------------------------------------------------------
    # CREATE DATABASE
    # --------------------------------------------------------

    conn = create_price_database(PRICE_DB)

    total_rows = 0
    chunks_processed = 0

    start_time = time.time()

    try:

        # ----------------------------------------------------
        # READ CLEAN EVENTS
        # ----------------------------------------------------

        chunks = pd.read_csv(
            CLEAN_EVENTS_FILE,
            chunksize=CHUNK_SIZE
        )

        for df in chunks:

            chunks_processed += 1

            print("\n" + "=" * 70)
            print(
                f"Processing price-band chunk "
                f"{chunks_processed}"
            )
            print("=" * 70)

            print(
                f"Rows: {len(df):,}"
            )

            total_rows += len(df)

            # ------------------------------------------------
            # PROCESS CHUNK
            # ------------------------------------------------

            process_price_chunk(
                df,
                conn
            )

            # ------------------------------------------------
            # CURRENT STATE SIZE
            # ------------------------------------------------

            price_pairs = conn.execute(
                """
                SELECT COUNT(*)
                FROM user_price_state
                """
            ).fetchone()[0]

            print(
                f"User-price-band pairs tracked: "
                f"{price_pairs:,}"
            )

            # ------------------------------------------------
            # TEST STOP
            # ------------------------------------------------

            if (
                max_chunks is not None
                and chunks_processed >= max_chunks
            ):

                print(
                    f"\nStopping after "
                    f"{max_chunks} chunk(s) "
                    f"for testing."
                )

                break

        # ----------------------------------------------------
        # BUILD PRICE SUMMARY
        # ----------------------------------------------------

        price_summary = pd.read_sql_query(
            """
            SELECT

                price_band,

                SUM(viewed)
                    AS view_users,

                SUM(added_to_cart)
                    AS cart_users,

                SUM(purchased)
                    AS purchase_users,

                SUM(purchase_count)
                    AS purchase_events,

                SUM(purchase_revenue)
                    AS revenue

            FROM user_price_state

            GROUP BY price_band
            """,
            conn
        )

        # ----------------------------------------------------
        # PRICE BAND ORDER
        # ----------------------------------------------------

        band_order = [
            "$0",
            "$0–$50",
            "$50–$100",
            "$100–$250",
            "$250–$500",
            "$500–$1,000",
            "$1,000–$2,000",
            "$2,000+",
            "Unknown"
        ]

        price_summary["price_band"] = pd.Categorical(
            price_summary["price_band"],
            categories=band_order,
            ordered=True
        )

        price_summary = (
            price_summary
            .sort_values("price_band")
            .reset_index(drop=True)
        )

        # ----------------------------------------------------
        # CONVERSION RATES
        # ----------------------------------------------------

        price_summary[
            "view_to_cart_rate"
        ] = (
            price_summary["cart_users"]
            /
            price_summary["view_users"]
        )

        price_summary[
            "cart_to_purchase_rate"
        ] = (
            price_summary["purchase_users"]
            /
            price_summary["cart_users"]
        )

        price_summary[
            "view_to_purchase_rate"
        ] = (
            price_summary["purchase_users"]
            /
            price_summary["view_users"]
        )

        # ----------------------------------------------------
        # HANDLE DIVISION BY ZERO
        # ----------------------------------------------------

        rate_columns = [
            "view_to_cart_rate",
            "cart_to_purchase_rate",
            "view_to_purchase_rate"
        ]

        price_summary[rate_columns] = (
            price_summary[rate_columns]
            .replace(
                [float("inf"), -float("inf")],
                pd.NA
            )
        )

        # ----------------------------------------------------
        # SAVE
        # ----------------------------------------------------

        price_summary.to_csv(
            PRICE_OUTPUT,
            index=False
        )

        elapsed = time.time() - start_time

        # ----------------------------------------------------
        # FINAL MESSAGE
        # ----------------------------------------------------

        print("\n" + "=" * 70)
        print("PRICE BAND ANALYSIS COMPLETE")
        print("=" * 70)

        print(
            f"Chunks processed : "
            f"{chunks_processed:,}"
        )

        print(
            f"Event rows read  : "
            f"{total_rows:,}"
        )

        print(
            f"Price bands      : "
            f"{len(price_summary):,}"
        )

        print(
            f"Processing time  : "
            f"{elapsed:.2f} seconds"
        )

        print("\nOutput file:")

        print(
            PRICE_OUTPUT.resolve()
        )

        return price_summary

    finally:

        conn.close()









# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    # build_category_analysis(
    #     max_chunks=None
    # )

    # run_brand_analysis(
    #     max_chunks=None
    # )

    run_price_analysis(
        max_chunks=None
    )