"""
funnel_analysis.py

Purpose:
Builds a user-level e-commerce funnel from the cleaned event dataset.

Funnel:
View → Add to Cart → Purchase

The funnel is constructed chronologically at the unique-user level
while processing the large dataset in chunks.

Why:
The raw data contains event-level records, but funnel conversion
analysis requires one consolidated state per user.
"""


import sqlite3
from pathlib import Path

import pandas as pd


# ============================================================
# PATHS
# ============================================================

CLEAN_EVENTS_FILE = Path(
    "../data/processed/clean_events.csv"
)

FUNNEL_FILE = Path(
    "../data/processed/user_funnel.csv"
)

FUNNEL_DB = Path(
    "../data/processed/user_funnel.db"
)


# ============================================================
# SETTINGS
# ============================================================

CHUNK_SIZE = 500_000


# ============================================================
# CREATE DATABASE
# ============================================================

def create_funnel_database(db_path):
    """
    Create the persistent user funnel state database.
    """

    connection = sqlite3.connect(db_path)

    cursor = connection.cursor()

    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.execute("PRAGMA temp_store=FILE;")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_funnel_state (

            user_id INTEGER PRIMARY KEY,

            viewed INTEGER NOT NULL DEFAULT 0,

            added_to_cart INTEGER NOT NULL DEFAULT 0,

            purchased INTEGER NOT NULL DEFAULT 0,

            first_view_time TEXT,

            first_cart_time TEXT,

            first_purchase_time TEXT,

            purchase_count INTEGER NOT NULL DEFAULT 0,

            purchase_revenue REAL NOT NULL DEFAULT 0

        );
        """
    )

    # Temporary table containing users in the current chunk
    cursor.execute(
        """
        CREATE TEMP TABLE IF NOT EXISTS current_users (
            user_id INTEGER PRIMARY KEY
        );
        """
    )

    connection.commit()

    return connection


# ============================================================
# GET EXISTING USER STATES
# ============================================================

def get_existing_states(connection, user_ids):
    """
    Retrieve funnel states only for users appearing in
    the current chunk.

    The complete user state table is never loaded.
    """

    cursor = connection.cursor()

    # Clear previous chunk users
    cursor.execute(
        "DELETE FROM current_users"
    )

    cursor.executemany(
        """
        INSERT OR IGNORE INTO current_users
        (user_id)
        VALUES (?)
        """,
        [
            (int(user_id),)
            for user_id in user_ids
        ]
    )

    connection.commit()

    query = """
        SELECT
            s.user_id,
            s.viewed,
            s.added_to_cart,
            s.purchased,
            s.first_view_time,
            s.first_cart_time,
            s.first_purchase_time,
            s.purchase_count,
            s.purchase_revenue

        FROM user_funnel_state AS s

        INNER JOIN current_users AS u
            ON s.user_id = u.user_id
    """

    states = pd.read_sql_query(
        query,
        connection
    )

    return states


# ============================================================
# CALCULATE CHUNK FUNNEL
# ============================================================

def calculate_chunk_funnel(df, existing_states):
    """
    Calculate funnel progression for the current chunk.

    Funnel logic:

        View
          ↓
        Cart
          ↓
        Purchase

    The sequence must occur chronologically.
    """

    # ========================================================
    # PREPARE DATA
    # ========================================================

    df = df.copy()

    df["event_time"] = pd.to_datetime(
        df["event_time"],
        utc=True
    )

    # Ensure chronological order within each user
    df = df.sort_values(
        ["user_id", "event_time"]
    )

    # ========================================================
    # PREPARE EXISTING USER STATES
    # ========================================================

    state_columns = [
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

    if existing_states.empty:

        existing_states = pd.DataFrame(
            columns=state_columns
        )

        # Explicit dtypes for an empty state table
        existing_states["user_id"] = (
            existing_states["user_id"]
            .astype("int64")
        )

    else:

        existing_states = existing_states.copy()

        existing_states["user_id"] = (
            existing_states["user_id"]
            .astype("int64")
        )

    # ========================================================
    # EVENT FLAGS
    # ========================================================

    event_type = df["event_type"].astype(str)

    df["is_view"] = (
        event_type == "view"
    )

    df["is_cart"] = (
        event_type == "cart"
    )

    df["is_purchase"] = (
        event_type == "purchase"
    )

    # ========================================================
    # PREVIOUS USER STATE LOOKUP
    # ========================================================

    if existing_states.empty:

        previous_viewed = pd.Series(
            0,
            index=df.index,
            dtype="int8"
        )

        previous_cart = pd.Series(
            0,
            index=df.index,
            dtype="int8"
        )

        previous_purchased = pd.Series(
            0,
            index=df.index,
            dtype="int8"
        )

    else:

        state_lookup = existing_states.set_index(
            "user_id"
        )

        previous_viewed = (
            df["user_id"]
            .map(state_lookup["viewed"])
            .fillna(0)
            .astype("int8")
        )

        previous_cart = (
            df["user_id"]
            .map(state_lookup["added_to_cart"])
            .fillna(0)
            .astype("int8")
        )

        previous_purchased = (
            df["user_id"]
            .map(state_lookup["purchased"])
            .fillna(0)
            .astype("int8")
        )

    df["previous_viewed"] = previous_viewed
    df["previous_cart"] = previous_cart
    df["previous_purchased"] = previous_purchased

    # ========================================================
    # VIEW STAGE
    # ========================================================

    view_count = (
        df["is_view"]
        .groupby(df["user_id"])
        .cumsum()
    )

    df["view_seen"] = (
        (view_count > 0)
        |
        (df["previous_viewed"] == 1)
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
        .groupby(df["user_id"])
        .cumsum()
    )

    df["cart_seen"] = (
        (cart_count > 0)
        |
        (df["previous_cart"] == 1)
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
    # PREPARE TIME COLUMNS
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
    # USER-LEVEL AGGREGATION
    # ========================================================

    chunk_summary = (
        df.groupby(
            "user_id",
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

            first_view_time_chunk=(
                "view_time",
                "min"
            ),

            first_cart_time_chunk=(
                "cart_time",
                "min"
            ),

            first_purchase_time_chunk=(
                "purchase_time",
                "min"
            ),

            purchase_count_chunk=(
                "is_purchase",
                "sum"
            ),

            purchase_revenue_chunk=(
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
    # MERGE WITH PREVIOUS USER STATE
    # ========================================================

    previous = existing_states.rename(
        columns={
            "viewed": "viewed_previous",
            "added_to_cart": "added_to_cart_previous",
            "purchased": "purchased_previous",
            "first_view_time": "first_view_time_previous",
            "first_cart_time": "first_cart_time_previous",
            "first_purchase_time": "first_purchase_time_previous",
            "purchase_count": "purchase_count_previous",
            "purchase_revenue": "purchase_revenue_previous",
        }
    )

    result = chunk_summary.merge(
        previous,
        on="user_id",
        how="left"
    )

    # ========================================================
    # FILL PREVIOUS NUMERIC STATE
    # ========================================================

    numeric_previous_columns = [
        "viewed_previous",
        "added_to_cart_previous",
        "purchased_previous",
        "purchase_count_previous",
        "purchase_revenue_previous",
    ]

    for column in numeric_previous_columns:

        result[column] = (
            pd.to_numeric(
                result[column],
                errors="coerce"
            )
            .fillna(0)
        )

    # ========================================================
    # FUNNEL FLAGS
    # ========================================================

    result["viewed"] = (
        result["viewed_previous"].astype(bool)
        |
        result["any_view"].astype(bool)
    ).astype("int8")

    result["added_to_cart"] = (
        result["added_to_cart_previous"].astype(bool)
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
        result["purchase_count_chunk"]
    ).astype("int64")

    result["purchase_revenue"] = (
        result["purchase_revenue_previous"]
        +
        result["purchase_revenue_chunk"]
    ).astype("float64")

    # ========================================================
    # FIRST VIEW TIME
    # ========================================================

    result["first_view_time_previous"] = pd.to_datetime(
        result["first_view_time_previous"],
        utc=True,
        errors="coerce"
    )

    result["first_view_time_chunk"] = pd.to_datetime(
        result["first_view_time_chunk"],
        utc=True,
        errors="coerce"
    )

    result["first_view_time"] = (
        result[
            [
                "first_view_time_previous",
                "first_view_time_chunk"
            ]
        ]
        .min(axis=1)
    )

    # ========================================================
    # FIRST CART TIME
    # ========================================================

    result["first_cart_time_previous"] = pd.to_datetime(
        result["first_cart_time_previous"],
        utc=True,
        errors="coerce"
    )

    result["first_cart_time_chunk"] = pd.to_datetime(
        result["first_cart_time_chunk"],
        utc=True,
        errors="coerce"
    )

    result["first_cart_time"] = (
        result[
            [
                "first_cart_time_previous",
                "first_cart_time_chunk"
            ]
        ]
        .min(axis=1)
    )

    # ========================================================
    # FIRST PURCHASE TIME
    # ========================================================

    result["first_purchase_time_previous"] = pd.to_datetime(
        result["first_purchase_time_previous"],
        utc=True,
        errors="coerce"
    )

    result["first_purchase_time_chunk"] = pd.to_datetime(
        result["first_purchase_time_chunk"],
        utc=True,
        errors="coerce"
    )

    result["first_purchase_time"] = (
        result[
            [
                "first_purchase_time_previous",
                "first_purchase_time_chunk"
            ]
        ]
        .min(axis=1)
    )

    # ========================================================
    # FINAL OUTPUT COLUMNS
    # ========================================================

    result = result[
        [
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
    ]

    return result


# ============================================================
# SAVE USER STATES
# ============================================================

def save_user_states(
    connection,
    user_states
):
    """
    Batch update the persistent user funnel database.
    """

    records = []

    for row in user_states.itertuples(
        index=False
    ):

        records.append(
            (
                int(row.user_id),

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

    cursor = connection.cursor()

    cursor.executemany(
        """
        INSERT INTO user_funnel_state (

            user_id,
            viewed,
            added_to_cart,
            purchased,
            first_view_time,
            first_cart_time,
            first_purchase_time,
            purchase_count,
            purchase_revenue

        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)

        ON CONFLICT(user_id)
        DO UPDATE SET

            viewed = excluded.viewed,

            added_to_cart = excluded.added_to_cart,

            purchased = excluded.purchased,

            first_view_time =
                excluded.first_view_time,

            first_cart_time =
                excluded.first_cart_time,

            first_purchase_time =
                excluded.first_purchase_time,

            purchase_count =
                excluded.purchase_count,

            purchase_revenue =
                excluded.purchase_revenue;
        """,
        records
    )

    connection.commit()


# ============================================================
# EXPORT FINAL FUNNEL
# ============================================================

def export_funnel(
    connection,
    output_file
):
    """
    Export final user-level funnel.
    """

    query = """
        SELECT

            user_id,
            viewed,
            added_to_cart,
            purchased,
            first_view_time,
            first_cart_time,
            first_purchase_time,
            purchase_count,
            purchase_revenue

        FROM user_funnel_state

        ORDER BY user_id
    """

    funnel_df = pd.read_sql_query(
        query,
        connection
    )

    funnel_df.to_csv(
        output_file,
        index=False
    )

    return funnel_df


# ============================================================
# BUILD COMPLETE FUNNEL
# ============================================================

def build_user_funnel(
    input_file=CLEAN_EVENTS_FILE,
    output_file=FUNNEL_FILE,
    db_file=FUNNEL_DB,
    chunk_size=CHUNK_SIZE,
    max_chunks=None
):
    """
    Build the complete user-level funnel.

    Events must be chronologically ordered in the input CSV.
    """

    input_file = Path(input_file)
    output_file = Path(output_file)
    db_file = Path(db_file)

    if not input_file.exists():

        raise FileNotFoundError(
            f"Clean events file not found:\n"
            f"{input_file.resolve()}"
        )

    # --------------------------------------------------------
    # Remove previous outputs
    # --------------------------------------------------------

    if output_file.exists():
        output_file.unlink()

    if db_file.exists():
        db_file.unlink()

    # --------------------------------------------------------
    # Create database
    # --------------------------------------------------------

    connection = create_funnel_database(
        db_file
    )

    chunks = pd.read_csv(
        input_file,
        chunksize=chunk_size
    )

    total_rows = 0
    chunk_number = 0

    previous_chunk_max_time = None

    try:

        for df in chunks:

            chunk_number += 1

            print("\n" + "=" * 70)

            print(
                f"Processing funnel chunk "
                f"{chunk_number}"
            )

            print("=" * 70)

            print(
                f"Rows: {len(df):,}"
            )

            total_rows += len(df)

            # ------------------------------------------------
            # Check chronological order
            # ------------------------------------------------

            chunk_times = pd.to_datetime(
                df["event_time"],
                utc=True
            )

            chunk_min_time = chunk_times.min()
            chunk_max_time = chunk_times.max()

            if (
                previous_chunk_max_time is not None
                and chunk_min_time < previous_chunk_max_time
            ):

                raise ValueError(
                    "The cleaned event file is not "
                    "chronologically ordered."
                )

            previous_chunk_max_time = (
                chunk_max_time
            )

            # ------------------------------------------------
            # Current users
            # ------------------------------------------------

            user_ids = (
                df["user_id"]
                .drop_duplicates()
                .tolist()
            )

            # ------------------------------------------------
            # Get previous states
            # ------------------------------------------------

            existing_states = (
                get_existing_states(
                    connection,
                    user_ids
                )
            )

            # ------------------------------------------------
            # Calculate current chunk
            # ------------------------------------------------

            user_states = calculate_chunk_funnel(
                df,
                existing_states
            )

            # ------------------------------------------------
            # Save updated states
            # ------------------------------------------------

            save_user_states(
                connection,
                user_states
            )

            # ------------------------------------------------
            # Progress
            # ------------------------------------------------

            current_users = connection.execute(
                """
                SELECT COUNT(*)
                FROM user_funnel_state
                """
            ).fetchone()[0]

            print(
                f"Users tracked so far: "
                f"{current_users:,}"
            )

            # ------------------------------------------------
            # Testing limit
            # ------------------------------------------------

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
        # Export
        # ----------------------------------------------------

        funnel_df = export_funnel(
            connection,
            output_file
        )

    finally:

        connection.close()

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("USER FUNNEL BUILD COMPLETE")
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
        f"Unique users     : "
        f"{len(funnel_df):,}"
    )

    print(
        "\nOutput file:"
    )

    print(
        output_file.resolve()
    )

    return funnel_df


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    build_user_funnel()