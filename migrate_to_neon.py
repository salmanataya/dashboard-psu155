import pandas as pd
import os
from sqlalchemy import create_engine

# =====================================
# LOCAL POSTGRES
# =====================================

LOCAL_DB = os.getenv("LOCAL_DB")

# =====================================
# NEON POSTGRES
# =====================================

NEON_DB = os.getenv("NEON_DB")

# =====================================
# CREATE ENGINES
# =====================================

local_engine = create_engine(LOCAL_DB)

neon_engine = create_engine(NEON_DB)

# =====================================
# TABLES TO MIGRATE
# =====================================

tables = [
    "stock_metadata",
    "stock_prices",
    "stock_features",
    "stock_idx80"
]

# =====================================
# MIGRATION
# =====================================

for table in tables:

    print(f"Migrating {table}...")

    df = pd.read_sql(
        f"SELECT * FROM {table}",
        local_engine
    )

    print(df.head())

    df.to_sql(
        table,
        neon_engine,
        if_exists="replace",
        index=False
    )

    print(f"SUCCESS: {table}")

print("ALL TABLES MIGRATED")