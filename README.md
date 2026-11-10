# Brand Visibility Intelligence Dashboard

An interactive Streamlit project for comparing product listings, prices, brands, customer ratings, and search placement across shopping platforms. The supplied dirty CSV is included in `data/raw/`; cleaned data is written to `data/processed/cleaned_products.csv` and SQLite (`data/brand_visibility.db`).

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

The first run initializes the SQLite database from the included CSV. Use the **Bring in data** section in the sidebar to import a replacement CSV or add live Google Shopping results. The dashboard queries SQLite for its shared filters and supports filtered CSV export from Product Explorer.

## Optional SerpApi extraction

The app calls `https://serpapi.com/search` with `engine=google_shopping`, a `q` search term, and `gl=in`, following [SerpApi's Google Shopping API](https://serpapi.com/google-shopping-api). The key can be entered in the sidebar or set in a local `.env` file:

```text
SERPAPI_API_KEY=your_key_here
```

Copy `.env.example` to `.env` before adding your key. Keep `.env` private; it is excluded from Git. Each search returns current Google Shopping results. Results and rankings can vary by time and location.

## Dashboard sections

- **Overview:** product count, average price and customer rating, review volume, price distribution, keyword volume, and retailer mix.
- **Brand insights:** listing volume, average customer rating, and top-ten search placement when ranking data exists.
- **Pricing analysis:** price ranges, brand price spread, price versus search position, and discounts when original price/discount evidence exists.
- **Platform comparison:** listing count, average price/rating, and brand mix per retailer.
- **Visibility & ranking:** search position, rank-based visibility, and review relationships when ranked results exist. Without rank data it shows customer-rating distribution and an explicit availability note.
- **Product explorer:** searchable and sortable product records with filtered CSV export.

## Data definitions and limitations

- **Customer rating** is the product's review score (0–5). **Search position** is a product's order in a Google Shopping result list. They are separate fields.
- **Visibility score** is `100 ÷ position`. A higher value means a better result position; it is not a Google metric.
- **Discount percentage** is computed from `(raw_price - price) ÷ raw_price × 100`, or taken from a valid supplied discount field. It remains blank when discount evidence is absent.
- **Price ranges** use rupee thresholds: under ₹1k, ₹1k–₹5k, ₹5k–₹20k, ₹20k–₹50k, and ₹50k+.
- Price outliers above the 1.5×IQR upper fence are flagged and retained, so a user can inspect them rather than silently losing source records.
- The supplied CSV has 1,320 source rows and fields for keyword, title, price, customer rating, reviews, platform, and delivery. It has **no search position, original price, or discount column**. Those measures stay unavailable until suitable API/source data is added.
- The supplied currency is treated as INR based on the project brief and Indian platform/category values. The source CSV does not include a currency column.
- Duplicate products are identified by normalized keyword + title + platform. Rows without an identifiable price/rating/review remain in the dataset with those fields blank.

## Project layout

```text
app.py                         Streamlit dashboard
src/pipeline.py                CSV cleaning, SerpApi extraction, SQLite access
data/raw/                      Original supplied dataset
data/processed/                Cleaned dataset
data/brand_visibility.db       SQLite dashboard source
reports/project_report.md      Data quality notes and analysis definitions
```
