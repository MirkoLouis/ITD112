# ITD112 Laboratory Exercise 1: Integrating Soil and Weather APIs

## Summary of the Activity

This project is a full API integration pipeline built as a single-page Streamlit web application. It fetches static soil properties from the **SoilGrids v2.0 REST API** (ISRIC) and daily weather records from the **Open-Meteo Historical Archive API** for five sites across Mindanao, Philippines. The pipeline covers building and sending API requests defensively (timeouts, retries with backoff, disk caching, and fair-use pauses), parsing two differently-shaped JSON responses into tabular data, joining the two datasets on a shared site key, deriving a daily water balance, and answering six analytical questions through interactive charts — all in one Python file.

## What the App Wants to Find Out

The app aims to answer six questions that span both data sources. Two of them (Q5 and Q6) cannot be answered by either API alone, which is the primary justification for the integration step.

| # | Question | Chart Type | Source |
|---|---|---|---|
| Q1 | How does temperature change over time at each site? | Line chart — 7-day rolling mean | Open-Meteo |
| Q2 | Does monthly rainfall meet evaporative demand (ET₀)? | Combo: monthly bars + ET₀ line | Open-Meteo |
| Q3 | How variable is daily rainfall across months? | Box plot by month | Open-Meteo |
| Q4 | What is the topsoil texture (sand / silt / clay) at each site? | 100 % stacked horizontal bar | SoilGrids |
| Q5 | Does higher clay content moderate annual water stress? | Bubble scatter + linear trend | **Both** |
| Q6 | Where are the sites and how do their SOC and rainfall compare? | Map — colour = SOC, size = rainfall | **Both** |

## Screenshots

| |
|---|
| **Title and Step 2 — Site selection and date inputs** |
| ![Title and Step 2](screenshots/Title%20and%20Step%202.png) |
| **Steps 3 & 4 — Request URLs and response log** |
| ![Step 3 and 4](screenshots/Step%203%20and%204.png) |
| **Step 5 — Parsed weather and soil audit tables** |
| ![Step 5](screenshots/Step%205.png) |
| **Steps 6 & 7 — Integration metrics and chart selector** |
| ![Step 6 and 7](screenshots/Step%206%20and%207.png) |
| **Q2 — Rainfall vs ET₀ and Q3 — Daily Rainfall Variability** |
| ![Q2 and Q3](screenshots/7(Q2)%20and%207(Q3).png) |
| **Q4 — Topsoil Texture and Q5 — Clay vs Water Stress** |
| ![Q4 and Q5](screenshots/7(Q4)%20and%207(Q5).png) |
| **Q6 — Site Map and Export buttons** |
| ![Q6 and Export](screenshots/7(Q6)%20and%20Export.png) |

## Changes from the Source Code & Why

The lab instruction code blocks served as the structural blueprint. The following adjustments were made when the actual API responses and runtime behaviour differed from what the instructions assumed.

---

### 1. `CACHE_DIR` — path anchor changed to script location

**Source code:**
```python
CACHE_DIR = Path("cache")
```
**Implementation:**
```python
CACHE_DIR = Path(__file__).parent / "cache"
```
**Why:** `Path("cache")` resolves relative to whatever directory the terminal is in when `streamlit run` is executed. Running the app from the repo root (`ITD112/`) rather than from inside `api-app/` causes the cache to be written to `ITD112/cache/` instead of `api-app/cache/`, creating a stray duplicate folder and causing every run to be treated as a cache miss (fetching from the network again). Anchoring to `__file__` guarantees the cache always resolves beside the script file regardless of the working directory.

---

### 2. `Valencia` latitude adjusted

**Source code:**
```python
("Valencia", 7.900, 125.090),
```
**Implementation:**
```python
("Valencia", 7.890, 125.090),
```
**Why:** The SoilGrids API returned null for every soil property at the original coordinate. The lab instructions note that this happens when a point falls on water, a built-up area, or a gap in the coverage grid, and advises moving the point slightly. Shifting the latitude ~1 km south resolved the mismatch.

---

### 3. `parse_weather` — defensive `.get()` on the `daily` key

**Source code:**
```python
df = pd.DataFrame(res["daily"])
```
**Implementation:**
```python
df = pd.DataFrame(res.get("daily", {}))
```
**Why:** The source code assumes the `daily` key is always present. On a malformed or partial response (which the SoilGrids beta warning in the lab anticipates for similar APIs), a direct key access raises a `KeyError` and crashes the parse step. Using `.get()` with an empty dict fallback allows the rest of the pipeline to continue and surface the problem as an empty dataframe rather than a traceback.

