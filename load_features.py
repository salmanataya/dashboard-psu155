import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

load_dotenv()

# =====================================
# CONNECT POSTGRESQL
# =====================================

DATABASE_URL = os.getenv("NEON_DB")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

# =====================================
# LOAD STOCK PRICES
# =====================================

query = """
SELECT
    date,
    ticker,
    close
FROM stock_prices
ORDER BY ticker, date
"""

df = pd.read_sql(query, engine)

print(df.head())

# =====================================
# SORT DATA
# =====================================

df = df.sort_values(by=["ticker", "date"])

# =====================================
# DAILY RETURN
# =====================================

df["daily_return"] = (
    df.groupby("ticker")["close"].pct_change()
)

# =====================================
# LOG RETURN
# =====================================

df["log_return"] = (
    df.groupby("ticker")["close"]
    .transform(lambda x: np.log(x / x.shift(1)))
)

# =====================================
# VaR 95
# =====================================

df["var_95"] = (
    df.groupby("ticker")["daily_return"]
    .transform(lambda x: x.rolling(30).quantile(0.05))
)

# =====================================
# CLEAN NaN SAFETY (FIX BUG)
# =====================================

features_df = df[[
    "date",
    "ticker",
    "daily_return",
    "log_return",
    "var_95"
]].dropna()

print(features_df.head())

# =====================================
# INSERT TO POSTGRESQL
# =====================================

features_df.to_sql(
    "stock_features",
    engine,
    if_exists="append",
    index=False
)

print("FEATURES INSERTED SUCCESSFULLY")
