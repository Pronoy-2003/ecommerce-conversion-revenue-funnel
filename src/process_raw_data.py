"""
process_raw_data.py

Purpose:
Runs the production data-cleaning pipeline on the large raw dataset.

The pipeline processes the data in chunks, standardizes the data,
handles missing values, creates datetime features, and performs
global exact-duplicate removal.

Why:
The raw dataset contains more than 42 million rows, so the complete
cleaning process must be memory-efficient and able to detect duplicates
across different chunks.
"""


import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

from data_cleaning import (
    standardize_dtypes,
    handle_missing_values,
    add_datetime_features,
)


# ============================================================
# PATHS
# ============================================================

RAW_FILE = Path("../data/raw/2019-Oct.csv")

PROCESSED_DIR = Path("../data/processed")
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = PROCESSED_DIR / "clean_events.csv"
DUPLICATE_DB = PROCESSED_DIR / "duplicate_index.db"


# ============================================================
# SETTINGS
# ============================================================

CHUNK_SIZE = 500_000

DUPLICATE_COLUMNS = [
    "event_time",
    "event_type",
    "product_id",
    "category_id",
    "category_code",
    "brand",
    "price",
    "user_id",
    "user_session",
]


# ============================================================
# CREATE 128-BIT DUPLICATE FINGERPRINT
# ============================================================

def create_duplicate_fingerprint(df):
    """
    Create a 128-bit fingerprint from all original event columns.

    Two independent 64-bit pandas hashes are combined into
    a 16-byte fingerprint.

    This is much faster and more memory-efficient than creating
    SHA-256 strings for 42M+ rows.
    """

    key_df = df[DUPLICATE_COLUMNS].copy()

    # event_type was converted to categorical during cleaning.
    # Convert it back to string so category codes cannot vary
    # between chunks.
    key_df["event_type"] = key_df["event_type"].astype("string")

    # First 64-bit hash
    hash_1 = pd.util.hash_pandas_object(
        key_df,
        index=False,
        categorize=True
    ).to_numpy(dtype=np.uint64)

    # Second hash using reversed column order
    hash_2 = pd.util.hash_pandas_object(
        key_df[DUPLICATE_COLUMNS[::-1]],
        index=False,
        categorize=True
    ).to_numpy(dtype=np.uint64)

    # Combine the two 64-bit hashes into a 128-bit fingerprint
    fingerprints = [
        int(h1).to_bytes(8, byteorder="little")
        + int(h2).to_bytes(8, byteorder="little")
        for h1, h2 in zip(hash_1, hash_2)
    ]

    return fingerprints


# ============================================================
# CREATE SQLITE DATABASE
# ============================================================

