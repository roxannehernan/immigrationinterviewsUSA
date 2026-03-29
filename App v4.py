import re
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from bs4 import BeautifulSoup

st.set_page_config(
    page_title="Visa Bulletin Forecast",
    page_icon="📍",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_URL = "https://travel.state.gov"
VISA_BULLETIN_INDEX = f"{BASE_URL}/content/travel/en/legal/visa-law0/visa-bulletin.html"
FAMILY_CATEGORIES = ["F1", "F2A", "F2B", "F3", "F4"]
EMPLOYMENT_CATEGORIES = ["EB1", "EB2", "EB3", "EB4", "EB5"]
IR_CATEGORIES = ["IR1", "CR1", "IR2", "IR5", "K1"]
ALL_CATEGORIES = FAMILY_CATEGORIES + EMPLOYMENT_CATEGORIES

CHARGEABILITY_REGIONS = {
    "Rest of World": "all",
    "China": "china_mainland",
    "India": "india",
    "Mexico": "mexico",
    "Philippines": "philippines",
    "El Salvador": "el_salvador",
    "Guatemala": "guatemala",
    "Honduras": "honduras",
    "Vietnam": "vietnam",
    "South Korea": "korea",
    "Brazil": "brazil",
    "Bangladesh": "bangladesh",
    "Pakistan": "pakistan",
}

CATEGORY_LABELS = {
    "F1": "F1 · Unmarried Sons and Daughters of U.S. Citizens",
    "F2A": "F2A · Spouses and Children of Permanent Residents",
    "F2B": "F2B · Unmarried Adult Sons and Daughters of Permanent Residents",
    "F3": "F3 · Married Sons and Daughters of U.S. Citizens",
    "F4": "F4 · Brothers and Sisters of Adult U.S. Citizens",
    "EB1": "EB1 · Priority Workers",
    "EB2": "EB2 · Advanced Degree or Exceptional Ability",
    "EB3": "EB3 · Skilled Workers and Professionals",
    "EB4": "EB4 · Special Immigrants",
    "EB5": "EB5 · Investors",
    "IR1": "IR1 · Spouse of a U.S. Citizen",
    "CR1": "CR1 · Spouse of a U.S. Citizen under 2 years",
    "IR2": "IR2 · Child of a U.S. Citizen",
    "IR5": "IR5 · Parent of a U.S. Citizen",
    "K1": "K1 · Fiancé(e) of a U.S. Citizen",
}

CONSULATES = {
    "india": [
        ("Mumbai", "C-49 BKC", "90–180d", 19.0760, 72.8777),
        ("New Delhi", "Shantipath", "60–120d", 28.6139, 77.2090),
        ("Chennai", "220 Anna Salai", "60–120d", 13.0827, 80.2707),
        ("Hyderabad", "Paigah Palace", "90–150d", 17.3850, 78.4867),
        ("Kolkata", "Ho Chi Minh Sarani", "30–60d", 22.5726, 88.3639),
    ],
    "china_mainland": [
        ("Guangzhou", "Shamian Island", "60–90d", 23.1291, 113.2644),
        ("Beijing", "An Jia Lou Rd", "45–75d", 39.9042, 116.4074),
        ("Shanghai", "Huaihai Middle Rd", "30–60d", 31.2304, 121.4737),
    ],
    "mexico": [
        ("Ciudad Juárez", "Paseo de la Victoria", "60–120d", 31.6904, -106.4245),
        ("Mexico City", "Paseo de la Reforma", "120–240d", 19.4326, -99.1332),
        ("Guadalajara", "Progreso 175", "60–90d", 20.6597, -103.3496),
        ("Monterrey", "Av. Alfonso Reyes", "60–90d", 25.6866, -100.3161),
        ("Tijuana", "Mesa de Otay", "60–90d", 32.5149, -117.0382),
    ],
    "philippines": [("Manila", "1201 Roxas Blvd", "90–180d", 14.5995, 120.9842)],
    "all": [
        ("London", "33 Nine Elms Ln", "30–60d", 51.5072, -0.1276),
        ("Frankfurt", "Gießener Str.", "30–45d", 50.1109, 8.6821),
        ("Montreal", "Sainte-Catherine", "30–60d", 45.5017, -73.5673),
        ("Sydney", "19-29 Martin Pl", "30–45d", -33.8688, 151.2093),
        ("Bangkok", "95 Wireless Rd", "45–90d", 13.7563, 100.5018),
        ("Santo Domingo", "Av. Colombia", "60–120d", 18.4861, -69.9312),
    ],
    "vietnam": [
        ("Ho Chi Minh City", "4 Le Duan Blvd", "60–120d", 10.8231, 106.6297),
        ("Hanoi", "7 Lang Ha St", "45–90d", 21.0278, 105.8342),
    ],
    "korea": [("Seoul", "188 Sejong-daero", "30–60d", 37.5665, 126.9780)],
    "brazil": [
        ("São Paulo", "Rua Henri Dunant", "60–120d", -23.5505, -46.6333),
        ("Rio de Janeiro", "Av. Pres. Wilson", "45–90d", -22.9068, -43.1729),
    ],
    "bangladesh": [("Dhaka", "Madani Ave", "90–180d", 23.8103, 90.4125)],
    "pakistan": [
        ("Islamabad", "Diplomatic Enclave", "90–180d", 33.6844, 73.0479),
        ("Karachi", "Mai Kolachi Rd", "60–120d", 24.8607, 67.0011),
    ],
    "el_salvador": [("San Salvador", "Blvd. Santa Elena", "60–120d", 13.6929, -89.2182)],
    "guatemala": [("Guatemala City", "Av. Reforma", "60–120d", 14.6349, -90.5069)],
    "honduras": [("Tegucigalpa", "Av. La Paz", "60–120d", 14.0723, -87.1921)],
}

MONTH_MAP = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

st.markdown(
    """
    <style>
    :root {
        --bg: #f6f3ee;
        --card: #fffdf9;
        --ink: #1f2937;
        --muted: #6b7280;
        --line: #e7e0d6;
        --accent: #7c5c3b;
        --accent-soft: #efe7db;
    }
    .stApp { background: var(--bg); color: var(--ink); }
    [data-testid="stSidebar"] { background: #fbf8f3; border-right: 1px solid var(--line); }
    .hero {
        padding: 1.1rem 1.2rem 0.8rem 1.2rem;
        border: 1px solid var(--line);
        background: linear-gradient(180deg, #fffdf9 0%, #f7f2eb 100%);
        border-radius: 18px;
        margin-bottom: 1rem;
    }
    .eyebrow { font-size: 0.78rem; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); }
    .hero h1 { margin: 0.25rem 0 0 0; font-size: 2.1rem; color: #1f2937; }
    .hero p { margin: 0.5rem 0 0 0; color: #4b5563; max-width: 900px; }
    .metric-card {
        background: var(--card);
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: 1rem;
        height: 100%;
        box-shadow: 0 2px 10px rgba(50,50,50,0.03);
    }
    .metric-label { color: var(--muted); font-size: 0.82rem; margin-bottom: 0.35rem; }
    .metric-value { font-size: 1.7rem; font-weight: 650; color: var(--ink); }
    .section-card {
        background: var(--card);
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: 0.6rem 0.9rem 0.3rem 0.9rem;
        margin-bottom: 1rem;
    }
    .map-note {
        background: #fffaf3;
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 0.8rem 0.9rem;
        color: #4b5563;
        margin-top: 0.4rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def metric_card(label: str, value: str):
    st.markdown(
        f"<div class='metric-card'><div class='metric-label'>{label}</div><div class='metric-value'>{value}</div></div>",
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_links(n=13):
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0"
    r = s.get(VISA_BULLETIN_INDEX, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    out = []
    for a in soup.find_all("a", href=True):
        m = re.search(r"visa-bulletin-for-(\w+)-(\d{4})", a["href"], re.I)
        if m and m.group(1).lower() in MONTH_MAP:
            url = a["href"] if a["href"].startswith("http") else BASE_URL + a["href"]
            out.append({"mn": m.group(1).lower(), "mi": MONTH_MAP[m.group(1).lower()], "yr": int(m.group(2)), "url": url})
    seen, unique = set(), []
    for b in out:
        key = (b["yr"], b["mi"])
        if key not in seen:
            seen.add(key)
            unique.append(b)
    unique.sort(key=lambda x: (x["yr"], x["mi"]), reverse=True)
    return unique[:n]


def parse_date(raw: str) -> Optional[datetime]:
    raw = raw.strip().upper()
    if raw in ("C", "CURRENT", ""):
        return datetime.today()
    if raw in ("U", "UNAVAILABLE"):
        return None
    for fmt in ("%d%b%y", "%d%b%Y", "%d-%b-%y", "%d-%b-%Y", "%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(raw, fmt)
        except Exception:
            pass
    return None


@st.cache_data(ttl=3600, show_spinner=False)
def parse_page(url: str):
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0"
    r = s.get(url, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    tables = soup.find_all("table")
    res = {"final_action": {}, "dates_for_filing": {}}

    for table in tables:
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue
        hdr = [h.get_text(strip=True).lower() for h in rows[0].find_all(["th", "td"])]
        prev = table.find_previous(["h2", "h3", "h4", "p", "strong"])
        target = res["dates_for_filing"] if prev and "filing" in prev.get_text(strip=True).lower() else res["final_action"]
        col_map = {}
        for i, h in enumerate(hdr):
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
            elif any(x in h for x in ["all", "world", "other"]):
                col_map[i] = "all"
        if not col_map:
            continue
        for row in rows[1:]:
            cells = row.find_all(["th", "td"])
            if not cells:
                continue
            cell_text = re.sub(r"[^A-Z0-9_]", "", cells[0].get_text(strip=True).upper())
            category = next((c for c in ALL_CATEGORIES if c.replace("_", "") in cell_text.replace("_", "")), None)
            if not category:
                continue
            if category not in target:
                target[category] = {}
            for ci, region in col_map.items():
                if ci < len(cells):
                    target[category][region] = cells[ci].get_text(strip=True)
    return res


def fetch_bulletins(n=13):
    links = fetch_links(n)
    records = []
    progress = st.progress(0, text="Loading recent bulletins")
    for i, lk in enumerate(links):
        bulletin_date = datetime(lk["yr"], lk["mi"], 1)
        progress.progress((i + 1) / len(links), text=f"Processing {lk['mn'].title()} {lk['yr']}")
        try:
            data = parse_page(lk["url"])
        except Exception:
            continue
        for table_type, categories in data.items():
            for category, regions in categories.items():
                for region, date_str in regions.items():
                    records.append(
                        {
                            "bulletin_date": bulletin_date,
                            "table_type": table_type,
                            "category": category,
                            "region": region,
                            "cutoff_raw": date_str,
                            "cutoff_date": parse_date(date_str),
                        }
                    )
    progress.empty()
    df = pd.DataFrame(records)
    if not df.empty:
        df.sort_values(["category", "region", "bulletin_date"], inplace=True)
    return df


def movement(df: pd.DataFrame, category: str, region: str, table_type: str) -> pd.DataFrame:
    mask = (
        (df["category"] == category)
        & (df["region"] == region)
        & (df["table_type"] == table_type)
        & (df["cutoff_date"].notna())
    )
    series = df.loc[mask].copy().sort_values("bulletin_date")
    series["prev"] = series["cutoff_date"].shift(1)
    series["move"] = (series["cutoff_date"] - series["prev"]).dt.days
    return series.dropna(subset=["move"])


def forecast(df: pd.DataFrame, category: str, region: str, priority_date: datetime, table_type: str, confidence: float):
    mv = movement(df, category, region, table_type)
    if mv.empty:
        return {"error": True}
    latest = mv.iloc[-1]
    last_cutoff = latest["cutoff_date"]
    last_bulletin = latest["bulletin_date"]
    days_remaining = (priority_date - last_cutoff).days
    if days_remaining <= 0:
        return {"status": "CURRENT"}

    moves = mv["move"].values
    avg_move = np.mean(moves)
    std_move = np.std(moves, ddof=1) if len(moves) > 1 else 0
    if avg_move <= 0:
        return {"status": "RETRO"}

    months_est = days_remaining / avg_move
    projected_current = last_bulletin + timedelta(days=months_est * 30.44)
    z_score = {0.8: 1.28, 0.9: 1.645, 0.95: 1.96}.get(confidence, 1.28)

    early_current = (
        last_bulletin + timedelta(days=(days_remaining / (avg_move + z_score * std_move)) * 30.44)
        if std_move > 0
        else projected_current - timedelta(days=60)
    )
    late_current = (
        last_bulletin + timedelta(days=(days_remaining / max(avg_move - z_score * std_move, avg_move * 0.25)) * 30.44)
        if std_move > 0
        else projected_current + timedelta(days=120)
    )

    return {
        "status": "OK",
        "days_remaining": days_remaining,
        "avg_move": round(avg_move, 1),
        "projected_current": projected_current,
        "current_early": early_current,
        "current_late": late_current,
        "interview_early": early_current + timedelta(days=60),
        "interview_late": late_current + timedelta(days=180),
        "samples": len(moves),
        "last_cutoff": last_cutoff,
        "last_bulletin": last_bulletin,
    }


def build_cutoff_trend_chart(mv: pd.DataFrame, priority_date: datetime, fc: dict):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=mv["bulletin_date"],
            y=mv["cutoff_date"],
            mode="lines+markers",
            name="Historical cutoff",
            line=dict(width=3, color="#7c5c3b"),
            marker=dict(size=7, color="#9b7b59"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[mv["bulletin_date"].min(), max(fc["current_late"], mv["bulletin_date"].max())],
            y=[priority_date, priority_date],
            mode="lines",
            name="Priority date",
            line=dict(width=2, dash="dash", color="#b45309"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[fc["current_early"], fc["projected_current"], fc["current_late"]],
            y=[priority_date, priority_date, priority_date],
            mode="markers+lines",
            name="Forecast window",
            line=dict(width=3, color="#c08a5b"),
            marker=dict(size=[8, 11, 8], color="#c08a5b"),
        )
    )
    fig.update_layout(
        title="Cutoff trend and forecast window",
        paper_bgcolor="#fffdf9",
        plot_bgcolor="#fffdf9",
        height=410,
        margin=dict(l=20, r=20, t=55, b=20),
        legend=dict(orientation="h", y=1.08, x=0),
    )
    return fig


def build_movement_bar_chart(mv: pd.DataFrame):
    chart = mv.copy()
    chart["month_label"] = chart["bulletin_date"].dt.strftime("%b %Y")
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=chart["month_label"],
            y=chart["move"],
            name="Monthly movement",
            marker_color="#b99a77",
            hovertemplate="%{x}<br>Movement: %{y} days<extra></extra>",
        )
    )
    fig.update_layout(
        title="Monthly movement in days",
        paper_bgcolor="#fffdf9",
        plot_bgcolor="#fffdf9",
        height=350,
        margin=dict(l=20, r=20, t=55, b=20),
        xaxis_title="",
        yaxis_title="Days",
    )
    return fig


def build_location_map(region_key: str, selected_post: Optional[str] = None):
    locations = CONSULATES.get(region_key, [])
    if not locations:
        return None
    df_map = pd.DataFrame(locations, columns=["city", "address", "wait", "lat", "lon"])
    df_map["size"] = np.where(df_map["city"].eq(selected_post), 16, 11)
    df_map["label"] = df_map["city"] + "<br>Wait: " + df_map["wait"]

    fig = go.Figure(
        go.Scattermap(
            lat=df_map["lat"],
            lon=df_map["lon"],
            mode="markers+text",
            marker=dict(size=df_map["size"], color="#7c5c3b"),
            text=df_map["city"],
            textposition="top right",
            customdata=np.stack([df_map["address"], df_map["wait"]], axis=-1),
            hovertemplate="<b>%{text}</b><br>%{customdata[0]}<br>Scheduling wait: %{customdata[1]}<extra></extra>",
            name="Posts",
        )
    )
    fig.update_layout(
        map=dict(style="open-street-map", zoom=1.5, center=dict(lat=float(df_map["lat"].mean()), lon=float(df_map["lon"].mean()))),
        margin=dict(l=10, r=10, t=10, b=10),
        height=420,
        paper_bgcolor="#fffdf9",
    )
    return fig


with st.sidebar:
    st.markdown("### Case setup")
    case_type = st.radio("Visa class", ["IR / CR", "Family", "Employment"], horizontal=True)
    is_ir = "IR" in case_type

    if is_ir:
        category = st.selectbox("Category", IR_CATEGORIES, format_func=lambda c: CATEGORY_LABELS.get(c, c))
    elif case_type == "Family":
        category = st.selectbox("Category", FAMILY_CATEGORIES, format_func=lambda c: CATEGORY_LABELS.get(c, c))
    else:
        category = st.selectbox("Category", EMPLOYMENT_CATEGORIES, format_func=lambda c: CATEGORY_LABELS.get(c, c))

    region_label = st.selectbox("Chargeability area", list(CHARGEABILITY_REGIONS.keys()))
    region = CHARGEABILITY_REGIONS[region_label]
    posts = CONSULATES.get(region, [])
    post_name = st.selectbox("Interview post", [p[0] for p in posts]) if posts else None
    selected_post = next((p for p in posts if p[0] == post_name), None)

    if not is_ir:
        table_type = st.segmented_control(
            "Bulletin table",
            options=["final_action", "dates_for_filing"],
            format_func=lambda t: "Final Action" if t == "final_action" else "Dates for Filing",
            default="final_action",
        )
        priority_date_input = st.date_input("Priority date", datetime(2022, 3, 15))
        confidence = st.select_slider("Confidence", options=[0.8, 0.9, 0.95], value=0.9, format_func=lambda x: f"{int(x*100)}%")
        history_months = st.slider("Bulletins to analyze", 6, 36, 16)

    run_button = st.button("Build forecast", use_container_width=True, type="primary")

st.markdown(
    """
    <div class='hero'>
        <div class='eyebrow'>Visa Bulletin Forecast</div>
        <h1>Cleaner projections for priority dates and interview locations</h1>
        <p>This version uses a softer editorial layout, a forecast window chart, a monthly movement graph, and a location map so the app feels more like a real decision tool and less like a generated demo.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if run_button:
    if is_ir:
        st.subheader(CATEGORY_LABELS.get(category, category))
        st.info("IR and CR visa categories are generally current, so there is no visa bulletin cutoff forecast to model.")
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            metric_card("I-130 petition", "6–14 mo")
        with m2:
            metric_card("NVC processing", "2–6 mo")
        with m3:
            metric_card("Interview", "1–3 mo")
        with m4:
            metric_card("Total estimate", "9–23 mo")

        left, right = st.columns([1.1, 1])
        with left:
            map_fig = build_location_map(region, post_name)
            if map_fig:
                st.plotly_chart(map_fig, use_container_width=True)
        with right:
            if selected_post:
                st.markdown(
                    f"""
                    <div class='map-note'>
                    <b>{selected_post[0]}</b><br>
                    {selected_post[1]}<br>
                    Typical scheduling wait: <b>{selected_post[2]}</b>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    else:
        df = fetch_bulletins(history_months)
        if df.empty:
            st.error("No bulletin data could be loaded.")
            st.stop()

        priority_date = datetime.combine(priority_date_input, datetime.min.time())
        fc = forecast(df, category, region, priority_date, table_type, confidence)
        if fc.get("error"):
            st.error("Not enough historical movement data for this selection.")
            st.stop()

        st.subheader(f"{region_label} · {CATEGORY_LABELS.get(category, category)}")

        if fc.get("status") == "CURRENT":
            st.success("Your selected priority date is already current based on the latest analyzed bulletin history.")
        elif fc.get("status") == "RETRO":
            st.warning("Recent movement is flat or retrogressed, so the app cannot produce a stable projection.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                metric_card("Days remaining", f"{fc['days_remaining']:,}")
            with c2:
                metric_card("Average movement", f"{fc['avg_move']} days / mo")
            with c3:
                metric_card("Estimated current", fc["projected_current"].strftime("%b %Y"))
            with c4:
                metric_card("Interview window", f"{fc['interview_early'].strftime('%b %Y')} – {fc['interview_late'].strftime('%b %Y')}")

            mv = movement(df, category, region, table_type)
            chart_col, map_col = st.columns([1.7, 1])
            with chart_col:
                st.markdown("<div class='section-card'>", unsafe_allow_html=True)
                st.plotly_chart(build_cutoff_trend_chart(mv, priority_date, fc), use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
            with map_col:
                st.markdown("<div class='section-card'>", unsafe_allow_html=True)
                map_fig = build_location_map(region, post_name)
                if map_fig:
                    st.plotly_chart(map_fig, use_container_width=True)
                if selected_post:
                    st.markdown(
                        f"""
                        <div class='map-note'>
                        <b>{selected_post[0]}</b><br>
                        {selected_post[1]}<br>
                        Scheduling wait: <b>{selected_post[2]}</b><br>
                        Forecasted interview range: <b>{fc['interview_early'].strftime('%b %Y')} to {fc['interview_late'].strftime('%b %Y')}</b>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                st.markdown("</div>", unsafe_allow_html=True)

            lower_col, upper_col = st.columns([1.1, 0.9])
            with lower_col:
                st.markdown("<div class='section-card'>", unsafe_allow_html=True)
                st.plotly_chart(build_movement_bar_chart(mv), use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
            with upper_col:
                st.markdown("<div class='section-card'>", unsafe_allow_html=True)
                summary = pd.DataFrame(
                    {
                        "Metric": [
                            "Last observed cutoff",
                            "Last bulletin month",
                            "Confidence level",
                            "Historical samples",
                            "Forecast current window",
                        ],
                        "Value": [
                            fc["last_cutoff"].strftime("%b %d, %Y"),
                            fc["last_bulletin"].strftime("%b %Y"),
                            f"{int(confidence*100)}%",
                            str(fc["samples"]),
                            f"{fc['current_early'].strftime('%b %Y')} – {fc['current_late'].strftime('%b %Y')}",
                        ],
                    }
                )
                st.dataframe(summary, hide_index=True, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

            with st.expander("Movement details"):
                details = mv[["bulletin_date", "cutoff_date", "move"]].rename(
                    columns={"bulletin_date": "Bulletin month", "cutoff_date": "Cutoff date", "move": "Movement days"}
                )
                st.dataframe(details, hide_index=True, use_container_width=True)

        st.download_button("Download data as CSV", df.to_csv(index=False), file_name="visa_bulletin_history.csv", mime="text/csv")
else:
    st.markdown("### Start with the panel on the left")
    st.write("Pick a category, region, post, and priority date, then build the forecast to see the redesigned charts and location map.")