---

### 4. `parse_soil` — guard for empty `properties` block

**Source code:**
```python
for layer in data["properties"]["layers"]:
```
**Implementation:**
```python
properties = data.get("properties", {})
if not properties:
    return pd.DataFrame(columns=[...])
for layer in properties.get("layers", []):
```
**Why:** SoilGrids occasionally returns a successful HTTP 200 with an empty or incomplete body (noted in the lab as a consequence of it being a beta service with no uptime guarantee). Accessing `data["properties"]["layers"]` directly on such a response raises a `KeyError`. The guard detects the empty case early and returns a typed empty DataFrame so the rest of the pipeline degrades gracefully instead of crashing.

---

### 5. `soil_table` — guard for empty long-format input

**Source code:**
```python
wide = (soil_long.pivot(...).reindex(...).reset_index())
```
**Implementation:**
```python
if soil_long.empty:
    return pd.DataFrame(columns=["site", "lat", "lon"] + SOIL_PROPERTIES)
wide = (soil_long.pivot(...).reindex(...).reset_index())
```
**Why:** Calling `.pivot()` on an empty DataFrame raises a `ValueError`. If every SoilGrids request fails or returns null, `soil_long` will be empty. The early return prevents the crash and passes a correctly-shaped empty table into the join step.

---

### 6. SoilGrids error handling — `raise` replaced with `st.error` + `continue`

**Source code:**
```python
except requests.RequestException as exc:
    raise RuntimeError(
        f"SoilGrids failed for {req['label']}: {exc}. ..."
    ) from exc
```
**Implementation:**
```python
except requests.RequestException as exc:
    st.error(f"SoilGrids failed for {req['label']}: {exc}. ...")
    continue
```
**Why:** Re-raising the exception crashes the entire app and shows a raw traceback to the user. Using `st.error()` displays a readable inline message and `continue` allows the loop to move on to the next site. This means a failure on one site does not prevent the pipeline from processing whichever sites did return data successfully.

---

### 7. Q2 — bar series name corrected

**Source code:**
```python
fig.add_bar(..., name="Rainfall (surplus month)", ...)
```
**Implementation:**
```python
fig.add_bar(..., name="Rainfall  (pale = deficit month)", ...)
```
**Why:** The original label `"Rainfall (surplus month)"` is applied to every bar in the chart — including the deficit-month bars that are rendered in a paler colour. The label therefore mislabels deficit months as surplus months. The updated name describes the colour encoding explicitly so the legend is self-explanatory without requiring the reader to infer the convention.

---

### 8. Q3 — month axis uses names instead of integers

**Source code:**
```python
fig = px.box(site_data, x='month', y='precipitation_sum', ...)
```
**Implementation:**
```python
site_data["month_name"] = site_data["month"].apply(lambda m: MONTHS[m - 1])
site_data["month_name"] = pd.Categorical(site_data["month_name"], categories=MONTHS, ordered=True)
fig = px.box(site_data, x="month_name", y="precipitation_sum", ...)
```
**Why:** Plotting `x='month'` (an integer column) renders the x-axis as `1, 2, 3 … 12`. Using a `pd.Categorical` column with the ordered `MONTHS` list produces `Jan … Dec` labels in the correct calendar order, making the chart immediately readable without needing to mentally map numbers to months.

---

### 9. Q6 — colour scale changed from cyclical to sequential; fixed range removed

**Source code:**
```python
color_continuous_scale=px.colors.cyclical.IceFire, range_color=[0, 100]
```
**Implementation:**
```python
color_continuous_scale="YlOrBr"   # range_color removed
```
**Why:** `IceFire` is a *cyclical* colour scale — it starts and ends at the same colour (black), so both the minimum and maximum SOC values appear identical on the legend (0 = black, 100 = black). SOC is a linear quantity that increases monotonically; it needs a *sequential* scale. `YlOrBr` (light yellow → dark brown) is appropriate for soil organic carbon and reads correctly from low to high. The hardcoded `range_color=[0, 100]` was also removed because the actual SOC values in the data are approximately 54–61 g/kg — fixing the range to 0–100 compresses all sites into a narrow portion of the scale with no visible contrast between them. Removing the constraint lets Plotly auto-scale to the real data range.

---

*Sources: SoilGrids 2.0 (ISRIC, CC BY 4.0), 0–5 cm mean; Open-Meteo Historical Weather API (CC BY 4.0).*
