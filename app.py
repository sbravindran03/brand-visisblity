from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from src.pipeline import DB_PATH, clean_products, fetch_serpapi, initialize, load_products, query_products, save_products

load_dotenv(ROOT / ".env")
st.set_page_config(page_title="Brand Visibility Intelligence", page_icon="◈", layout="wide", initial_sidebar_state="expanded")

NAVY = "#0A1020"
PANEL = "#121B2D"
MUTED = "#92A0B5"
CYAN = "#59D4D9"
LIME = "#C8F36A"
PLOT = {"template": "plotly_dark", "paper_bgcolor": "rgba(0,0,0,0)", "plot_bgcolor": "rgba(0,0,0,0)", "font": {"family": "Inter, sans-serif", "color": "#DCE5F2"}, "margin": {"l": 10, "r": 10, "t": 36, "b": 10}, "colorway": [CYAN, LIME, "#9B8AFB", "#FFB86B", "#FF7F9C", "#73A6FF"]}

st.markdown(f"""
<style>
  .stApp {{ background: radial-gradient(ellipse at 18% 0%, #15243a 0, {NAVY} 48%); color: #edf3fb; }}
  [data-testid="stSidebar"] {{ background: #0d1627; border-right: 1px solid #26334a; }}
  [data-testid="stMetric"] {{ background: linear-gradient(145deg, #17243a, #111a2a); border: 1px solid #26364f; padding: 16px 18px; border-radius: 14px; }}
  [data-testid="stMetricLabel"] {{ color: {MUTED}; }}
  [data-testid="stMetricValue"] {{ color: #f3f7fc; }}
  h1 {{ letter-spacing: -0.04em; }}
  h2, h3 {{ letter-spacing: -0.02em; }}
  .eyebrow {{ color: {CYAN}; font-size: .74rem; letter-spacing: .16em; font-weight: 700; text-transform: uppercase; }}
  .subtle {{ color: {MUTED}; }}
  div[data-testid="stTabs"] button {{ font-weight: 600; }}
  div[data-testid="stDataFrame"] {{ border: 1px solid #27364d; border-radius: 12px; overflow: hidden; }}
</style>
""", unsafe_allow_html=True)


def metric(label: str, value: str, help_text: str | None = None):
    st.metric(label, value, help=help_text)


def money(value: float | int | None) -> str:
    return "—" if pd.isna(value) else f"₹{value:,.0f}"


def chart(fig, height: int = 320):
    fig.update_layout(**PLOT, height=height, legend_title_text="")
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="rgba(146,160,181,.14)", zeroline=False)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


@st.cache_data(show_spinner=False)
def cached_options(df: pd.DataFrame, column: str) -> list[str]:
    return sorted(df[column].dropna().astype(str).unique().tolist())


all_products = initialize()
flash_message = st.session_state.pop("flash_message", None)
if flash_message:
    st.success(flash_message)

with st.sidebar:
    st.markdown("<div class='eyebrow'>Explore the market</div>", unsafe_allow_html=True)
    st.markdown("### Filters")
    keyword_options = ["All"] + cached_options(all_products, "keyword")
    platform_options = ["All"] + cached_options(all_products, "platform")
    brand_options = ["All"] + cached_options(all_products, "brand")
    range_options = ["All"] + cached_options(all_products, "price_range")
    keyword = st.selectbox("Search keyword", keyword_options)
    platform = st.selectbox("Shopping platform", platform_options)
    brand = st.selectbox("Brand", brand_options)
    price_range = st.selectbox("Price range", range_options)
    rating_range = st.slider("Customer rating", min_value=0.0, max_value=5.0, value=(0.0, 5.0), step=0.1)
    st.divider()
    with st.expander("Bring in data", expanded=False):
        st.caption("Import a CSV to replace the current products, or fetch current search results with SerpApi.")
        uploaded = st.file_uploader("CSV dataset", type=["csv"], help="Expected fields include keyword, title, price, rating, reviews and platform.")
        if st.button("Import CSV", use_container_width=True, disabled=uploaded is None):
            try:
                imported = pd.read_csv(uploaded)
                cleaned = clean_products(imported)
                save_products(cleaned)
                st.cache_data.clear()
                st.session_state["flash_message"] = f"Imported and cleaned {len(cleaned):,} product rows."
                st.rerun()
            except Exception as exc:
                st.error(f"Could not import this CSV: {exc}")
        st.markdown("**Live Google Shopping search**")
        api_keywords = st.text_input("Keywords", value="office chair ergonomic, air fryer India", help="Separate multiple searches with commas.")
        api_key = st.text_input("SerpApi key", value=os.getenv("SERPAPI_API_KEY", ""), type="password")
        if st.button("Fetch and add results", use_container_width=True):
            try:
                with st.spinner("Fetching Google Shopping results…"):
                    fetched = fetch_serpapi([k.strip() for k in api_keywords.split(",") if k.strip()], api_key=api_key)
                    combined = pd.concat([fetched, all_products], ignore_index=True, sort=False)
                    cleaned = clean_products(combined)
                    save_products(cleaned)
                st.cache_data.clear()
                st.session_state["flash_message"] = f"Added live results. The dataset now has {len(cleaned):,} products."
                st.rerun()
            except Exception as exc:
                st.error(f"SerpApi request failed: {exc}")

