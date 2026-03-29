import re
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Optional

import requests
from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Visa Bulletin Forecast",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_URL = "https://travel.state.gov"
VISA_BULLETIN_INDEX = (
    f"{BASE_URL}/content/travel/en/legal/visa-law0/visa-bulletin.html"
)

FAMILY_CATEGORIES = ["F1", "F2A", "F2B", "F3", "F4"]
EMPLOYMENT_CATEGORIES = ["EB1", "EB2", "EB3", "EB4", "EB5"]
ALL_CATEGORIES = FAMILY_CATEGORIES + EMPLOYMENT_CATEGORIES

CHARGEABILITY_REGIONS = {
    "All / Rest of World": "all",
    "China (Mainland)": "china_mainland",
    "India": "india",
    "Mexico": "mexico",
    "Philippines": "philippines",
}

CATEGORY_LABELS = {
    "F1": "F1 — Unmarried Sons/Daughters of U.S. Citizens",
    "F2A": "F2A — Spouses/Children of Permanent Residents",
    "F2B": "F2B — Unmarried Sons/Daughters (21+) of Permanent Residents",
    "F3": "F3 — Married Sons/Daughters of U.S. Citizens",
    "F4": "F4 — Brothers/Sisters of Adult U.S. Citizens",
    "EB1": "EB1 — Priority Workers",
    "EB2": "EB2 — Advanced Degree / Exceptional Ability",
    "EB3": "EB3 — Skilled Workers / Professionals",
    "EB4": "EB4 — Special Immigrants",
    "EB5": "EB5 — Immigrant Investors",
}

MONTH_MAP = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}


# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap');

    .stApp { font-family: 'DM Sans', sans-serif; }

    .hero-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #0f172a 100%);
        padding: 2.5rem 2rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        border: 1px solid rgba(59, 130, 246, 0.2);
    }
    .hero-header h1 {
        color: #f8fafc;
        font-size: 2rem;
        font-weight: 700;
        margin: 0 0 0.5rem 0;
        letter-spacing: -0.02em;
    }
    .hero-header p {
        color: #94a3b8;
        font-size: 1.05rem;
        margin: 0;
    }

    .metric-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.25rem;
        text-align: center;
    }
    .metric-card .label {
        font-size: 0.8rem;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 500;
    }
    .metric-card .value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #0f172a;
        margin-top: 0.25rem;
    }

    .forecast-box {
        background: linear-gradient(135deg, #ecfdf5, #f0fdf4);
        border: 1px solid #86efac;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    .forecast-box h3 { color: #166534; margin-top: 0; }

    .retro-box {
        background: linear-gradient(135deg, #fef2f2, #fff7ed);
        border: 1px solid #fca5a5;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    .retro-box h3 { color: #991b1b; margin-top: 0; }

    .current-box {
        background: linear-gradient(135deg, #eff6ff, #e0f2fe);
        border: 1px solid #93c5fd;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    .current-box h3 { color: #1e40af; margin-top: 0; }

    div[data-testid="stSidebar"] {
        background: #f8fafc;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Scraper (cached)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_bulletin_links(count=13):
    session = requests.Session()
    session.headers["User-Agent"] = (
        "Mozilla/5.0 (compatible; VisaForecast/1.0)"
    )
    resp = session.get(VISA_BULLETIN_INDEX, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    bulletins = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        match = re.search(
            r"visa-bulletin-for-(\w+)-(\d{4})", href, re.IGNORECASE
        )
        if match:
            month_name = match.group(1).lower()
            year = int(match.group(2))
            if month_name in MONTH_MAP:
                url = href if href.startswith("http") else BASE_URL + href
                bulletins.append({
                    "month": month_name,
                    "month_num": MONTH_MAP[month_name],
                    "year": year,
                    "url": url,
                })

    seen = set()
    unique = []
    for b in bulletins:
        key = (b["year"], b["month_num"])
        if key not in seen:
            seen.add(key)
            unique.append(b)
    unique.sort(key=lambda x: (x["year"], x["month_num"]), reverse=True)
    return unique[:count]


def parse_cutoff_date(raw: str) -> Optional[datetime]:
    raw = raw.strip().upper()
    if raw in ("C", "CURRENT", ""):
        return datetime.today()
    if raw in ("U", "UNAVAILABLE"):
        return None
    for fmt in ("%d%b%y", "%d%b%Y", "%d-%b-%y", "%d-%b-%Y",
                 "%b %d, %Y", "%B %d, %Y", "%d %b %Y"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


@st.cache_data(ttl=3600, show_spinner=False)
def parse_bulletin_page(url: str) -> dict:
    session = requests.Session()
    session.headers["User-Agent"] = (
        "Mozilla/5.0 (compatible; VisaForecast/1.0)"
    )
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    tables = soup.find_all("table")
    result = {"final_action": {}, "dates_for_filing": {}}

    for table in tables:
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue

        headers = [th.get_text(strip=True).lower()
                   for th in rows[0].find_all(["th", "td"])]

        preceding_text = ""
        prev = table.find_previous(["h2", "h3", "h4", "p", "strong"])
        if prev:
            preceding_text = prev.get_text(strip=True).lower()

        if "filing" in preceding_text:
            target = result["dates_for_filing"]
        else:
            target = result["final_action"]

        col_map = {}
        for i, h in enumerate(headers):
            if i == 0:
                continue
            if "china" in h:
                col_map[i] = "china_mainland"
            elif "india" in h:
                col_map[i] = "india"
            elif "mexico" in h:
                col_map[i] = "mexico"
            elif "philippines" in h:
                col_map[i] = "philippines"
            elif "all" in h or "world" in h or "other" in h:
                col_map[i] = "all"

        if not col_map:
            continue

        for row in rows[1:]:
            cells = row.find_all(["th", "td"])
            if not cells:
                continue
            cat_text = cells[0].get_text(strip=True).upper()
            cat_text = re.sub(r"[^A-Z0-9_]", "", cat_text)

            cat_key = None
            for cat in ALL_CATEGORIES:
                if cat.replace("_", "") in cat_text.replace("_", ""):
                    cat_key = cat
                    break
            if cat_key is None:
                for cat in ALL_CATEGORIES:
                    if cat_text.startswith(cat.replace("_", "")):
                        cat_key = cat
                        break
            if cat_key is None:
                continue

            if cat_key not in target:
                target[cat_key] = {}

            for col_idx, region in col_map.items():
                if col_idx < len(cells):
                    val = cells[col_idx].get_text(strip=True)
                    target[cat_key][region] = val

    return result


def fetch_all_bulletins(months=13):
    links = fetch_bulletin_links(count=months)
    records = []
    progress = st.progress(0, text="Fetching visa bulletins...")

    for i, link in enumerate(links):
        bulletin_date = datetime(link["year"], link["month_num"], 1)
        progress.progress(
            (i + 1) / len(links),
            text=f"Fetching {link['month'].title()} {link['year']}..."
        )
        try:
            data = parse_bulletin_page(link["url"])
        except Exception:
            continue

        for table_type, categories in data.items():
            for category, regions in categories.items():
                for region, date_str in regions.items():
                    parsed = parse_cutoff_date(date_str)
                    records.append({
                        "bulletin_date": bulletin_date,
                        "table_type": table_type,
                        "category": category,
                        "region": region,
                        "cutoff_raw": date_str,
                        "cutoff_date": parsed,
                    })

    progress.empty()
    df = pd.DataFrame(records)
    if not df.empty:
        df.sort_values(["category", "region", "bulletin_date"], inplace=True)
        df.reset_index(drop=True, inplace=True)
    return df


# ---------------------------------------------------------------------------
# Forecasting
# ---------------------------------------------------------------------------

def compute_movement(df, category, region, table_type="final_action"):
    mask = (
        (df["category"] == category)
        & (df["region"] == region)
        & (df["table_type"] == table_type)
        & (df["cutoff_date"].notna())
    )
    subset = df.loc[mask].copy()
    if subset.empty:
        return pd.DataFrame()
    subset.sort_values("bulletin_date", inplace=True)
    subset["prev_cutoff"] = subset["cutoff_date"].shift(1)
    subset["movement_days"] = (
        subset["cutoff_date"] - subset["prev_cutoff"]
    ).dt.days
    subset.dropna(subset=["movement_days"], inplace=True)
    return subset


def forecast(df, category, region, priority_date,
             table_type="final_action", confidence=0.80):
    movement = compute_movement(df, category, region, table_type)
    if movement.empty:
        return {"error": "Insufficient data for this category/region."}

    latest = movement.iloc[-1]
    latest_cutoff = latest["cutoff_date"]
    latest_bulletin = latest["bulletin_date"]

    days_remaining = (priority_date - latest_cutoff).days
    if days_remaining <= 0:
        return {
            "status": "CURRENT",
            "latest_cutoff": latest_cutoff,
            "priority_date": priority_date,
        }

    moves = movement["movement_days"].values
    avg_move = float(np.mean(moves))
    std_move = float(np.std(moves, ddof=1)) if len(moves) > 1 else 0
    median_move = float(np.median(moves))

    if avg_move <= 0:
        return {
            "status": "RETROGRESSED",
            "avg_monthly_movement_days": round(avg_move, 1),
            "latest_cutoff": latest_cutoff,
        }

    months_est = days_remaining / avg_move
    projected_date = latest_bulletin + timedelta(days=months_est * 30.44)

    z_map = {0.80: 1.28, 0.90: 1.645, 0.95: 1.96}
    z = z_map.get(confidence, 1.28)

    if std_move > 0:
        opt_move = avg_move + z * std_move
        months_opt = days_remaining / opt_move
        date_early = latest_bulletin + timedelta(days=months_opt * 30.44)

        pess_move = max(avg_move - z * std_move, avg_move * 0.25)
        months_pess = days_remaining / pess_move
        date_late = latest_bulletin + timedelta(days=months_pess * 30.44)
    else:
        date_early = projected_date - timedelta(days=60)
        date_late = projected_date + timedelta(days=120)

    nvc_min, nvc_max = 60, 180
    interview_early = date_early + timedelta(days=nvc_min)
    interview_late = date_late + timedelta(days=nvc_max)

    return {
        "status": "PROJECTED",
        "priority_date": priority_date,
        "latest_cutoff": latest_cutoff,
        "latest_bulletin": latest_bulletin,
        "days_remaining": days_remaining,
        "avg_move": round(avg_move, 1),
        "median_move": round(median_move, 1),
        "std_move": round(std_move, 1),
        "data_points": len(moves),
        "projected_date": projected_date,
        "date_early": date_early,
        "date_late": date_late,
        "interview_early": interview_early,
        "interview_late": interview_late,
        "confidence": confidence,
    }


# ---------------------------------------------------------------------------
# Chart
# ---------------------------------------------------------------------------

def build_chart(movement_df, forecast_result, category, region):
    fig = go.Figure()

    # Historical cutoff line
    fig.add_trace(go.Scatter(
        x=movement_df["bulletin_date"],
        y=movement_df["cutoff_date"],
        mode="lines+markers",
        name="Historical Cutoff Date",
        line=dict(color="#2563eb", width=3),
        marker=dict(size=7),
    ))

    if forecast_result.get("status") == "PROJECTED":
        pd_date = forecast_result["priority_date"]

        # Priority date line
        fig.add_hline(
            y=pd_date, line_dash="dash", line_color="#dc2626",
            annotation_text=f"Your Priority Date: {pd_date.strftime('%Y-%m-%d')}",
            annotation_position="top left",
            annotation_font_color="#dc2626",
        )

        # Projected point
        fig.add_trace(go.Scatter(
            x=[forecast_result["projected_date"]],
            y=[pd_date],
            mode="markers",
            name="Projected Current Date",
            marker=dict(color="#16a34a", size=14, symbol="star"),
        ))

        # Interview window
        fig.add_vrect(
            x0=forecast_result["interview_early"],
            x1=forecast_result["interview_late"],
            fillcolor="rgba(22, 163, 74, 0.1)",
            line_width=0,
            annotation_text="Interview Window",
            annotation_position="top left",
            annotation_font_color="#166534",
        )

    fig.update_layout(
        title=dict(
            text=(f"Cutoff Date Trend & Forecast<br>"
                  f"<sub>{CATEGORY_LABELS.get(category, category)} · "
                  f"{region.replace('_', ' ').title()}</sub>"),
            font=dict(size=18),
        ),
        xaxis_title="Bulletin Month",
        yaxis_title="Cutoff / Priority Date",
        template="plotly_white",
        height=480,
        margin=dict(l=60, r=30, t=80, b=50),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="right", x=1,
        ),
    )

    return fig


# ---------------------------------------------------------------------------
# App Layout
# ---------------------------------------------------------------------------

# Header
st.markdown("""
<div class="hero-header">
    <h1>🌐 Visa Bulletin Forecast</h1>
    <p>Track U.S. Department of State cutoff dates and forecast your consulate interview window</p>
</div>
""", unsafe_allow_html=True)

# Sidebar inputs
with st.sidebar:
    st.markdown("### ⚙️ Configuration")

    cat_type = st.radio(
        "Category Type",
        ["Family-Based", "Employment-Based"],
        horizontal=True,
    )

    cats = FAMILY_CATEGORIES if cat_type == "Family-Based" else EMPLOYMENT_CATEGORIES
    category = st.selectbox(
        "Preference Category",
        cats,
        format_func=lambda c: CATEGORY_LABELS.get(c, c),
    )

    region_label = st.selectbox("Chargeability Region", list(CHARGEABILITY_REGIONS.keys()))
    region = CHARGEABILITY_REGIONS[region_label]

    table_type = st.selectbox(
        "Chart Type",
        ["final_action", "dates_for_filing"],
        format_func=lambda t: "Final Action Dates" if t == "final_action"
                              else "Dates for Filing",
    )

    months = st.slider("Months of History", 6, 36, 13)

    st.markdown("---")
    st.markdown("### 📅 Your Case")

    has_pd = st.checkbox("I have a priority date", value=True)
    priority_date = None
    if has_pd:
        priority_date = st.date_input(
            "Priority Date",
            value=datetime(2021, 6, 1),
            min_value=datetime(2000, 1, 1),
            max_value=datetime.today(),
        )

    confidence = st.select_slider(
        "Confidence Level",
        options=[0.80, 0.90, 0.95],
        value=0.80,
        format_func=lambda x: f"{x:.0%}",
    )

    run = st.button("🔍  Run Forecast", type="primary", use_container_width=True)

    st.markdown("---")
    st.caption(
        "Data sourced from [travel.state.gov]"
        "(https://travel.state.gov/content/travel/en/legal/"
        "visa-law0/visa-bulletin.html). Forecasts are statistical "
        "estimates — not legal advice."
    )


# ---------------------------------------------------------------------------
# Main Content
# ---------------------------------------------------------------------------

if run:
    with st.spinner("Fetching visa bulletin data from the Department of State..."):
        df = fetch_all_bulletins(months=months)

    if df.empty:
        st.error("Could not retrieve bulletin data. Please try again later.")
        st.stop()

    st.success(
        f"Loaded **{df['bulletin_date'].nunique()}** bulletins with "
        f"**{len(df):,}** data points."
    )

    # Movement table
    movement = compute_movement(df, category, region, table_type)

    if movement.empty:
        st.warning(
            f"No data found for **{category}** / **{region_label}** / "
            f"**{table_type}**. Try a different combination."
        )
        st.stop()

    # Tabs
    tab_chart, tab_table, tab_download = st.tabs([
        "📈 Chart & Forecast", "📊 Movement Table", "💾 Download"
    ])

    with tab_chart:
        fc = None
        if priority_date:
            pd_dt = datetime.combine(priority_date, datetime.min.time())
            fc = forecast(df, category, region, pd_dt, table_type, confidence)

        fig = build_chart(movement, fc or {}, category, region)
        st.plotly_chart(fig, use_container_width=True)

        if fc:
            if fc["status"] == "CURRENT":
                st.markdown("""
                <div class="current-box">
                    <h3>✅ Your priority date is CURRENT</h3>
                    <p>Your case is eligible for processing. Expect NVC to
                    schedule your consulate interview within 2–6 months,
                    depending on embassy workload.</p>
                </div>
                """, unsafe_allow_html=True)

            elif fc["status"] == "RETROGRESSED":
                st.markdown(f"""
                <div class="retro-box">
                    <h3>⚠️ Category Retrogressed / Stalled</h3>
                    <p>Average monthly movement is
                    <strong>{fc['avg_monthly_movement_days']} days</strong>
                    (negative or zero). Reliable forecasting is not possible
                    while the category is retrogressing.</p>
                </div>
                """, unsafe_allow_html=True)

            elif fc["status"] == "PROJECTED":
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="label">Days to Current</div>
                        <div class="value">{fc['days_remaining']:,}</div>
                    </div>""", unsafe_allow_html=True)
                with col2:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="label">Avg Movement / Mo</div>
                        <div class="value">{fc['avg_move']} days</div>
                    </div>""", unsafe_allow_html=True)
                with col3:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="label">Est. Current By</div>
                        <div class="value">{fc['projected_date'].strftime('%b %Y')}</div>
                    </div>""", unsafe_allow_html=True)
                with col4:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="label">Interview Window</div>
                        <div class="value">{fc['interview_early'].strftime('%b %Y')} – {fc['interview_late'].strftime('%b %Y')}</div>
                    </div>""", unsafe_allow_html=True)

                st.markdown(f"""
                <div class="forecast-box">
                    <h3>📅 Projected Interview Window</h3>
                    <p>Based on <strong>{fc['data_points']}</strong> months of data
                    at <strong>{confidence:.0%}</strong> confidence:</p>
                    <ul>
                        <li><strong>Become current:</strong>
                            {fc['date_early'].strftime('%b %d, %Y')} –
                            {fc['date_late'].strftime('%b %d, %Y')}</li>
                        <li><strong>Interview scheduling:</strong>
                            {fc['interview_early'].strftime('%b %d, %Y')} –
                            {fc['interview_late'].strftime('%b %d, %Y')}</li>
                    </ul>
                    <p style="font-size:0.85rem; color:#4b5563;">
                    Includes NVC processing buffer of 2–6 months after becoming
                    current. Actual timing depends on embassy capacity and
                    case completeness.</p>
                </div>
                """, unsafe_allow_html=True)

    with tab_table:
        display = movement[[
            "bulletin_date", "cutoff_date", "cutoff_raw", "movement_days"
        ]].copy()
        display["bulletin_date"] = display["bulletin_date"].dt.strftime("%b %Y")
        display["cutoff_date"] = display["cutoff_date"].dt.strftime("%Y-%m-%d")
        display.columns = ["Bulletin", "Cutoff Date", "Raw", "Movement (days)"]
        st.dataframe(display, use_container_width=True, hide_index=True)

        avg = movement["movement_days"].mean()
        med = movement["movement_days"].median()
        std = movement["movement_days"].std()
        st.markdown(
            f"**Stats:** Mean = {avg:.1f} days/mo · "
            f"Median = {med:.1f} · Std Dev = {std:.1f}"
        )

    with tab_download:
        csv = df.to_csv(index=False)
        st.download_button(
            "⬇️  Download Full Bulletin Data (CSV)",
            csv, "visa_bulletin_data.csv", "text/csv",
            use_container_width=True,
        )

        if priority_date and fc and fc.get("status") == "PROJECTED":
            import json
            st.download_button(
                "⬇️  Download Forecast (JSON)",
                json.dumps({k: str(v) for k, v in fc.items()}, indent=2),
                "visa_forecast.json", "application/json",
                use_container_width=True,
            )

else:
    # Landing state
    st.markdown("""
    ### How It Works

    1. **Configure** your visa category and chargeability region in the sidebar
    2. **Enter** your priority date
    3. **Click Run** to fetch live data from the Department of State
    4. **Review** the cutoff date trend chart and your projected interview window

    The tool analyzes month-over-month movement in the Visa Bulletin's cutoff
    dates and projects forward using a statistical model with confidence
    intervals. An NVC processing buffer is added to estimate the actual
    consulate interview scheduling window.
    """)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class="metric-card">
            <div class="label">Data Source</div>
            <div class="value">travel.state.gov</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="metric-card">
            <div class="label">Categories</div>
            <div class="value">10 (F + EB)</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="metric-card">
            <div class="label">Regions</div>
            <div class="value">5</div>
        </div>""", unsafe_allow_html=True)
