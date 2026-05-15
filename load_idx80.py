import pandas as pd
from sqlalchemy import create_engine

# =====================================
# DATABASE
# =====================================

import os

DATABASE_URL = os.getenv("LOCAL_DB")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

# =====================================
# LOAD STOCK PRICES
# =====================================

prices_query = """
SELECT
    date,
    ticker,
    close
FROM stock_prices
"""

prices_df = pd.read_sql(
    prices_query,
    engine
)

# =====================================
# LOAD METADATA
# =====================================

metadata_query = """
SELECT
    ticker,
    market_cap
FROM stock_metadata
"""

metadata_df = pd.read_sql(
    metadata_query,
    engine
)

# =====================================
# MERGE MARKET CAP
# =====================================

combined_df = prices_df.merge(
    metadata_df,
    on="ticker",
    how="left"
)

# =====================================
# WEIGHTED PRICE
# =====================================

combined_df["weighted_price"] = (
    combined_df["close"]
    *
    combined_df["market_cap"]
)

# =====================================
# DAILY INDEX VALUE
# =====================================

daily_index = (
    combined_df
    .groupby("date")["weighted_price"]
    .sum()
    .reset_index()
)

# =====================================
# NORMALIZE INDEX
# =====================================

base_value = 100

first_value = daily_index[
    "weighted_price"
].iloc[0]

daily_index["idx80_value"] = (
    daily_index["weighted_price"]
    / first_value
) * base_value

# =====================================
# KEEP FINAL COLUMNS
# =====================================

daily_index = daily_index[
    [
        "date",
        "idx80_value"
    ]
]

print(daily_index.head())

# =====================================
# SAVE TO POSTGRESQL
# =====================================

daily_index.to_sql(
    "stock_idx80",
    engine,
    if_exists="replace",
    index=False
)

print("IDX80 OVERVIEW GENERATED")