filtered = query_products({"keyword": keyword, "platform": platform, "brand": brand, "price_range": price_range, "rating_range": rating_range})
has_position = filtered["position"].notna().any() if "position" in filtered else False
ranked = filtered[filtered["position"].notna()].copy() if has_position else filtered.iloc[0:0].copy()
discounted_observed = filtered[filtered["discount_pct"].notna()] if "discount_pct" in filtered else filtered.iloc[0:0]
avg_price = filtered["price"].mean()
avg_rating = filtered["rating"].mean()
total_reviews = filtered["reviews"].fillna(0).sum()

st.markdown("<div class='eyebrow'>Commerce intelligence / India</div>", unsafe_allow_html=True)
st.title("Brand Visibility Intelligence")
st.markdown("A clear view of brand presence, pricing, and product performance across shopping platforms.")
if filtered.empty:
    st.warning("No products match these filters. Adjust the selections in the sidebar.")
    st.stop()

tabs = st.tabs(["Overview", "Brand insights", "Pricing analysis", "Platform comparison", "Visibility & ranking", "Product explorer"])

with tabs[0]:
    st.markdown("### Market snapshot")
    c = st.columns(4)
    with c[0]: metric("Products", f"{len(filtered):,}")
    with c[1]: metric("Average price", money(avg_price))
    with c[2]: metric("Average customer rating", f"{avg_rating:.2f} / 5" if pd.notna(avg_rating) else "—")
    with c[3]: metric("Customer reviews", f"{total_reviews:,.0f}")
    left, right = st.columns([1.4, 1])
    with left:
        st.markdown("#### Price distribution")
        chart(px.histogram(filtered.dropna(subset=["price"]), x="price", nbins=28, labels={"price": "Price (₹)", "count": "Products"}))
    with right:
        st.markdown("#### Products by keyword")
        kw = filtered.groupby("keyword", as_index=False).size().sort_values("size", ascending=True)
        chart(px.bar(kw, x="size", y="keyword", orientation="h", labels={"size": "Products", "keyword": "Keyword"}))
    plat = filtered.groupby("platform", as_index=False).size().sort_values("size", ascending=False)
    l, r = st.columns([.95, 1.45])
    with l:
        st.markdown("#### Platform mix")
        chart(px.pie(plat, names="platform", values="size", hole=.62))
    with r:
        st.markdown("#### Price and customer rating by category")
        cat = filtered.groupby("keyword", as_index=False).agg(avg_price=("price", "mean"), avg_rating=("rating", "mean"), products=("title", "count"))
        chart(px.scatter(cat, x="avg_price", y="avg_rating", size="products", color="keyword", hover_name="keyword", labels={"avg_price": "Average price (₹)", "avg_rating": "Average customer rating"}))
    st.markdown("#### Review volume distribution")
    chart(px.histogram(filtered.dropna(subset=["reviews"]), x="reviews", nbins=28, labels={"reviews": "Customer reviews", "count": "Products"}))

