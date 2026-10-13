"""
analyze.py — reads sales.csv and writes summary JSON files to output/

Run with:
    python analyze.py
"""

import json
import os
import pathlib
import time

from google import genai
import pandas as pd
from dotenv import load_dotenv

load_dotenv()


# ── File paths ────────────────────────────────────────────────────────────────
DATA_FILE  = pathlib.Path("data/sales.csv")
OUTPUT_DIR = pathlib.Path("output")


def load_data() -> pd.DataFrame:
    """Read the CSV file and return it as a DataFrame.

    parse_dates=["date"] tells pandas to convert the date column from a
    plain string into a proper datetime object, which unlocks .dt operations
    later (e.g. extracting the month).
    """
    df = pd.read_csv(DATA_FILE, parse_dates=["date"])
    print(f"Loaded {len(df)} rows from {DATA_FILE}")
    return df


def compute_summary(df: pd.DataFrame) -> dict:
    """Compute overall totals and identify the top product and region.

    Key operations:
    - .sum()    — adds up all values in a column
    - .groupby() — splits the data into groups (one per product or region)
    - .idxmax() — returns the *label* (name) of the group with the highest value
    """
    total_revenue = round(df["revenue"].sum(), 2)
    total_units   = int(df["units_sold"].sum())

    # Group all rows by product, sum their revenue, then find the top name
    top_product = df.groupby("product")["revenue"].sum().idxmax()

    # Same pattern for region
    top_region  = df.groupby("region")["revenue"].sum().idxmax()

    return {
        "total_revenue": total_revenue,
        "total_units":   total_units,
        "top_product":   top_product,
        "top_region":    top_region,
    }


def compute_monthly_revenue(df: pd.DataFrame) -> list[dict]:
    """Return total revenue per calendar month, sorted oldest to newest.

    Key operations:
    - .dt.to_period("M") — converts a full date like 2024-03-15 to just "2024-03"
    - .astype(str)       — converts the Period object to a plain string for JSON
    - .reset_index()     — after groupby, the group labels become an index column;
                           reset_index() turns them back into a regular column
    - to_dict("records") — converts the DataFrame to a list of dicts:
                           [{"month": "2024-01", "revenue": 1234.56}, ...]
                           This format is exactly what Chart.js expects.
    """
    df = df.copy()  # avoid modifying the original DataFrame
    df["month"] = df["date"].dt.to_period("M").astype(str)

    monthly = (
        df.groupby("month")["revenue"]
        .sum()
        .round(2)
        .reset_index()
        .sort_values("month")  # sort chronologically (strings sort correctly here)
    )

    return monthly.to_dict(orient="records")


def compute_revenue_by_product(df: pd.DataFrame) -> list[dict]:
    """Return total revenue per product, sorted highest to lowest."""
    by_product = (
        df.groupby("product")["revenue"]
        .sum()
        .round(2)
        .reset_index()
        .sort_values("revenue", ascending=False)
    )
    return by_product.to_dict(orient="records")


def compute_revenue_by_region(df: pd.DataFrame) -> list[dict]:
    """Return total revenue per region, sorted highest to lowest."""
    by_region = (
        df.groupby("region")["revenue"]
        .sum()
        .round(2)
        .reset_index()
        .sort_values("revenue", ascending=False)
    )
    return by_region.to_dict(orient="records")


def compute_insights(df: pd.DataFrame) -> dict:
    """Send a summary of the sales data to Gemini and return AI-written insights.

    We build a compact text summary of the data and ask Gemini to identify
    notable trends and patterns within it. The result is a plain string.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "Missing GEMINI_API_KEY in .env — add it to enable AI insights."
        )

    # Build a compact summary to send to Gemini instead of the full raw CSV
    monthly = compute_monthly_revenue(df)
    by_product = compute_revenue_by_product(df)
    by_region = compute_revenue_by_region(df)

    data_summary = f"""
Monthly revenue (Jan–Oct 2024):
{json.dumps(monthly, indent=2)}

Revenue by product:
{json.dumps(by_product, indent=2)}

Revenue by region:
{json.dumps(by_region, indent=2)}
""".strip()

    prompt = f"""You are a business analyst. Based on the sales data below, write
2-3 sentences of plain-English insight. Focus on notable trends, month-over-month
changes, or unusual patterns visible within this dataset. Be specific and concise.

{data_summary}"""

    client = genai.Client(api_key=api_key)

    for attempt in range(5):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=prompt,
            )
            return {"insights": response.text.strip()}
        except Exception as e:
            if "429" in str(e) and attempt < 4:
                wait = 10 * (attempt + 1)
                print(f"Rate limited — waiting {wait}s before retry {attempt + 1}/4…")
                time.sleep(wait)
            else:
                raise


def write_json(data: dict | list, filename: str) -> None:
    """Write a Python object to output/<filename> as formatted JSON.

    indent=2 makes the file human-readable (pretty-printed).
    """
    path = OUTPUT_DIR / filename
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Wrote {path}")


def main():
    # Create the output directory if it doesn't exist yet
    OUTPUT_DIR.mkdir(exist_ok=True)

    df = load_data()

    write_json(compute_summary(df),             "summary.json")
    write_json(compute_monthly_revenue(df),     "monthly_revenue.json")
    write_json(compute_revenue_by_product(df),  "revenue_by_product.json")
    write_json(compute_revenue_by_region(df),   "revenue_by_region.json")
    write_json(compute_insights(df),            "insights.json")

    print("\nDone. Check the output/ folder.")


if __name__ == "__main__":
    main()
