"""
data_cleaning.py

Purpose:
Contains reusable functions for standardizing data types,
handling missing values, and creating datetime features.

Why:
Centralizing cleaning logic makes the production pipeline
consistent, reusable, and easier to maintain.
"""


import pandas as pd


def standardize_dtypes(df):
    """
    Standardize data types for the event dataset.
    """

    df["event_time"] = pd.to_datetime(
        df["event_time"],
        utc=True
    )

    df["event_type"] = df["event_type"].astype("category")

    df["product_id"] = df["product_id"].astype("int64")

    df["category_id"] = df["category_id"].astype("int64")

    df["price"] = df["price"].astype("float64")

    df["user_id"] = df["user_id"].astype("int64")

    return df


def handle_missing_values(df):
    """
    Handle missing values in descriptive categorical columns.
    """

    df["category_code"] = df["category_code"].fillna("Unknown")

    df["brand"] = df["brand"].fillna("Unknown")

    df["user_session"] = df["user_session"].fillna("Unknown")

    return df


def add_datetime_features(df):
    """
    Add date and time-based analytical columns.
    """

    df["event_date"] = df["event_time"].dt.date

    df["event_hour"] = df["event_time"].dt.hour

    df["day_of_week"] = df["event_time"].dt.day_name()

    df["day_of_month"] = df["event_time"].dt.day

    return df