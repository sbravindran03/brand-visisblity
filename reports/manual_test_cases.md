# Manual Test Cases — Brand Visibility Intelligence Dashboard

**Tester:** ____________________  
**Date:** ____________________  
**Build/version:** ____________________  
**Environment:** ____________________

## How to run

From the project folder, activate the virtual environment and start the app:

```bash
source .venv/bin/activate
streamlit run app.py
```

Open the local URL shown in the terminal, usually `http://localhost:8501`. Use the included dataset for cases TC-01 through TC-11. SerpApi cases are optional and require a valid API key.

## Expected baseline for the included dataset

These values provide a quick check that the starting data loaded correctly:

| Measure | Expected value |
|---|---:|
| Clean product records | 1,196 |
| Average price | ₹33,555 (dashboard display; underlying mean ₹33,555.16) |
| Average customer rating | 3.79 / 5 |
| Total reviews | 2,843,090 |
| Search-position records | 0 |
| Records with discount evidence | 0 |

Keyword counts: Air Fryer India 237; Men Running Shoes 240; Microwave Oven Convection 255; Office Chair Ergonomic 229; Power Bank Fast Charging 235.

## Test cases

| ID | Feature | Steps | Expected result | Result / notes |
|---|---|---|---|---|
| TC-01 | App launch | Start the app using the command above and open the local URL. | Dashboard opens without a traceback. Six tabs are visible: Overview, Brand insights, Pricing analysis, Platform comparison, Visibility & ranking, and Product explorer. | ☑ Pass — AppTest rendered all six tabs; no app exceptions. |
| TC-02 | Default overview | Leave all sidebar filters at **All** and the rating range at 0–5. | Overview shows 1,196 products, average price ₹33,555 (underlying mean ₹33,555.16), average rating 3.79 / 5, and 2,843,090 reviews. Charts render. | ☑ Pass — All baseline metrics and charts rendered. |
| TC-03 | Keyword filter | Select **Microwave Oven Convection** in Search keyword. | All dashboard tabs reflect that keyword; the filtered product count is 255. Reset to All afterward. | ☑ Pass — 255 products. |
| TC-04 | Platform filter | Select **Amazon** in Shopping platform. | Dashboard shows only Amazon records; product count is 309. Reset to All afterward. | ☑ Pass — 309 products. |
| TC-05 | Combined filters | Select **Air Fryer India** and **Amazon**. | Charts and KPIs update to the intersection of the two filters. Every visible product belongs to both selected values. | ☑ Pass — 54 matching products. |
| TC-06 | Brand filter | Select one brand in the Brand filter. | Brand insight and product explorer show only that brand; overview counts and charts update. | ☑ Pass — HP filter returned 154 products. |
| TC-07 | Price and rating filters | Select a Price range, then narrow the Customer rating slider. | Product count and charts update to matching prices and ratings. Products with missing ratings are excluded when the rating range is narrowed. | ☑ Pass — Under ₹1k and rating 4–5 returned 6 products. |
| TC-08 | Product title search | Open Product explorer and search for **Samsung**. Then search for a phrase that is not present. | First search returns matching titles only. Unmatched search returns an empty table without crashing. Clear the search afterward. | ☑ Pass — Samsung returned 125 matching rows; unmatched search returned none. |
| TC-09 | Product table sorting | In Product explorer, sort the table by Price or Reviews. | Rows reorder by the selected column; values and labels remain aligned. | ☑ Pass — Clicked the title header; rows sorted alphabetically in the live browser. |
| TC-10 | Filtered CSV download | Apply a keyword or platform filter, then select **Download filtered CSV**. | A CSV downloads and contains only the currently filtered and searched records, with the product columns and derived fields. | ☑ Pass — Triggered export with 237 matching products; download control and filtered export code path checked. The saved file was not reopened for a separate content audit. |
| TC-11 | Rank and discount availability | Open Visibility & ranking and Pricing analysis using the supplied CSV. | App explains that search position and discount evidence are unavailable. It does not display fabricated rank or discount values. This is expected for this source file. | ☑ Pass — Explicit unavailable messages; database has 0 position and 0 discount values. |
| TC-12 | CSV import and cleaning | In the sidebar, expand Bring in data, upload `data/raw/brand_dirty_dataset.csv`, and select Import CSV. | App confirms import. Product count is 1,196 after cleaning/deduplication; retailer names are standardized; invalid/nonpositive prices and invalid ratings/reviews are blank. | ☑ Pass — Import confirmation reported 1,196 cleaned rows. |
| TC-13 | Missing SerpApi key | Leave the SerpApi key blank and select Fetch and add results. | App displays a clear message that an API key is required; it does not crash or replace the current dataset. | ☑ Pass — Clear missing-key message; no exception and no API request. |
| TC-14 | SerpApi fetch (optional) | Enter a valid SerpApi key and one keyword, then select Fetch and add results. | App fetches Google Shopping results, adds them to the existing data, and refreshes. Returned records may populate position, visibility, and discount views where those source fields exist. | N/A — Not run because no valid SerpApi key was provided. |

## Execution summary

| Total | Passed | Failed | Not run / N/A |
|---:|---:|---:|---:|
| 14 | 13 | 0 | 1 |

**Issues found / screenshots:**  
TC-13 initially exposed a blank-key fallback bug. Fixed it so an explicitly blank key is rejected before any network request. TC-14 needs a valid key and remains unverified.

**Presenter summary:** Startup, baseline metrics, interactive filters, title search and sorting, filtered export handling, CSV cleaning/import, and unavailable ranking/discount handling were checked. The live SerpApi request was not run because no valid key was provided.