def create_duplicate_database(db_path):
    """
    Create a disk-backed SQLite database containing fingerprints
    of all events already processed.
    """

    connection = sqlite3.connect(db_path)

    cursor = connection.cursor()

    # Improve bulk-processing performance
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.execute("PRAGMA temp_store=FILE;")

    # Persistent global duplicate index
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS seen_events (
            event_hash BLOB PRIMARY KEY
        ) WITHOUT ROWID;
        """
    )

    # Temporary table for the current chunk
    cursor.execute(
        """
        CREATE TEMP TABLE IF NOT EXISTS current_chunk (
            row_id INTEGER PRIMARY KEY,
            event_hash BLOB UNIQUE
        );
        """
    )

    connection.commit()

    return connection


# ============================================================
# FIND GLOBALLY UNIQUE EVENTS
# ============================================================

def get_new_row_ids(connection, fingerprints):
    """
    Determine which rows are new globally.

    Handles:
        1. duplicates inside the current chunk
        2. duplicates from previous chunks

    The complete seen_events table is NEVER loaded into RAM.
    """

    cursor = connection.cursor()

    # Clear previous temporary chunk
    cursor.execute("DELETE FROM current_chunk")

    # Insert current chunk fingerprints.
    #
    # UNIQUE event_hash means duplicate events inside this
    # chunk are automatically ignored.
    chunk_records = [
        (row_id, fingerprint)
        for row_id, fingerprint in enumerate(fingerprints)
    ]

    cursor.executemany(
        """
        INSERT OR IGNORE INTO current_chunk
        (row_id, event_hash)
        VALUES (?, ?)
        """,
        chunk_records
    )

    # Find fingerprints that have NEVER appeared before.
    #
    # This compares only the current chunk against the
    # disk-backed global index.
    new_rows = cursor.execute(
        """
        SELECT
            c.row_id,
            c.event_hash
        FROM current_chunk AS c
        WHERE NOT EXISTS (
            SELECT 1
            FROM seen_events AS s
            WHERE s.event_hash = c.event_hash
        )
        ORDER BY c.row_id;
        """
    ).fetchall()

    # Add newly discovered fingerprints to the global index.
    cursor.executemany(
        """
        INSERT INTO seen_events (event_hash)
        VALUES (?)
        """,
        [
            (event_hash,)
            for _, event_hash in new_rows
        ]
    )

    connection.commit()

    return [
        row_id
        for row_id, _ in new_rows
    ]


# ============================================================
# PROCESS DATASET
# ============================================================

def process_dataset(
    input_file=RAW_FILE,
    output_file=OUTPUT_FILE,
    db_file=DUPLICATE_DB,
    chunk_size=CHUNK_SIZE,
    max_chunks=None,
):
    """
    Process the complete raw dataset in chunks.

    Cleaning:
        - standardize data types
        - fill missing descriptive values
        - add datetime features
        - remove global exact duplicates

    Parameters
    ----------
    input_file : Path
        Raw CSV file.

    output_file : Path
        Cleaned CSV output.

    db_file : Path
        SQLite global duplicate index.

    chunk_size : int
        Number of rows processed per chunk.

    max_chunks : int or None
        Useful for testing.
        max_chunks=1 processes only the first 500k rows.
    """

    input_file = Path(input_file)
    output_file = Path(output_file)
    db_file = Path(db_file)

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    db_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Safety check
    # --------------------------------------------------------

    if not input_file.exists():
        raise FileNotFoundError(
            f"Raw dataset not found:\n{input_file.resolve()}"
        )

    # --------------------------------------------------------
    # Remove previous output/database
    # --------------------------------------------------------

    if output_file.exists():
        output_file.unlink()

    if db_file.exists():
        db_file.unlink()

    # --------------------------------------------------------
    # Create database
    # --------------------------------------------------------

    connection = create_duplicate_database(db_file)

    # --------------------------------------------------------
    # Read CSV in chunks
    # --------------------------------------------------------

    chunks = pd.read_csv(
        input_file,
        chunksize=chunk_size
    )

    total_input_rows = 0
    total_output_rows = 0
    total_duplicates_removed = 0

    chunk_number = 0
    first_output = True

    try:

        for df in chunks:

            chunk_number += 1

            print("\n" + "=" * 70)
            print(f"Processing chunk {chunk_number}")
            print("=" * 70)

            original_rows = len(df)

            total_input_rows += original_rows

            print(f"Rows read: {original_rows:,}")

            # ------------------------------------------------
            # STEP 1 — Standardize data types
            # ------------------------------------------------

            df = standardize_dtypes(df)

            # ------------------------------------------------
            # STEP 2 — Handle missing descriptive values
            # ------------------------------------------------

            df = handle_missing_values(df)

            # ------------------------------------------------
            # STEP 3 — Add datetime features
            # ------------------------------------------------

            df = add_datetime_features(df)

            # ------------------------------------------------
            # STEP 4 — Create duplicate fingerprint
            # ------------------------------------------------

            fingerprints = create_duplicate_fingerprint(df)

            # ------------------------------------------------
            # STEP 5 — Global deduplication
            # ------------------------------------------------

            new_row_ids = get_new_row_ids(
                connection,
                fingerprints
            )

            # Keep only globally unique events
            df_clean = df.iloc[new_row_ids].copy()

            cleaned_rows = len(df_clean)

            duplicates_removed = (
                original_rows - cleaned_rows
            )

            total_output_rows += cleaned_rows
            total_duplicates_removed += duplicates_removed

            print(
                f"Rows after deduplication: "
                f"{cleaned_rows:,}"
            )

            print(
                f"Duplicates removed: "
                f"{duplicates_removed:,}"
            )

            # ------------------------------------------------
            # STEP 6 — Save cleaned data
            # ------------------------------------------------

            df_clean.to_csv(
                output_file,
                mode="w" if first_output else "a",
                header=first_output,
                index=False
            )

            first_output = False

            print(
                f"Total rows written so far: "
                f"{total_output_rows:,}"
            )

            # ------------------------------------------------
            # Optional testing limit
            # ------------------------------------------------

            if (
                max_chunks is not None
                and chunk_number >= max_chunks
            ):
                print(
                    f"\nStopping after "
                    f"{max_chunks} chunk(s) for testing."
                )
                break

    finally:

        connection.close()

    # --------------------------------------------------------
    # FINAL SUMMARY
    # --------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("PROCESSING COMPLETE")
    print("=" * 70)

    print(f"Chunks processed       : {chunk_number:,}")
    print(f"Input rows             : {total_input_rows:,}")
    print(f"Output rows            : {total_output_rows:,}")
    print(
        f"Duplicates removed    : "
        f"{total_duplicates_removed:,}"
    )

    if total_input_rows > 0:

        duplicate_rate = (
            total_duplicates_removed
            / total_input_rows
            * 100
        )

        print(
            f"Duplicate removal rate: "
            f"{duplicate_rate:.4f}%"
        )

    print(f"\nOutput file:")
    print(output_file.resolve())

    print(f"\nDuplicate index:")
    print(db_file.resolve())

    return {
        "chunks_processed": chunk_number,
        "input_rows": total_input_rows,
        "output_rows": total_output_rows,
        "duplicates_removed": total_duplicates_removed,
    }


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    process_dataset()