import pandas as pd
import yfinance as yf
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
# GET TICKERS FROM METADATA
# =====================================

metadata_df = pd.read_sql(
    """
    SELECT ticker, date_started
    FROM stock_metadata
    """,
    engine
)

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

        # FIX MULTIINDEX SAFETY
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df["ticker"] = row["ticker"]

        df = df[[
            "Date",
            "ticker",
            "Open",
            "High",
            "Low",
            "Close",
            "Volume"
        ]]

        df.columns = [
            "date",
            "ticker",
            "open",
            "high",
            "low",
            "close",
            "volume"
        ]

        df["date"] = pd.to_datetime(df["date"])

        all_data.append(df)

        print(f"SUCCESS: {ticker}")

    except Exception as e:
        print(f"ERROR {ticker}: {e}")

# =====================================
# SAFETY CHECK (FIX CRASH)
# =====================================

if len(all_data) == 0:
    print("No data fetched. Exit.")
    exit()

# =====================================
# COMBINE ALL DATA
# =====================================

final_df = pd.concat(all_data, ignore_index=True)

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
