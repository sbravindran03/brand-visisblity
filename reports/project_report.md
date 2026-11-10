# Brand Visibility Intelligence Dashboard

## Project purpose

This project supports e-commerce and digital-marketing teams comparing product presence, price positioning, customer feedback, and search placement across retailers. The dashboard uses a local Streamlit interface, a cleaned CSV export, and SQLite storage. Optional SerpApi extraction adds current Google Shopping results for selected search terms.

## Source data reviewed

The supplied `brand_dirty_dataset.csv` contains 1,320 rows and seven columns: `keyword`, `title`, `price`, `rating`, `reviews`, `platform`, and `delivery`. Five search keywords and four retailers are represented. Prices appear to be INR based on the brief and retailer/category context; the source does not provide a currency field.

### Data quality findings

- The source has 126 blank and 66 nonnumeric price values; 26 parsed prices are zero or negative and are set to missing.
- There are 131 blank customer ratings. Parsed ratings are within the 0–5 scale.
- There are 26 nonnumeric review-count values in the source. Valid review counts are converted to integers.
- Retailer capitalization varies; names are standardized to title case.
- Product titles may include repeated punctuation; repeated exclamation marks and extra whitespace are cleaned.
- Duplicate records are removed using normalized keyword + title + platform. This removes 124 rows after title cleanup, leaving 1,196 products.
- The cleaned set has 1,000 positive numeric prices. Its median is ₹24,669.50 and its maximum is ₹498,050. Prices above the 1.5×IQR upper fence (₹79,009.50 on this snapshot) are flagged and retained; 38 cleaned rows are flagged.
- Missing price, rating, review, delivery, ranking, or discount evidence is retained as missing or labeled “Not provided” where appropriate. The cleaning process does not impute measurements that were not collected.

## Feature definitions

| Feature | Definition |
|---|---|
| Brand | Recognized brand from the title; otherwise the first title token is used as a fallback. |
| Price range | Under ₹1k, ₹1k–₹5k, ₹5k–₹20k, ₹20k–₹50k, or ₹50k+. |
| Discount percentage | `(raw_price - price) / raw_price × 100`, or a valid supplied discount. Blank without evidence. |
| Visibility score | `100 / position`; higher indicates better placement in the returned result order. |
| Top-ten share | Ranked products with position ≤10 divided by products with a position. |
| Price outlier | Price above the imported dataset's 1.5×IQR upper fence. Flagged for review, not removed or capped. |

Customer rating (stars out of 5) and search position (rank) are kept separate. Several questions in the project brief refer to “rating” when the intended measure appears to be rank; dashboard labels use the correct field explicitly.

## Analysis and dashboard

The six dashboard sections cover market overview, brand comparison, pricing and offers, retailer comparison, visibility and ranking, and product-level exploration. Shared filters apply to the selected keyword, platform, brand, price range, and customer-rating range. Product Explorer supports title search, sorting, product links where supplied, and filtered CSV download.

The supplied CSV does not contain search position, original price, or discount. Consequently, rank-based charts and discount comparisons are explicitly marked unavailable until source data with those fields is imported. The SerpApi connector requests the Google Shopping engine using `q`, `api_key`, and `gl=in`; its results can include position, extracted price, extracted old price, rating, reviews, delivery, and retailer. API access requires the user's SerpApi key.

## Intended business use

- Compare brand listing counts and customer-rating averages within the same keyword/platform selection.
- Find price-position patterns once ranked search results are available.
- Compare retailers on price, listing count, and customer rating.
- Identify products with observed discounts when original-price evidence is present.
- Investigate unusually high prices while preserving those records for review.

These are descriptive comparisons. Correlation between price, reviews, rating, and rank does not establish that one factor causes another. Google Shopping results are location- and time-dependent and should be refreshed before making current competitive decisions.

## Run and refresh

Install dependencies with `pip install -r requirements.txt`, then run `streamlit run app.py`. The app initializes the SQLite database from the included clean snapshot on first launch. Use the sidebar data controls to import a new CSV or fetch SerpApi results. Keep SerpApi credentials in `.env` or enter them through the password field in the sidebar; do not commit secrets.
