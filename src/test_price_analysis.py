"""
test_price_analysis.py

Purpose:
Validates the generated price-band analysis dataset.

Checks:
- expected price bands
- required columns
- duplicate bands
- missing bands
- negative metrics
- funnel hierarchy
- conversion-rate calculations
- zero-cart cases
- revenue consistency
- zero-price band behavior

Why:
Ensures that price segmentation and its funnel metrics are
correct before downstream analysis.
"""


import pandas as pd

from src.eda_analysis import PRICE_OUTPUT


df = pd.read_csv(PRICE_OUTPUT)


print("\n" + "=" * 70)
print("PRICE BAND ANALYSIS VALIDATION")
print("=" * 70)


# ============================================================
# 1. SHAPE
# ============================================================

print("\nShape:")
print(df.shape)


# ============================================================
# 2. REQUIRED COLUMNS
# ============================================================

required_columns = [
    "price_band",
    "view_users",
    "cart_users",
    "purchase_users",
    "purchase_events",
    "revenue",
    "view_to_cart_rate",
    "cart_to_purchase_rate",
    "view_to_purchase_rate"
]

missing_columns = [
    column
    for column in required_columns
    if column not in df.columns
]

print("\nMissing required columns:")
print(missing_columns)


# ============================================================
# 3. EXPECTED PRICE BANDS
# ============================================================

expected_bands = [
    "$0",
    "$0–$50",
    "$50–$100",
    "$100–$250",
    "$250–$500",
    "$500–$1,000",
    "$1,000–$2,000",
    "$2,000+"
]

actual_bands = df["price_band"].tolist()

missing_bands = [
    band
    for band in expected_bands
    if band not in actual_bands
]

unexpected_bands = [
    band
    for band in actual_bands
    if band not in expected_bands
]

print("\nMissing expected price bands:")
print(missing_bands)

print("\nUnexpected price bands:")
print(unexpected_bands)


# ============================================================
# 4. DUPLICATE PRICE BANDS
# ============================================================

duplicate_bands = (
    df["price_band"]
    .duplicated()
    .sum()
)

print("\nDuplicate price bands:")
print(duplicate_bands)


# ============================================================
# 5. MISSING PRICE BAND
# ============================================================

missing_price_band = (
    df["price_band"]
    .isna()
    .sum()
)

print("\nMissing price-band values:")
print(missing_price_band)


# ============================================================
# 6. NEGATIVE METRICS
# ============================================================

metric_columns = [
    "view_users",
    "cart_users",
    "purchase_users",
    "purchase_events",
    "revenue"
]

negative_metrics = (
    df[metric_columns] < 0
).sum()

print("\nNegative metric counts:")
print(negative_metrics)


# ============================================================
# 7. FUNNEL HIERARCHY
# ============================================================

cart_greater_than_view = (
    df["cart_users"]
    >
    df["view_users"]
).sum()

purchase_greater_than_cart = (
    df["purchase_users"]
    >
    df["cart_users"]
).sum()

purchase_greater_than_view = (
    df["purchase_users"]
    >
    df["view_users"]
).sum()

print("\nFunnel hierarchy violations:")

print(
    "Cart users > View users:",
    cart_greater_than_view
)

print(
    "Purchase users > Cart users:",
    purchase_greater_than_cart
)

print(
    "Purchase users > View users:",
    purchase_greater_than_view
)


# ============================================================
# 8. CONVERSION RATE VALIDATION
# ============================================================

expected_view_to_cart = (
    df["cart_users"]
    /
    df["view_users"]
)

expected_cart_to_purchase = (
    df["purchase_users"]
    /
    df["cart_users"]
)

expected_view_to_purchase = (
    df["purchase_users"]
    /
    df["view_users"]
)


# ------------------------------------------------------------
# View → Cart
# ------------------------------------------------------------

mask_view = (
    df["view_users"] > 0
)

view_to_cart_errors = (
    (
        df.loc[
            mask_view,
            "view_to_cart_rate"
        ]
        -
        expected_view_to_cart[
            mask_view
        ]
    )
    .abs()
    >
    1e-10
).sum()


# ------------------------------------------------------------
# Cart → Purchase
# ------------------------------------------------------------

mask_cart = (
    df["cart_users"] > 0
)

cart_to_purchase_errors = (
    (
        df.loc[
            mask_cart,
            "cart_to_purchase_rate"
        ]
        -
        expected_cart_to_purchase[
            mask_cart
        ]
    )
    .abs()
    >
    1e-10
).sum()


# ------------------------------------------------------------
# View → Purchase
# ------------------------------------------------------------

view_to_purchase_errors = (
    (
        df.loc[
            mask_view,
            "view_to_purchase_rate"
        ]
        -
        expected_view_to_purchase[
            mask_view
        ]
    )
    .abs()
    >
    1e-10
).sum()


print("\nConversion-rate mismatches:")

print(
    "View → Cart:",
    view_to_cart_errors
)

print(
    "Cart → Purchase:",
    cart_to_purchase_errors
)

print(
    "View → Purchase:",
    view_to_purchase_errors
)


# ============================================================
# 9. ZERO-CART VALIDATION
# ============================================================

zero_cart_bands = (
    df["cart_users"] == 0
).sum()

nan_cart_purchase_rates = (
    df["cart_to_purchase_rate"]
    .isna()
).sum()

print("\nCart → Purchase undefined cases:")

print(
    "Price bands with zero carts:",
    zero_cart_bands
)

print(
    "NaN Cart → Purchase rates:",
    nan_cart_purchase_rates
)


# ============================================================
# 10. REVENUE SANITY
# ============================================================

purchase_without_revenue = (
    (
        (df["purchase_events"] > 0)
        &
        (df["revenue"] == 0)
    )
).sum()

print("\nRevenue sanity:")

print(
    "Bands with purchases but zero revenue:",
    purchase_without_revenue
)


# ============================================================
# 11. ZERO-PRICE BAND CHECK
# ============================================================

zero_price_rows = df[
    df["price_band"] == "$0"
]

print("\nZero-price band:")

if len(zero_price_rows) > 0:

    print(
        zero_price_rows.to_string(
            index=False
        )
    )

else:

    print(
        "$0 band not present in this sample."
    )


# ============================================================
# 12. PRICE BAND SUMMARY
# ============================================================

print("\nPrice-band summary:")

print(
    df[
        [
            "price_band",
            "view_users",
            "cart_users",
            "purchase_users",
            "purchase_events",
            "revenue",
            "view_to_cart_rate",
            "cart_to_purchase_rate",
            "view_to_purchase_rate"
        ]
    ]
    .to_string(index=False)
)


# ============================================================
# FINAL
# ============================================================

print("\n" + "=" * 70)
print("VALIDATION COMPLETE")
print("=" * 70)