import pandas as pd
from sqlalchemy import create_engine

# =====================================
# READ EXCEL
# =====================================

file_path = r"E:\06 cc26\CAPSTONE\IDX80 Metadata.xlsx"

df = pd.read_excel(
    file_path,
    sheet_name="Summary"
)

# =====================================
# RENAME COLUMNS
# =====================================

df.columns = [
    "no",
    "ticker",
    "date_started",
    "company_name",
    "sector",
    "industry",
    "market_cap",
    "beta",
    "country",
    "currency",
    "exchange"
]

# =====================================
# DROP UNUSED COLUMN
# =====================================

df = df.drop(columns=["no"])

# =====================================
# CLEAN DATA
# =====================================

df["ticker"] = df["ticker"].astype(str)

df["date_started"] = pd.to_datetime(
    df["date_started"],
    errors="coerce"
)

df["market_cap"] = pd.to_numeric(
    df["market_cap"],
    errors="coerce"
)

df["beta"] = pd.to_numeric(
    df["beta"],
    errors="coerce"
)

df["yf_ticker"] = df["ticker"] + ".JK"

# =====================================
# CONNECT POSTGRESQL
# =====================================

DATABASE_URL = os.getenv("LOCAL_DB")

engine = create_engine(DATABASE_URL)

# =====================================
# INSERT TO POSTGRESQL
# =====================================

df.to_sql(
    "stock_metadata",
    engine,
    if_exists="append",
    index=False
)

print("Metadata inserted successfully!")