with tabs[1]:
    st.markdown("### Brand performance")
    brands = filtered.groupby("brand", as_index=False).agg(products=("title", "count"), avg_rating=("rating", "mean"), avg_price=("price", "mean"), reviews=("reviews", "sum"), avg_visibility=("visibility_score", "mean"))
    brands = brands.sort_values("products", ascending=False)
    top_brand = brands.iloc[0]
    best_rated = brands.dropna(subset=["avg_rating"]).sort_values("avg_rating", ascending=False)
    best_visibility = brands.dropna(subset=["avg_visibility"]).sort_values("avg_visibility", ascending=False)
    c = st.columns(4)
    with c[0]: metric("Brands in view", f"{filtered['brand'].nunique():,}")
    with c[1]: metric("Most listed", str(top_brand["brand"]), f"{int(top_brand['products'])} products")
    with c[2]: metric("Highest average rating", str(best_rated.iloc[0]["brand"]) if len(best_rated) else "—", f"{best_rated.iloc[0]['avg_rating']:.2f} / 5" if len(best_rated) else None)
    with c[3]: metric("Best visibility", str(best_visibility.iloc[0]["brand"]) if len(best_visibility) else "Needs rank data", "Based on 100 ÷ search position" if len(best_visibility) else "No search position in current data")
    l, r = st.columns(2)
    with l:
        st.markdown("#### Brands by product count")
        chart(px.bar(brands.head(14).sort_values("products"), x="products", y="brand", orientation="h", labels={"products": "Products", "brand": "Brand"}))
    with r:
        st.markdown("#### Average customer rating by brand")
        chart(px.bar(brands.dropna(subset=["avg_rating"]).sort_values("avg_rating").tail(14), x="avg_rating", y="brand", orientation="h", labels={"avg_rating": "Average customer rating (out of 5)", "brand": "Brand"}))
    st.markdown("#### Brands in top 10 search positions")
    if has_position:
        top10 = ranked[ranked["position"] <= 10].groupby("brand", as_index=False).size().sort_values("size", ascending=False).head(12)
        chart(px.bar(top10.sort_values("size"), x="size", y="brand", orientation="h", labels={"size": "Top 10 listings", "brand": "Brand"}))
    else:
        st.info("Search position is not present in the supplied CSV. Import ranked SerpApi results to populate this view.")

with tabs[2]:
    st.markdown("### Pricing and offers")
    c = st.columns(5)
    with c[0]: metric("Average price", money(avg_price))
    with c[1]: metric("Highest listed price", money(filtered["price"].max()))
    with c[2]: metric("Lowest listed price", money(filtered["price"].min()))
    discounted_count = int(discounted_observed["discount_pct"].gt(0).sum()) if not discounted_observed.empty else 0
    with c[3]: metric("Products discounted", f"{discounted_count / len(discounted_observed) * 100:.1f}%" if len(discounted_observed) else "Unavailable", f"Based on {len(discounted_observed):,} products with discount evidence.")
    with c[4]: metric("Price outliers flagged", f"{int(filtered['price_outlier'].sum()):,}", "Values above the 1.5×IQR upper fence are flagged and retained.")
    l, r = st.columns(2)
    with l:
        st.markdown("#### Price by brand")
        chart(px.box(filtered.dropna(subset=["price"]), x="brand", y="price", color="brand", points=False, labels={"price": "Price (₹)", "brand": "Brand"}))
    with r:
        st.markdown("#### Price versus search position")
        if has_position:
            chart(px.scatter(ranked.dropna(subset=["price", "reviews"]), x="price", y="position", color="brand", size="reviews", hover_name="title", labels={"price": "Price (₹)", "position": "Search position"}))
            st.caption("Lower search position numbers indicate stronger placement.")
        else:
            st.info("Search position is not available in the supplied CSV.")
    l, r = st.columns(2)
    with l:
        st.markdown("#### Price range mix")
        mix = filtered.groupby("price_range", as_index=False, observed=False).size()
        chart(px.bar(mix, x="price_range", y="size", labels={"price_range": "Price range", "size": "Products"}))
    with r:
        st.markdown("#### Discount by brand")
        if not discounted_observed.empty:
            d = discounted_observed.groupby("brand", as_index=False).agg(discount=("discount_pct", "mean")).dropna().sort_values("discount", ascending=False).head(12)
            chart(px.bar(d.sort_values("discount"), x="discount", y="brand", orientation="h", labels={"discount": "Average discount (%)", "brand": "Brand"}))
        else:
            st.info("The supplied CSV has no original price or discount field. Discount comparisons will appear after importing data with either field.")
    l, r = st.columns(2)
    with l:
        st.markdown("#### Discount by platform")
        if not discounted_observed.empty:
            d = discounted_observed.groupby("platform", as_index=False).agg(discount=("discount_pct", "mean")).dropna().sort_values("discount", ascending=False)
            chart(px.bar(d, x="platform", y="discount", labels={"discount": "Average discount (%)", "platform": "Platform"}))
        else:
            st.info("No discount source values are available for the current selection.")
    with r:
        st.markdown("#### Highest-priced product per keyword")
        highest = filtered.dropna(subset=["price"]).loc[filtered.dropna(subset=["price"]).groupby("keyword")["price"].idxmax(), ["keyword", "title", "platform", "price"]].sort_values("price", ascending=False)
        st.dataframe(highest, use_container_width=True, hide_index=True, column_config={"price": st.column_config.NumberColumn("Price (₹)", format="₹%.0f")})
    st.markdown("#### Customer rating versus price")
    chart(px.scatter(filtered.dropna(subset=["price", "rating"]), x="price", y="rating", color="platform", hover_name="title", labels={"price": "Price (₹)", "rating": "Customer rating (out of 5)"}))
    if not discounted_observed.empty:
        st.markdown("#### Discount and customer rating")
        chart(px.scatter(discounted_observed, x="discount_pct", y="rating", color="platform", hover_name="title", labels={"discount_pct": "Discount (%)", "rating": "Customer rating (out of 5)"}))

