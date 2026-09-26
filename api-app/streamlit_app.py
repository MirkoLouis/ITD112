import streamlit as st
import pandas as pd
from datetime import date
import requests
import json
import hashlib
import time
from pathlib import Path
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 1. Configuration
st.set_page_config(page_title="ITD112 Laboratory Exercise 1: API Integration", layout="wide")

SITES = pd.DataFrame(
    [
        ("Iligan City",     8.200, 124.300),
        ("Malaybalay",      8.150, 125.130),
        ("Valencia",        7.890, 125.090),
        ("Davao (Calinan)", 7.190, 125.460),
        ("General Santos",  6.150, 125.150),
    ],
    columns=["site", "lat", "lon"],
)

SOIL_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
WEATHER_URL = "https://archive-api.open-meteo.com/v1/archive"
SOIL_PROPERTIES = ["clay", "sand", "silt", "phh2o", "soc"]
SOIL_DEPTH = "0-5cm"
DAILY_VARS = ["temperature_2m_mean", "precipitation_sum", "et0_fao_evapotranspiration"]
TIMEZONE = "Asia/Manila"

CACHE_DIR = Path(__file__).parent / "cache"
SOILGRIDS_PAUSE_S = 12

COLORS = {
    "sky": "#0ea5e9",
    "sky_pale": "#e0f2fe",
    "sun": "#f59e0b"
}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# 3. Build the request
def full_url(url, params):
    """The exact URL that will be sent, with the query string encoded."""
    return requests.Request("GET", url, params=params).prepare().url

def build_weather_request(sites, start, end):
    """Open-Meteo accepts comma-separated coordinates, so one request covers every site."""
    params = {
        "latitude":  ",".join(str(v) for v in sites["lat"]),
        "longitude": ",".join(str(v) for v in sites["lon"]),
        "start_date": start,
        "end_date": end,
        "daily": ",".join(DAILY_VARS),
        "timezone": TIMEZONE,
    }
    return {"api": "Open-Meteo", "label": "All sites", "url": WEATHER_URL,
            "params": params, "full_url": full_url(WEATHER_URL, params)}

def build_soil_request(site, lat, lon):
    """SoilGrids takes one point per request. 'property' repeats once per soil property."""
    params = [("lat", lat), ("lon", lon), ("depth", SOIL_DEPTH), ("value", "mean")]
    params += [("property", p) for p in SOIL_PROPERTIES]      # repeated keys
    return {"api": "SoilGrids", "label": site, "url": SOIL_URL,
            "params": params, "full_url": full_url(SOIL_URL, params)}

# 4. Send the request
@st.cache_resource
def http_session():
    """Session that retries on rate limiting (429) and server errors (5xx)."""
    retry = Retry(total=3, backoff_factor=2,
                  status_forcelist=(429, 500, 502, 503, 504),
                  allowed_methods=("GET",))
    s = requests.Session()
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers["User-Agent"] = "itd112-lab1/1.0"
    return s

