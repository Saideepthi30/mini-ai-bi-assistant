from pathlib import Path
import sqlite3
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "sales_data.csv"
DB_PATH = ROOT / "sales.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sales_transactions (
    transaction_id TEXT PRIMARY KEY,
    order_date TEXT NOT NULL,
    month TEXT NOT NULL,
    product TEXT NOT NULL,
    category TEXT,
    region TEXT,
    sales_channel TEXT,
    quantity REAL NOT NULL,
    unit_price REAL NOT NULL,
    discount_amount REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    revenue REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sales_month ON sales_transactions(month);
CREATE INDEX IF NOT EXISTS idx_sales_product ON sales_transactions(product);
CREATE INDEX IF NOT EXISTS idx_sales_region ON sales_transactions(region);
"""

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def initialise_database():
    """Create the table and import valid, completed transactions from CSV."""
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found at {CSV_PATH}. Put sales_data.csv in the data/ folder."
        )

    df = pd.read_csv(CSV_PATH)
    expected = [
        "Transaction_Id", "Order_date", "Product", "Category", "Region",
        "Sales_channel", "Quantity", "Unit_price", "Discount_amount", "Status"
    ]
    missing_columns = [c for c in expected if c not in df.columns]
    if missing_columns:
        raise ValueError(f"CSV is missing required columns: {', '.join(missing_columns)}")

    original_rows = len(df)
    df = df[expected].copy()
    df["Order_date"] = pd.to_datetime(df["Order_date"], dayfirst=True, errors="coerce")
    for col in ["Quantity", "Unit_price", "Discount_amount"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Trim text fields and normalize status.
    for col in ["Transaction_Id", "Product", "Category", "Region", "Sales_channel", "Status"]:
        df[col] = df[col].astype("string").str.strip()
    df["Status"] = df["Status"].str.title()
    df["Discount_amount"] = df["Discount_amount"].fillna(0)

    # Missing date/product/ID, invalid numeric values, nonpositive quantity/price,
    # duplicate transaction IDs, and non-completed transactions are not revenue rows.
    valid = (
        df["Transaction_Id"].notna() & df["Transaction_Id"].ne("") &
        df["Product"].notna() & df["Product"].ne("") &
        df["Order_date"].notna() &
        df["Quantity"].notna() & (df["Quantity"] > 0) &
        df["Unit_price"].notna() & (df["Unit_price"] > 0) &
        df["Discount_amount"].ge(0) &
        df["Status"].eq("Completed")
    )
    cleaned = df.loc[valid].copy()
    cleaned = cleaned.drop_duplicates(subset=["Transaction_Id"], keep="first")
    cleaned["revenue"] = (
        cleaned["Quantity"] * cleaned["Unit_price"] - cleaned["Discount_amount"]
    ).clip(lower=0)
    cleaned["month"] = cleaned["Order_date"].dt.strftime("%Y-%m")
    cleaned["order_date"] = cleaned["Order_date"].dt.strftime("%Y-%m-%d")

    with get_connection() as conn:
        conn.executescript(SCHEMA)
        conn.execute("DELETE FROM sales_transactions")
        rows = [
            (
                r.Transaction_Id, r.order_date, r.month, r.Product, r.Category,
                r.Region, r.Sales_channel, float(r.Quantity), float(r.Unit_price),
                float(r.Discount_amount), r.Status, float(r.revenue)
            )
            for r in cleaned.itertuples(index=False)
        ]
        conn.executemany("""
            INSERT INTO sales_transactions (
                transaction_id, order_date, month, product, category, region,
                sales_channel, quantity, unit_price, discount_amount, status, revenue
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)

    return {
        "source_rows": int(original_rows),
        "loaded_rows": int(len(cleaned)),
        "excluded_rows": int(original_rows - len(cleaned)),
        "database": str(DB_PATH.name),
        "revenue_rule": "quantity × unit_price − discount_amount; Completed rows only"
    }