with tabs[3]:
    st.markdown("### Platform comparison")
    by_platform = filtered.groupby("platform", as_index=False).agg(products=("title", "count"), avg_rating=("rating", "mean"), avg_price=("price", "mean"), brands=("brand", "nunique"), avg_position=("position", "mean"))
    best_platform = by_platform.dropna(subset=["avg_rating"]).sort_values("avg_rating", ascending=False)
    cheapest = by_platform.dropna(subset=["avg_price"]).sort_values("avg_price")
    most_products = by_platform.sort_values("products", ascending=False)
    c = st.columns(4)
    with c[0]: metric("Platforms", f"{filtered['platform'].nunique()}")
    with c[1]: metric("Highest average rating", str(best_platform.iloc[0]["platform"]) if len(best_platform) else "—")
    with c[2]: metric("Lowest average price", str(cheapest.iloc[0]["platform"]) if len(cheapest) else "—", money(cheapest.iloc[0]["avg_price"]) if len(cheapest) else None)
    with c[3]: metric("Most products", str(most_products.iloc[0]["platform"]) if len(most_products) else "—", f"{int(most_products.iloc[0]['products'])} listings" if len(most_products) else None)
    l, r = st.columns(2)
    with l:
        st.markdown("#### Product listings by platform")
        chart(px.bar(by_platform.sort_values("products"), x="products", y="platform", orientation="h", labels={"products": "Products", "platform": "Platform"}))
    with r:
        st.markdown("#### Average customer rating by platform")
        chart(px.bar(by_platform.sort_values("avg_rating"), x="platform", y="avg_rating", labels={"platform": "Platform", "avg_rating": "Rating (out of 5)"}))
    l, r = st.columns(2)
    with l:
        st.markdown("#### Average price by platform")
        chart(px.bar(by_platform.sort_values("avg_price"), x="platform", y="avg_price", labels={"platform": "Platform", "avg_price": "Average price (₹)"}))
    with r:
        st.markdown("#### Brand mix by platform")
        mix = filtered.groupby(["platform", "brand"], as_index=False).size()
        chart(px.bar(mix, x="platform", y="size", color="brand", labels={"platform": "Platform", "size": "Products", "brand": "Brand"}))
    if has_position:
        st.markdown("#### Average search position by platform")
        chart(px.bar(by_platform.dropna(subset=["avg_position"]).sort_values("avg_position", ascending=False), x="platform", y="avg_position", labels={"platform": "Platform", "avg_position": "Average search position (lower is better)"}))

