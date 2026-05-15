import pandas as pd
import yfinance as yf
from sqlalchemy import create_engine

# =====================================
# CONNECT POSTGRESQL
# =====================================

import os

DATABASE_URL = os.getenv("NEON_DB")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

# =====================================
# GET TICKERS FROM METADATA
# =====================================

metadata_df = pd.read_sql(
    """
    SELECT
        ticker,
        date_started
    FROM stock_metadata
    """,
    engine
)

tickers = metadata_df["ticker"].tolist()

# tambah .JK
yf_tickers = [ticker + ".JK" for ticker in tickers]

print(yf_tickers)

# =====================================
# FETCH DATA
# =====================================

all_data = []

for _, row in metadata_df.iterrows():

    ticker = row["ticker"] + ".JK"
    start_date = row["date_started"]

    print(f"Fetching {ticker} from {start_date}...")

    try:

        df = yf.download(
            ticker,
            start=start_date,
            progress=False,
            auto_adjust=False
        )

        if df.empty:
            print(f"No data for {ticker}")
            continue

        df = df.reset_index()

        # flatten multiindex
        df.columns = [
            col[0] if isinstance(col, tuple) else col
            for col in df.columns
        ]

        df["ticker"] = ticker.replace(".JK", "")

        df = df[
            [
                "Date",
                "ticker",
                "Open",
                "High",
                "Low",
                "Close",
                "Volume"
            ]
        ]

        df.columns = [
            "date",
            "ticker",
            "open",
            "high",
            "low",
            "close",
            "volume"
        ]

        all_data.append(df)

        print(f"SUCCESS: {ticker}")

    except Exception as e:
        print(f"ERROR {ticker}: {e}")

# =====================================
# COMBINE ALL DATA
# =====================================

final_df = pd.concat(all_data, ignore_index=True)

print(final_df.head())

# =====================================
# INSERT TO POSTGRESQL
# =====================================

final_df.to_sql(
    "stock_prices",
    engine,
    if_exists="append",
    index=False
)

print("ALL STOCK DATA INSERTED SUCCESSFULLY")
