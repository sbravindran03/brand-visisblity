"""Data ingestion, cleaning, feature engineering, and SQLite helpers."""

from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "brand_visibility.db"
SAMPLE_PATH = DATA_DIR / "raw" / "brand_dirty_dataset.csv"
OUTPUT_PATH = DATA_DIR / "processed" / "cleaned_products.csv"

COLUMN_ALIASES = {
    "keyword": "keyword", "search_term": "keyword", "query": "keyword",
    "title": "title", "product_title": "title", "name": "title",
    "price": "price", "extracted_price": "price", "selling_price": "price",
    "raw_price": "raw_price", "original_price": "raw_price", "list_price": "raw_price",
    "rating": "rating", "stars": "rating", "reviews": "reviews", "review_count": "reviews",
    "platform": "platform", "source": "platform", "store": "platform",
    "position": "position", "rank": "position", "ranking": "position",
    "discount": "discount", "product_link": "product_link", "link": "product_link",
    "product_id": "product_id", "is_demo": "is_demo",
    "delivery": "delivery", "delivery_time": "delivery",
}


def _number(value: object) -> float | None:
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"-?\d[\d,]*(?:\.\d+)?", str(value).replace("−", "-"))
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", ""))
    except ValueError:
        return None


def _slug(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


def _brand_from_title(title: object) -> str:
    text = str(title).strip()
    known = ["Apple", "Samsung", "Sony", "Nike", "Adidas", "Dell", "HP", "LG", "Lenovo", "Logitech", "Bose", "Canon", "Philips", "Google", "OnePlus", "Xiaomi", "Puma", "Asus", "Acer", "JBL", "Anker", "Boat"]
    for brand in known:
        if re.search(rf"\b{re.escape(brand)}\b", text, flags=re.I):
            return "LG" if brand.lower() == "lg" else brand
    first = re.match(r"[A-Za-z0-9]+", text)
    return first.group(0).title() if first else "Unknown"


def clean_products(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize source columns and derive analysis-ready features."""
    if frame.empty:
        return pd.DataFrame(columns=["keyword", "title", "price", "raw_price", "rating", "reviews", "platform", "position", "brand", "visibility_score", "price_range", "discount_pct", "is_demo"])
    df = frame.copy()
    df.columns = [_slug(c).replace(" ", "_") for c in df.columns]
    df = df.rename(columns={c: COLUMN_ALIASES.get(c, c) for c in df.columns})
    for col in ["keyword", "title", "platform", "delivery"]:
        if col not in df:
            df[col] = "Unknown" if col != "delivery" else "Not provided"
        df[col] = df[col].fillna("Unknown" if col != "delivery" else "Not provided").astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
    df["keyword"] = df["keyword"].str.title()
    platform_aliases = {"amazon.com": "Amazon", "amazon.in": "Amazon", "flipkart.com": "Flipkart", "croma.com": "Croma", "reliance digital": "Reliance Digital", "reliancedigital.com": "Reliance Digital", "walmart.com": "Walmart"}
    df["platform"] = df["platform"].str.casefold().map(lambda value: platform_aliases.get(value, value.title()))
    df["delivery"] = df["delivery"].replace({"": "Not provided", "Nan": "Not provided", "None": "Not provided"})
    df["title"] = df["title"].str.replace(r"[!]{2,}", "", regex=True).str.replace(r"\s+", " ", regex=True).str.strip(" -|")
    for col in ["price", "raw_price", "rating", "reviews", "position", "discount"]:
        if col not in df:
            df[col] = None
        df[col] = pd.to_numeric(df[col].map(_number), errors="coerce")
    df["price"] = df["price"].where(df["price"].gt(0))
    df["raw_price"] = df["raw_price"].where(df["raw_price"].gt(0))
    df["rating"] = df["rating"].where(df["rating"].between(0, 5))
    df["reviews"] = df["reviews"].where(df["reviews"].ge(0)).round().astype("Int64")
    df["position"] = df["position"].where(df["position"].gt(0))
    if "is_demo" not in df:
        df["is_demo"] = False
    df["is_demo"] = df["is_demo"].fillna(False).astype(str).str.lower().isin(["true", "1", "yes"])
    if "product_link" not in df:
        df["product_link"] = ""
    if "product_id" not in df:
        df["product_id"] = ""
    df["product_link"] = df["product_link"].fillna("").astype(str)
    df["product_id"] = df["product_id"].fillna("").astype(str)
    df["brand"] = df["title"].map(_brand_from_title)
    derived_discount = ((df["raw_price"] - df["price"]) / df["raw_price"] * 100).where(df["raw_price"].gt(df["price"]))
    supplied_discount = df["discount"].where(df["discount"].between(0, 100))
    df["discount_pct"] = derived_discount.fillna(supplied_discount).clip(0, 100).round(1)
    df["price_range"] = pd.cut(df["price"], [-float("inf"), 1000, 5000, 20000, 50000, float("inf")], labels=["Under ₹1k", "₹1k–₹5k", "₹5k–₹20k", "₹20k–₹50k", "₹50k+"]).astype("string").fillna("Unknown")
    df["visibility_score"] = (100 / df["position"].clip(lower=1)).round(2)
    valid_prices = df["price"].dropna()
    if not valid_prices.empty:
        lower, upper = valid_prices.quantile([0.25, 0.75])
        cutoff = upper + 1.5 * (upper - lower)
        df["price_outlier"] = df["price"].gt(cutoff)
    else:
        df["price_outlier"] = False
    df = df.sort_values("position", na_position="last", kind="stable").drop_duplicates(subset=["keyword", "title", "platform"], keep="first").reset_index(drop=True)
    return df


def load_source(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path)


def fetch_serpapi(keywords: Iterable[str], api_key: str | None = None, country: str = "in") -> pd.DataFrame:
    """Fetch Google Shopping result rows from SerpApi. Requires a user API key."""
    load_dotenv(ROOT / ".env")
    # An explicitly supplied blank value means "no key". Only use the
    # environment fallback when the caller omitted the argument entirely.
    key = os.getenv("SERPAPI_API_KEY") if api_key is None else api_key.strip()
    if not key:
        raise ValueError("Add SERPAPI_API_KEY to .env or Streamlit secrets to enable live extraction.")
    rows: list[dict] = []
    for keyword in keywords:
        try:
            response = requests.get("https://serpapi.com/search", params={"engine": "google_shopping", "q": keyword, "api_key": key, "gl": country}, timeout=30)
        except requests.RequestException as exc:
            raise RuntimeError("Could not reach SerpApi. Check the network connection and try again.") from exc
        if response.status_code in (401, 403):
            raise RuntimeError("SerpApi rejected the request. Check that the API key is valid and active.")
        if response.status_code >= 400:
            raise RuntimeError(f"SerpApi returned HTTP {response.status_code}. Check the query and try again.")
        payload = response.json()
        for item in payload.get("shopping_results", []):
            rows.append({"keyword": keyword, "title": item.get("title"), "price": item.get("extracted_price"), "raw_price": item.get("extracted_old_price") or item.get("old_price"), "rating": item.get("rating"), "reviews": item.get("reviews"), "platform": item.get("source"), "position": item.get("position"), "product_link": item.get("product_link") or item.get("link"), "product_id": item.get("product_id"), "delivery": item.get("delivery"), "is_demo": False})
    return pd.DataFrame(rows)


def save_products(frame: pd.DataFrame, db_path: str | Path = DB_PATH, csv_path: str | Path = OUTPUT_PATH) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(csv_path, index=False)
    with sqlite3.connect(db_path) as conn:
        frame.to_sql("products", conn, if_exists="replace", index=False)


def load_products(db_path: str | Path = DB_PATH) -> pd.DataFrame:
    if Path(db_path).exists():
        with sqlite3.connect(db_path) as conn:
            try:
                return pd.read_sql_query("SELECT * FROM products", conn)
            except Exception:
                pass
    if OUTPUT_PATH.exists():
        return pd.read_csv(OUTPUT_PATH)
    return clean_products(load_source(SAMPLE_PATH))


def query_products(filters: dict, db_path: str | Path = DB_PATH) -> pd.DataFrame:
    """Apply shared dashboard filters in SQLite with bound parameters."""
    clauses: list[str] = []
    params: list[object] = []
    for field in ("keyword", "platform", "brand", "price_range"):
        value = filters.get(field)
        if value and value != "All":
            clauses.append(f"\"{field}\" = ?")
            params.append(value)
    low, high = filters.get("rating_range", (0.0, 5.0))
    if float(low) > 0 or float(high) < 5:
        clauses.append("rating >= ? AND rating <= ?")
        params.extend([float(low), float(high)])
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql_query("SELECT * FROM products" + where, conn, params=params)


def initialize() -> pd.DataFrame:
    if not DB_PATH.exists():
        products = clean_products(load_source(SAMPLE_PATH))
        save_products(products)
        return products
    return load_products()