with tabs[4]:
    st.markdown("### Search visibility and product engagement")
    c = st.columns(4)
    with c[0]: metric("Average customer rating", f"{avg_rating:.2f} / 5" if pd.notna(avg_rating) else "—")
    with c[1]: metric("Average visibility score", f"{ranked['visibility_score'].mean():.2f}" if has_position else "Needs rank data", "Visibility score = 100 ÷ search position")
    with c[2]: metric("Products in top 10", f"{(ranked['position'].le(10).mean() * 100):.1f}%" if has_position else "Needs rank data")
    with c[3]: metric("Best-ranked product", str(ranked.loc[ranked["position"].idxmin(), "title"])[:34] if has_position else "Needs rank data", f"Position {int(ranked['position'].min())}" if has_position else "Import SerpApi search results")
    if has_position:
        l, r = st.columns(2)
        with l:
            st.markdown("#### Search position distribution")
            chart(px.histogram(ranked, x="position", nbins=20, labels={"position": "Search position", "count": "Products"}))
        with r:
            st.markdown("#### Reviews versus search position")
            chart(px.scatter(ranked.dropna(subset=["reviews", "price"]), x="reviews", y="position", size="price", color="brand", hover_name="title", labels={"reviews": "Reviews", "position": "Search position"}))
        st.markdown("#### Customer rating versus search position")
        chart(px.scatter(ranked.dropna(subset=["rating", "reviews"]), x="rating", y="position", size="reviews", color="platform", hover_name="title", labels={"rating": "Customer rating (out of 5)", "position": "Search position"}))
        st.markdown("#### Visibility score by brand")
        vis = ranked.groupby("brand", as_index=False).agg(visibility=("visibility_score", "mean")).sort_values("visibility", ascending=False).head(14)
        chart(px.bar(vis.sort_values("visibility"), x="visibility", y="brand", orientation="h", labels={"visibility": "Average visibility score", "brand": "Brand"}))
        st.markdown("#### Highest-visibility products")
        st.dataframe(ranked.sort_values("position").head(10)[["position", "title", "brand", "platform", "price", "rating", "reviews"]], use_container_width=True, hide_index=True, column_config={"position": st.column_config.NumberColumn("Position", format="%d"), "price": st.column_config.NumberColumn("Price (₹)", format="₹%.0f"), "rating": st.column_config.NumberColumn("Customer rating", format="%.1f / 5")})
        st.caption("Visibility score is a rank-based index (100 ÷ position); higher values indicate stronger placement. Customer rating remains a separate measure.")
    else:
        st.info("The uploaded source dataset contains customer ratings but no search-position field. This section will populate when you fetch ranked Google Shopping results through SerpApi.")
        st.markdown("#### Customer rating distribution")
        chart(px.histogram(filtered.dropna(subset=["rating"]), x="rating", nbins=20, labels={"rating": "Customer rating (out of 5)", "count": "Products"}))
    st.markdown("#### Customer rating versus review volume")
    chart(px.scatter(filtered.dropna(subset=["rating", "reviews", "price"]), x="reviews", y="rating", size="price", color="platform", hover_name="title", labels={"reviews": "Reviews", "rating": "Customer rating (out of 5)"}))

with tabs[5]:
    st.markdown("### Product explorer")
    c = st.columns(3)
    with c[0]: metric("Filtered products", f"{len(filtered):,}")
    with c[1]: metric("Average price", money(avg_price))
    with c[2]: metric("Average customer rating", f"{avg_rating:.2f} / 5" if pd.notna(avg_rating) else "—")
    search = st.text_input("Search product title", placeholder="Try 'Samsung', 'shoes', or a model number")
    view = filtered.copy()
    if search.strip():
        view = view[view["title"].str.contains(search.strip(), case=False, na=False)]
    columns = ["keyword", "title", "brand", "price", "rating", "reviews", "platform", "position", "discount_pct", "delivery", "product_link"]
    columns = [col for col in columns if col in view.columns]
    st.dataframe(view[columns].sort_values("position", na_position="last") if "position" in columns else view[columns], use_container_width=True, hide_index=True, height=520, column_config={"price": st.column_config.NumberColumn("Price (₹)", format="₹%.0f"), "rating": st.column_config.NumberColumn("Customer rating", format="%.1f / 5"), "reviews": st.column_config.NumberColumn("Reviews", format="%d"), "position": st.column_config.NumberColumn("Search position", format="%d"), "discount_pct": st.column_config.NumberColumn("Discount %", format="%.1f%%"), "product_link": st.column_config.LinkColumn("Product link", display_text="Open")})
    st.download_button("Download filtered CSV", data=view.to_csv(index=False).encode("utf-8"), file_name="brand_visibility_filtered.csv", mime="text/csv")

st.caption(f"Data source: SQLite · {len(all_products):,} cleaned records · Prices are displayed in Indian rupees. Search ranking and discounts are shown only where source fields support them.")
