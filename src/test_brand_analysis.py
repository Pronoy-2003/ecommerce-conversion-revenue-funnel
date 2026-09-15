"""
test_brand_analysis.py

Purpose:
Validates the generated brand-level analysis dataset.

Checks:
- schema
- duplicate brands
- missing values
- negative metrics
- funnel hierarchy
- conversion-rate calculations
- undefined Cart → Purchase cases
- revenue consistency

Why:
Ensures the brand analysis is structurally and mathematically correct
before being used for business analysis.
"""


import pandas as pd

from src.eda_analysis import BRAND_OUTPUT


df = pd.read_csv(BRAND_OUTPUT)

print("\n" + "=" * 70)
print("BRAND ANALYSIS VALIDATION")
print("=" * 70)

# ------------------------------------------------------------
# 1. Shape
# ------------------------------------------------------------

print("\nShape:")
print(df.shape)


# ------------------------------------------------------------
# 2. Required columns
# ------------------------------------------------------------

required_columns = [
    "brand",
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
    col for col in required_columns
    if col not in df.columns
]

print("\nMissing required columns:")
print(missing_columns)


# ------------------------------------------------------------
# 3. Duplicate brands
# ------------------------------------------------------------

duplicate_brands = df["brand"].duplicated().sum()

print("\nDuplicate brands:")
print(duplicate_brands)


# ------------------------------------------------------------
# 4. Missing brand
# ------------------------------------------------------------

missing_brand = df["brand"].isna().sum()

print("\nMissing brand values:")
print(missing_brand)


# ------------------------------------------------------------
# 5. Negative metrics
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# 6. Funnel hierarchy
# ------------------------------------------------------------

cart_greater_than_view = (
    df["cart_users"] > df["view_users"]
).sum()

purchase_greater_than_cart = (
    df["purchase_users"] > df["cart_users"]
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


# ------------------------------------------------------------
# 7. Conversion-rate validation
# ------------------------------------------------------------

expected_view_to_cart = (
    df["cart_users"] / df["view_users"]
)

expected_cart_to_purchase = (
    df["purchase_users"] / df["cart_users"]
)

expected_view_to_purchase = (
    df["purchase_users"] / df["view_users"]
)

# Compare only where denominator > 0
mask_view = df["view_users"] > 0
mask_cart = df["cart_users"] > 0

view_to_cart_errors = (
    (
        df.loc[mask_view, "view_to_cart_rate"]
        -
        expected_view_to_cart[mask_view]
    ).abs() > 1e-10
).sum()

cart_to_purchase_errors = (
    (
        df.loc[mask_cart, "cart_to_purchase_rate"]
        -
        expected_cart_to_purchase[mask_cart]
    ).abs() > 1e-10
).sum()

view_to_purchase_errors = (
    (
        df.loc[mask_view, "view_to_purchase_rate"]
        -
        expected_view_to_purchase[mask_view]
    ).abs() > 1e-10
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


# ------------------------------------------------------------
# 8. Expected undefined Cart → Purchase
# ------------------------------------------------------------

undefined_cart_rate = (
    df["cart_users"] == 0
).sum()

actual_nan_cart_rate = (
    df["cart_to_purchase_rate"].isna()
).sum()

print("\nCart → Purchase undefined cases:")

print(
    "Brands with zero carts:",
    undefined_cart_rate
)

print(
    "NaN Cart → Purchase rates:",
    actual_nan_cart_rate
)


# ------------------------------------------------------------
# 9. Revenue sanity
# ------------------------------------------------------------

zero_revenue_purchase_brands = (
    (
        (df["purchase_events"] > 0)
        &
        (df["revenue"] == 0)
    )
).sum()

print("\nRevenue sanity:")
print(
    "Brands with purchases but zero revenue:",
    zero_revenue_purchase_brands
)


# ------------------------------------------------------------
# 10. Top brands
# ------------------------------------------------------------

print("\nTop 10 brands by revenue:")

print(
    df[
        [
            "brand",
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
    .sort_values(
        "revenue",
        ascending=False
    )
    .head(10)
    .to_string(index=False)
)


# ------------------------------------------------------------
# FINAL
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("VALIDATION COMPLETE")
print("=" * 70)