def send(req):
    """GET the request and return the response record. A response saved on disk is
    reused instead of calling the API again."""
    key = hashlib.sha1(
        (req["url"] + json.dumps(req["params"], sort_keys=True, default=str)).encode()
    ).hexdigest()
    path = CACHE_DIR / f"{key}.json"

    if path.exists():                                   # cache hit — no network at all
        text = path.read_text(encoding="utf-8")
        return {"status": None, "from_cache": True, "data": json.loads(text)}

    r = http_session().get(req["url"], params=req["params"], timeout=60)
    r.raise_for_status()                                # 4xx / 5xx -> exception
    data = r.json()
    CACHE_DIR.mkdir(exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return {"status": r.status_code, "from_cache": False, "data": data}

# 5. Parse the JSON
def parse_weather(data, sites):
    """Each site's 'daily' block holds parallel arrays; each array becomes a column."""
    results = data if isinstance(data, list) else [data]   # one site returns an object
    frames = []
    for site, res in zip(sites["site"], results):
        df = pd.DataFrame(res.get("daily", {}))
        df.insert(0, "site", site)
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def parse_soil(data, site):
    """One row per soil property. SoilGrids stores integers; dividing by d_factor gives
    conventional units (g/kg -> %, pH x10 -> pH, dg/kg -> g/kg)."""
    rows = []
    properties = data.get("properties", {})
    if not properties:
        return pd.DataFrame(columns=["site", "property", "raw_mean", "mapped_units", "d_factor", "value", "target_units"])
        
    for layer in properties.get("layers", []):
        raw = layer["depths"][0]["values"]["mean"]
        unit = layer["unit_measure"]
        rows.append({
            "site": site,
            "property": layer["name"],
            "raw_mean": raw,
            "mapped_units": unit.get("mapped_units"),
            "d_factor": unit["d_factor"],
            "value": np.nan if raw is None else raw / unit["d_factor"],
            "target_units": unit.get("target_units"),
        })
    return pd.DataFrame(rows)

def soil_table(soil_long, sites):
    """Pivot to one row per site, one column per property, and attach coordinates."""
    if soil_long.empty:
        return pd.DataFrame(columns=["site", "lat", "lon"] + SOIL_PROPERTIES)
    wide = (soil_long.pivot(index="site", columns="property", values="value")
            .reindex(columns=SOIL_PROPERTIES).reset_index())
    wide.columns.name = None
    return sites.merge(wide, on="site", how="left")

# 6. Integrate
def integrate(weather, soil):
    if weather.empty or soil.empty:
        return pd.DataFrame(), pd.DataFrame()
        
    daily = weather.merge(soil, on="site", how="left")          # the join
    if "time" in daily.columns:
        daily["time"] = pd.to_datetime(daily["time"])
        daily["month"] = daily["time"].dt.month
        
    if "precipitation_sum" in daily.columns and "et0_fao_evapotranspiration" in daily.columns:
        daily["water_balance_mm"] = (daily["precipitation_sum"]
                                     - daily["et0_fao_evapotranspiration"])

    summary = (daily.groupby("site", sort=False)
               .agg(rain_mm=("precipitation_sum", "sum"),
                    et0_mm=("et0_fao_evapotranspiration", "sum"),
                    water_balance_mm=("water_balance_mm", "sum"),
                    temp_mean_c=("temperature_2m_mean", "mean"))
               .reset_index().merge(soil, on="site"))
    return daily, summary

# 7. Charts
def chart_q1(daily, site):
    site_data = daily[daily["site"] == site].copy()
    if not site_data.empty and 'temperature_2m_mean' in site_data.columns:
        site_data['temp_rolling'] = site_data['temperature_2m_mean'].rolling(7).mean()
        fig = px.line(site_data, x='time', y='temp_rolling', title=f"Q1: 7-day Rolling Mean Temp ({site})")
        return fig
    return go.Figure()

def chart_q2(daily, site):
    """Monthly rainfall bars vs reference ET0 line, on the same mm axis."""
    site_data = daily[daily["site"] == site]
    if site_data.empty: return go.Figure()
    
    m = (site_data.groupby("month")
         [["precipitation_sum", "et0_fao_evapotranspiration"]].sum()
         .reindex(range(1, 13), fill_value=0))
    deficit = m["precipitation_sum"] < m["et0_fao_evapotranspiration"]

    fig = go.Figure()
    fig.add_bar(x=MONTHS, y=m["precipitation_sum"],
                name="Rainfall  (pale = deficit month)",
                marker_color=np.where(deficit, COLORS["sky_pale"], COLORS["sky"]))
    fig.add_scatter(x=MONTHS, y=m["et0_fao_evapotranspiration"], name="Reference ET0",
                    mode="lines+markers", line=dict(color=COLORS["sun"], width=2.5))
    fig.update_layout(title=f"Q2: Rainfall vs ET0 ({site})")
    fig.update_yaxes(title="mm per month", rangemode="tozero")
    return fig

def chart_q3(daily, site):
    site_data = daily[daily["site"] == site].copy()
    if not site_data.empty:
        site_data["month_name"] = site_data["month"].apply(lambda m: MONTHS[m - 1])
        # Preserve calendar order by sorting month integer then assigning category
        site_data["month_name"] = pd.Categorical(
            site_data["month_name"], categories=MONTHS, ordered=True
        )
        fig = px.box(site_data, x="month_name", y="precipitation_sum",
                     title=f"Q3: Daily Rainfall Variability ({site})",
                     labels={"month_name": "Month", "precipitation_sum": "Daily Rainfall (mm)"})
        return fig
    return go.Figure()

def chart_q4(summary):
    if summary.empty: return go.Figure()
    tex = summary.set_index("site")[["sand", "silt", "clay"]].dropna()
    if not tex.empty:
        tex = tex.div(tex.sum(axis=1), axis=0).mul(100).sort_values("clay")
        fig = px.bar(tex, orientation='h', title="Q4: Topsoil Texture", labels={'value': 'Percentage', 'variable': 'Texture'}, barmode='stack')
        return fig
    return go.Figure()

def chart_q5(summary):
    if summary.empty: return go.Figure()
    s = summary.dropna(subset=["clay", "soc"])
    fig = go.Figure()
    if not s.empty:
        fig.add_scatter(
            x=s["clay"], y=s["water_balance_mm"], mode="markers+text", text=s["site"],
            marker=dict(size=14 + 26 * s["soc"] / s["soc"].max()),   # bubble size = SOC
            name="Sites"
        )
        if len(s) >= 5:                                  # least-squares trend line
            slope, intercept = np.polyfit(s["clay"], s["water_balance_mm"], 1)
            r = np.corrcoef(s["clay"], s["water_balance_mm"])[0, 1]
            xs = np.array([s["clay"].min(), s["clay"].max()])
            fig.add_scatter(x=xs, y=slope * xs + intercept, mode="lines",
                            name=f"Linear fit (r = {r:.2f}, n = {len(s)})")
    fig.add_hline(y=0, annotation_text="rainfall = ET0")
    fig.update_layout(title="Q5: Soil vs Water Stress", xaxis_title="Clay %", yaxis_title="Water Balance (mm)")
    return fig

def chart_q6(summary):
    if summary.empty: return go.Figure()
    s = summary.dropna(subset=["soc", "rain_mm", "lat", "lon"])
    if s.empty: return go.Figure()
    fig = px.scatter_map(
        s, lat="lat", lon="lon",
        hover_name="site",
        hover_data={"rain_mm": True, "soc": True, "lat": False, "lon": False},
        map_style="carto-positron",
        color="soc",
        size="rain_mm",
        size_max=35,
        zoom=5,
        title="Q6: Sites — colour = SOC (g/kg), size = annual rainfall",
        labels={"soc": "SOC (g/kg)", "rain_mm": "Rainfall (mm)"},
        color_continuous_scale="YlOrBr",   # sequential: light-yellow → dark-brown
    )
    return fig


# 8. Pipeline and page
def main():
    st.title("Integrating APIs: Soil and Weather Data")
    st.write("Inputs, request, response, parsing, joining, analysis — one step at a time.")
    
    st.header("Step 2: Inputs")
    chosen = st.multiselect("Sites", SITES["site"].tolist(), default=SITES["site"].tolist()[:3])
    start = st.date_input("Start date", date(2025, 1, 1))
    end = st.date_input("End date", date(2025, 12, 31))
    fetch = st.button("Run the integration", type="primary")

    sites = SITES[SITES["site"].isin(chosen)].reset_index(drop=True)

    if fetch:
        if len(sites) == 0:
            st.error("Please select at least one site.")
            return
        if start > end:
            st.error("Start date must be before or on the end date.")
            return

        st.header("Step 3 & 4: Requests & Responses")
        
        weather_req = build_weather_request(sites, start, end)
        st.write("Weather Request URL:")
        st.code(weather_req["full_url"])
        
        with st.spinner("Fetching Weather..."):
            weather_res = send(weather_req)
            st.write(f"Weather Status: {weather_res['status']}, From Cache: {weather_res['from_cache']}")
        
        soil_reqs = [build_soil_request(row.site, row.lat, row.lon) for _, row in sites.iterrows()]
        soil_res = []
        
        with st.spinner("Fetching Soil Data..."):
            for i, req in enumerate(soil_reqs):
                try:
                    res = send(req)
                except requests.RequestException as exc:
                    st.error(f"SoilGrids failed for {req['label']}: {exc}. The SoilGrids REST API is a beta service and is sometimes paused. Try again later.")
                    continue
                soil_res.append(res)
                if not res["from_cache"] and i < len(soil_reqs) - 1:
                    time.sleep(SOILGRIDS_PAUSE_S)
        
        st.write("Soil Requests Status:")
        soil_status_df = pd.DataFrame([{"Site": r["label"], "Status": res.get("status", "Error"), "Cached": res.get("from_cache", False)} for r, res in zip(soil_reqs, soil_res)])
        st.dataframe(soil_status_df)
        
        st.header("Step 5: Parse JSON")
        weather_df = parse_weather(weather_res["data"], sites)
        st.write("Parsed Weather Data Sample:")
        st.dataframe(weather_df.head())
        
        soil_long_dfs = []
        for i, res in enumerate(soil_res):
            soil_long_dfs.append(parse_soil(res["data"], sites.iloc[i]["site"]))
        
        if soil_long_dfs:
            soil_long_df = pd.concat(soil_long_dfs, ignore_index=True)
            st.write("Soil Long Data (Audit Table):")
            st.dataframe(soil_long_df)
            
            soil_wide_df = soil_table(soil_long_df, sites)
            st.write("Soil Wide Data:")
            st.dataframe(soil_wide_df)
            
            missing = soil_wide_df.loc[soil_wide_df["clay"].isna(), "site"].tolist()
            if missing:
                st.warning(f"SoilGrids returned null for: {', '.join(missing)}. The map has no value at that exact point (water, a built-up area, or a gap in the map). The request still succeeded; try moving the point slightly.")
        
            st.header("Step 6: Integrate")
            daily, summary = integrate(weather_df, soil_wide_df)
            
            st.write(f"Joined Daily Records: {len(daily)} rows")
            st.write(f"Summary Records: {len(summary)} rows")
            
            st.header("Step 7: Charts")
            if len(sites) > 0:
                site_to_plot = st.selectbox("Select site for Q1-Q3", sites["site"].tolist())
                st.plotly_chart(chart_q1(daily, site_to_plot), width='stretch')
                st.plotly_chart(chart_q2(daily, site_to_plot), width='stretch')
                st.plotly_chart(chart_q3(daily, site_to_plot), width='stretch')
            
            st.plotly_chart(chart_q4(summary), width='stretch')
            st.plotly_chart(chart_q5(summary), width='stretch')
            st.plotly_chart(chart_q6(summary), width='stretch')
            
            st.header("Step 8: Export")
            b1, b2, _ = st.columns([1, 1, 2])
            b1.download_button("Download site summary (CSV)", summary.to_csv(index=False),
                               "site_summary.csv", "text/csv", width="stretch")
            if "month" in daily.columns:
                daily_export = daily.drop(columns="month")
            else:
                daily_export = daily
            b2.download_button("Download daily records (CSV)",
                               daily_export.to_csv(index=False),
                               "integrated_daily.csv", "text/csv", width="stretch")
            
            SOURCE_NOTE = (f"Sources: SoilGrids 2.0 (ISRIC, CC BY 4.0), {SOIL_DEPTH} mean; "
                           "Open-Meteo Historical Weather API (CC BY 4.0).")
            st.caption(SOURCE_NOTE)

if __name__ == "__main__":
    main()
