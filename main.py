from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy import text
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

import os
import pandas as pd
import yfinance as yf
import numpy as np

load_dotenv()

# =====================================
# FASTAPI
# =====================================

app = FastAPI()

# =====================================
# DATABASE CONNECTION
# =====================================

DATABASE_URL = os.getenv("NEON_DB")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

# =====================================
# UPDATE FUNCTION
# =====================================

def update_stock_data():

    print("RUNNING DAILY UPDATE...")

    metadata_df = pd.read_sql(
        "SELECT ticker FROM stock_metadata",
        engine
    )

    for ticker in metadata_df["ticker"].tolist():

        yf_ticker = ticker + ".JK"

        try:

            # =====================================
            # GET LAST DATE (FIX NULL BUG)
            # =====================================

            query = f"""
            SELECT MAX(date)
            FROM stock_prices
            WHERE ticker = '{ticker}'
            """

            last_date = pd.read_sql(query, engine).iloc[0, 0]

            if last_date is None:
                last_date = "2020-01-01"

            # =====================================
            # FETCH NEW DATA
            # =====================================

            df = yf.download(
                yf_ticker,
                start=last_date,
                progress=False,
                auto_adjust=False
            )

            if df.empty:
                continue

            df = df.reset_index()

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            df["ticker"] = ticker

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

            # =====================================
            # REMOVE DUPLICATES SAFELY
            # =====================================

            existing_dates = pd.read_sql(
                f"""
                SELECT date
                FROM stock_prices
                WHERE ticker = '{ticker}'
                """,
                engine
            )

            if not existing_dates.empty:
                existing_dates["date"] = pd.to_datetime(existing_dates["date"])
                df = df[~df["date"].isin(existing_dates["date"])]

            # =====================================
            # INSERT STOCK PRICES
            # =====================================

            if not df.empty:
                df.to_sql(
                    "stock_prices",
                    engine,
                    if_exists="append",
                    index=False
                )

            # =====================================
            # FEATURE ENGINEERING (UNCHANGED LOGIC)
            # =====================================

            feature_df = df.copy()

            if not feature_df.empty:
                feature_df["daily_return"] = feature_df["close"].pct_change()
                feature_df["log_return"] = np.log(
                    feature_df["close"] / feature_df["close"].shift(1)
                )
                feature_df["var_95"] = (
                    feature_df["daily_return"]
                    .rolling(30)
                    .quantile(0.05)
                )

                feature_df = feature_df[[
                    "date",
                    "ticker",
                    "daily_return",
                    "log_return",
                    "var_95"
                ]].dropna()

                feature_df.to_sql(
                    "stock_features",
                    engine,
                    if_exists="append",
                    index=False
                )

            print(f"UPDATED: {ticker}")

        except Exception as e:
            print(f"ERROR {ticker}: {e}")

# =====================================
# SCHEDULER
# =====================================

scheduler = BackgroundScheduler()

scheduler.add_job(
    update_stock_data,
    "cron",
    hour=17,
    minute=0
)

scheduler.start()

# =====================================
# API ENDPOINTS
# =====================================

@app.get("/")
def root():
    return {"message": "Stockation API running"}

@app.get("/stocks/{ticker}")
def get_stock_data(ticker: str):

    query = text("""
        SELECT *
        FROM stock_prices
        WHERE ticker = :ticker
        ORDER BY date
    """)

    df = pd.read_sql(query, engine, params={"ticker": ticker})

    return df.to_dict(orient="records")

@app.get("/features/{ticker}")
def get_features(ticker: str):

    query = text("""
        SELECT *
        FROM stock_features
        WHERE ticker = :ticker
        ORDER BY date
    """)

    df = pd.read_sql_query(query, engine, params={"ticker": ticker})

    # safety: handle empty data
    if df.empty:
        return {"message": "No features found", "data": []}

    # safety: convert NaN -> None biar JSON aman
    df = df.where(pd.notnull(df), None)

    return df.to_dict(orient="records")

@app.get("/metadata")
def get_metadata():

    query = """
    SELECT *
    FROM stock_metadata
    """

    df = pd.read_sql(query, engine)
    df = df.replace({None: None})
    df = df.fillna("")

    return df.to_dict(orient="records")

@app.get("/update")
def manual_update():

    update_stock_data()

    return {"message": "Update completed"}
