
import re
import json
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
    "🌍 Rest of World": "all",
    "🇨🇳 China": "china_mainland",
    "🇮🇳 India": "india",
    "🇲🇽 Mexico": "mexico",
    "🇵🇭 Philippines": "philippines",
    "🇸🇻 El Salvador": "el_salvador",
    "🇬🇹 Guatemala": "guatemala",
    "🇭🇳 Honduras": "honduras",
    "🇻🇳 Vietnam": "vietnam",
    "🇰🇷 South Korea": "korea",
    "🇧🇷 Brazil": "brazil",
    "🇧🇩 Bangladesh": "bangladesh",
    "🇵🇰 Pakistan": "pakistan",
}

CATEGORY_LABELS = {
    "F1": "F1 · Unmarried Sons and Daughters",
    "F2A": "F2A · Spouses and Children of Permanent Residents",
    "F2B": "F2B · Unmarried Adult Sons and Daughters",
    "F3": "F3 · Married Sons and Daughters",
    "F4": "F4 · Brothers and Sisters",
    "EB1": "EB1 · Priority Workers",
    "EB2": "EB2 · Advanced Degree",
    "EB3": "EB3 · Skilled Workers and Professionals",
    "EB4": "EB4 · Special Immigrants",
    "EB5": "EB5 · Investors",
    "IR1": "IR1 · Spouse of a U.S. Citizen",
    "CR1": "CR1 · Spouse under 2 years",
    "IR2": "IR2 · Child of a U.S. Citizen",
    "IR5": "IR5 · Parent of a U.S. Citizen",
    "K1": "K1 · Fiancé(e)",
}

CONSULATES = {
    "china_mainland": [
        {"id": "gz", "name": "Consulate Guangzhou", "city": "Guangzhou", "addr": "No. 1 Shamian South St", "lat": 23.1058, "lng": 113.2373, "note": "Primary IV post for China", "wait": "60–90 days", "flag": "🇨🇳"},
        {"id": "bj", "name": "Embassy Beijing", "city": "Beijing", "addr": "No. 55 An Jia Lou Rd", "lat": 39.9526, "lng": 116.4683, "note": "Limited IV processing", "wait": "45–75 days", "flag": "🇨🇳"},
        {"id": "sh", "name": "Consulate Shanghai", "city": "Shanghai", "addr": "1469 Huaihai Middle Rd", "lat": 31.2116, "lng": 121.4441, "note": "Non immigrant primarily", "wait": "30–60 days", "flag": "🇨🇳"},
    ],
    "india": [
        {"id": "mum", "name": "Consulate Mumbai", "city": "Mumbai", "addr": "C-49, G-Block, BKC", "lat": 19.0596, "lng": 72.8656, "note": "Highest volume IV post in India", "wait": "90–180 days", "flag": "🇮🇳"},
        {"id": "del", "name": "Embassy New Delhi", "city": "New Delhi", "addr": "Shantipath, Chanakyapuri", "lat": 28.5979, "lng": 77.1710, "note": "Full IV services", "wait": "60–120 days", "flag": "🇮🇳"},
        {"id": "che", "name": "Consulate Chennai", "city": "Chennai", "addr": "220 Anna Salai", "lat": 13.0604, "lng": 80.2497, "note": "High EB for South India", "wait": "60–120 days", "flag": "🇮🇳"},
        {"id": "hyd", "name": "Consulate Hyderabad", "city": "Hyderabad", "addr": "Paigah Palace", "lat": 17.4065, "lng": 78.4772, "note": "Tech corridor and high EB demand", "wait": "90–150 days", "flag": "🇮🇳"},
        {"id": "kol", "name": "Consulate Kolkata", "city": "Kolkata", "addr": "5/1 Ho Chi Minh Sarani", "lat": 22.5449, "lng": 88.3510, "note": "Eastern India", "wait": "30–60 days", "flag": "🇮🇳"},
    ],
    "mexico": [
        {"id": "cjs", "name": "Consulate Ciudad Juárez", "city": "Ciudad Juárez", "addr": "Paseo de la Victoria #3650", "lat": 31.6904, "lng": -106.4245, "note": "Highest IV volume worldwide", "wait": "60–120 days", "flag": "🇲🇽"},
        {"id": "cdmx", "name": "Embassy Mexico City", "city": "CDMX", "addr": "Paseo de la Reforma 305", "lat": 19.4276, "lng": -99.1677, "note": "Largest embassy in western hemisphere", "wait": "120–240 days", "flag": "🇲🇽"},
        {"id": "gdl", "name": "Consulate Guadalajara", "city": "Guadalajara", "addr": "Progreso 175", "lat": 20.6722, "lng": -103.3625, "note": "Western Mexico", "wait": "60–90 days", "flag": "🇲🇽"},
        {"id": "mty", "name": "Consulate Monterrey", "city": "Monterrey", "addr": "Av. Alfonso Reyes 150", "lat": 25.6714, "lng": -100.3091, "note": "Northeast Mexico", "wait": "60–90 days", "flag": "🇲🇽"},
        {"id": "tij", "name": "Consulate Tijuana", "city": "Tijuana", "addr": "Paseo de las Culturas", "lat": 32.5366, "lng": -116.9717, "note": "High volume border post", "wait": "60–90 days", "flag": "🇲🇽"},
    ],
    "philippines": [
        {"id": "mnl", "name": "Embassy Manila", "city": "Manila", "addr": "1201 Roxas Blvd", "lat": 14.5619, "lng": 120.9801, "note": "Busiest IV post worldwide", "wait": "90–180 days", "flag": "🇵🇭"},
    ],
    "el_salvador": [
        {"id": "ss", "name": "Embassy San Salvador", "city": "San Salvador", "addr": "Blvd. Santa Elena", "lat": 13.6664, "lng": -89.2530, "note": "Sole post", "wait": "60–120 days", "flag": "🇸🇻"},
    ],
    "guatemala": [
        {"id": "gua", "name": "Embassy Guatemala City", "city": "Guatemala City", "addr": "Av. Reforma 7-01", "lat": 14.5980, "lng": -90.5137, "note": "Sole post", "wait": "60–120 days", "flag": "🇬🇹"},
    ],
    "honduras": [
        {"id": "tgu", "name": "Embassy Tegucigalpa", "city": "Tegucigalpa", "addr": "Av. La Paz", "lat": 14.0910, "lng": -87.1963, "note": "Sole post", "wait": "60–120 days", "flag": "🇭🇳"},
    ],
    "vietnam": [
        {"id": "hcm", "name": "Consulate HCMC", "city": "Ho Chi Minh City", "addr": "4 Le Duan Blvd", "lat": 10.7816, "lng": 106.7010, "note": "Primary IV post", "wait": "60–120 days", "flag": "🇻🇳"},
        {"id": "han", "name": "Embassy Hanoi", "city": "Hanoi", "addr": "7 Lang Ha St", "lat": 21.0170, "lng": 105.8132, "note": "Full IV processing", "wait": "45–90 days", "flag": "🇻🇳"},
    ],
    "korea": [
        {"id": "sel", "name": "Embassy Seoul", "city": "Seoul", "addr": "188 Sejong-daero", "lat": 37.5661, "lng": 126.9747, "note": "Sole post", "wait": "30–60 days", "flag": "🇰🇷"},
    ],
    "brazil": [
        {"id": "sp", "name": "Consulate São Paulo", "city": "São Paulo", "addr": "Rua Henri Dunant 500", "lat": -23.6275, "lng": -46.6958, "note": "Highest volume in Brazil", "wait": "60–120 days", "flag": "🇧🇷"},
        {"id": "rio", "name": "Consulate Rio", "city": "Rio de Janeiro", "addr": "Av. Pres. Wilson 147", "lat": -22.9028, "lng": -43.1722, "note": "Full IV processing", "wait": "45–90 days", "flag": "🇧🇷"},
    ],
    "bangladesh": [
        {"id": "dhk", "name": "Embassy Dhaka", "city": "Dhaka", "addr": "Madani Ave", "lat": 23.8103, "lng": 90.4125, "note": "High family volume", "wait": "90–180 days", "flag": "🇧🇩"},
    ],
    "pakistan": [
        {"id": "isl", "name": "Embassy Islamabad", "city": "Islamabad", "addr": "Diplomatic Enclave", "lat": 33.7215, "lng": 73.0884, "note": "Primary post", "wait": "90–180 days", "flag": "🇵🇰"},
        {"id": "khi", "name": "Consulate Karachi", "city": "Karachi", "addr": "Mai Kolachi Rd", "lat": 24.8465, "lng": 67.0195, "note": "Sindh and Balochistan", "wait": "60–120 days", "flag": "🇵🇰"},
    ],
    "all": [
        {"id": "lon", "name": "Embassy London", "city": "London", "addr": "33 Nine Elms Ln", "lat": 51.48, "lng": -0.12, "note": "Major UK and EU post", "wait": "30–60 days", "flag": "🇬🇧"},
        {"id": "fra", "name": "Consulate Frankfurt", "city": "Frankfurt", "addr": "Gießener Str. 30", "lat": 50.12, "lng": 8.68, "note": "Germany and high EB demand", "wait": "30–45 days", "flag": "🇩🇪"},
        {"id": "mtl", "name": "Consulate Montreal", "city": "Montreal", "addr": "Sainte-Catherine O", "lat": 45.50, "lng": -73.57, "note": "Primary Canadian IV post", "wait": "30–60 days", "flag": "🇨🇦"},
        {"id": "syd", "name": "Consulate Sydney", "city": "Sydney", "addr": "19-29 Martin Pl", "lat": -33.87, "lng": 151.21, "note": "AU, NZ and Pacific", "wait": "30–45 days", "flag": "🇦🇺"},
        {"id": "acc", "name": "Embassy Accra", "city": "Accra", "addr": "Fourth Circular Rd", "lat": 5.57, "lng": -0.18, "note": "West Africa hub", "wait": "60–120 days", "flag": "🇬🇭"},
        {"id": "nbo", "name": "Embassy Nairobi", "city": "Nairobi", "addr": "United Nations Ave", "lat": -1.24, "lng": 36.81, "note": "East Africa hub", "wait": "60–90 days", "flag": "🇰🇪"},
        {"id": "dxb", "name": "Consulate Dubai", "city": "Dubai", "addr": "Al Seef Rd", "lat": 25.26, "lng": 55.30, "note": "UAE", "wait": "30–60 days", "flag": "🇦🇪"},
        {"id": "bkk", "name": "Embassy Bangkok", "city": "Bangkok", "addr": "95 Wireless Rd", "lat": 13.74, "lng": 100.55, "note": "Thailand, Laos and Cambodia", "wait": "45–90 days", "flag": "🇹🇭"},
        {"id": "sto", "name": "Embassy Santo Domingo", "city": "Santo Domingo", "addr": "Av. Colombia #57", "lat": 18.46, "lng": -69.93, "note": "High family based demand", "wait": "60–120 days", "flag": "🇩🇴"},
        {"id": "bog", "name": "Embassy Bogotá", "city": "Bogotá", "addr": "Calle 24 Bis #48-50", "lat": 4.64, "lng": -74.09, "note": "Colombia", "wait": "45–90 days", "flag": "🇨🇴"},
        {"id": "jnb", "name": "Consulate Johannesburg", "city": "Johannesburg", "addr": "1 Sandton Dr", "lat": -26.11, "lng": 28.06, "note": "Southern Africa", "wait": "30–60 days", "flag": "🇿🇦"},
        {"id": "war", "name": "Embassy Warsaw", "city": "Warsaw", "addr": "Aleje Ujazdowskie", "lat": 52.22, "lng": 21.02, "note": "Poland", "wait": "30–45 days", "flag": "🇵🇱"},
    ],
}

MONTH_MAP = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif&family=JetBrains+Mono:wght@400;500;600&family=Karla:wght@400;500;600;700&display=swap');

:root{
    --bg:#0a0a0a;
    --panel:#0e0e0e;
    --card:#101010;
    --line:#1a1a1a;
    --text:#cccccc;
    --soft:#777777;
    --muted:#444444;
    --white:#ffffff;
    --accent:#caa072;
}
html, body, [class*="css"]  { font-family:'Karla', sans-serif; }
.stApp { background: var(--bg); color: var(--text); }
[data-testid="stSidebar"] {
    background: #0a0a0a;
    border-right: 1px solid var(--line);
}
[data-testid="stSidebar"] > div:first-child { padding-top: 0.8rem; }
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stDateInput label,
section[data-testid="stSidebar"] .stSlider label,
section[data-testid="stSidebar"] .stRadio label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.64rem !important;
    letter-spacing: .11em;
    color: var(--muted) !important;
    font-weight: 600;
}
div[data-baseweb="select"] > div,
.stDateInput > div > div,
.stTextInput > div > div {
    background: var(--panel);
    border: 1px solid var(--line);
}
.stButton > button {
    width: 100%;
    background: #fff;
    color: #000;
    border: none;
    border-radius: 0;
    font-size: 0.76rem;
    font-weight: 700;
    letter-spacing: .10em;
    min-height: 2.7rem;
}
.sidebar-brand{
    border-bottom:1px solid var(--line);
    padding-bottom:0.9rem;
    margin-bottom:0.9rem;
}
.brand-kicker{
    font-family:'JetBrains Mono', monospace;
    font-size:.70rem;
    letter-spacing:.18em;
    color:#fff;
    font-weight:600;
}
.brand-sub{
    font-size:.70rem;
    color:var(--muted);
    line-height:1.5;
    margin-top:.2rem;
}
.hero-title{
    font-family:'Instrument Serif', serif;
    font-size:3rem;
    line-height:1.02;
    color:#fff;
    font-weight:400;
    letter-spacing:-.03em;
    margin:0;
}
.hero-copy{
    font-size:.96rem;
    color:#555;
    line-height:1.85;
    max-width:560px;
    margin-top:.65rem;
}
.mini-stat{
    border:1px solid var(--line);
    padding:1rem 1.1rem;
    height:100%;
}
.mini-stat .num{
    font-family:'Instrument Serif', serif;
    font-size:2rem;
    color:#fff;
}
.mini-stat .sub{
    font-size:.67rem;
    color:#444;
    text-transform:uppercase;
    letter-spacing:.08em;
    margin-top:.15rem;
}
.divider-head{
    display:flex;
    align-items:baseline;
    justify-content:space-between;
    margin-bottom:.25rem;
    border-bottom:1px solid var(--line);
    padding-bottom:.75rem;
}
.kicker{
    font-family:'JetBrains Mono', monospace;
    font-size:.62rem;
    color:#444;
    letter-spacing:.10em;
    text-transform:uppercase;
}
.live-pill{
    font-family:'JetBrains Mono', monospace;
    font-size:.60rem;
    letter-spacing:.14em;
    color:var(--accent);
    border:1px solid rgba(202,160,114,.2);
    padding:.30rem .65rem;
}
.metric-shell{
    border:1px solid var(--line);
    padding:.95rem 1rem;
}
.metric-l{
    font-size:.56rem;
    color:#444;
    text-transform:uppercase;
    letter-spacing:.11em;
    font-weight:600;
}
.metric-v{
    font-family:'JetBrains Mono', monospace;
    color:#fff;
    margin-top:.28rem;
}
.section-shell{
    border:1px solid var(--line);
    padding:1rem 1.05rem .6rem 1.05rem;
    margin-bottom:1rem;
}
.note-shell{
    border:1px solid var(--line);
    border-left:3px solid var(--accent);
    padding:1.15rem 1.25rem;
    margin-top:1.2rem;
}
.consulate-shell{
    border:1px solid var(--line);
    margin-top:1rem;
}
.consulate-top{
    display:flex;
    align-items:center;
    justify-content:space-between;
    padding:.95rem 1.15rem;
    border-bottom:1px solid var(--line);
    background:#0e0e0e;
}
.cons-grid{
    display:grid;
    grid-template-columns:1fr 1fr 1fr;
}
.cons-cell{
    padding:.8rem 1rem;
    border-right:1px solid var(--line);
}
.cons-cell:last-child{
    border-right:none;
}
.cons-label{
    font-size:.56rem;
    color:#444;
    text-transform:uppercase;
    letter-spacing:.09em;
    font-weight:600;
    margin-bottom:.2rem;
}
.cons-value{
    font-size:.75rem;
    color:#777;
    line-height:1.55;
}
.cons-accent{
    color:var(--accent);
}
.small-muted{
    font-size:.72rem;
    color:#555;
}
thead tr th{
    text-align:left !important;
    font-family:'JetBrains Mono', monospace !important;
    font-size:.62rem !important;
    color:#444 !important;
    letter-spacing:.10em !important;
    text-transform:uppercase;
}
tbody tr td{
    color:#777 !important;
}
</style>
""", unsafe_allow_html=True)

def accent_for_case(case_type: str) -> str:
    if case_type == "IR / CR":
        return "#2980b9"
    if case_type == "Family":
        return "#8e44ad"
    return "#caa072"

def metric_block(label: str, value: str):
    st.markdown(
        f"""
        <div class="metric-shell">
            <div class="metric-l">{label}</div>
            <div class="metric-v">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def consulate_block(consulate: dict, est_early: Optional[datetime], est_late: Optional[datetime], accent: str):
    st.markdown(
        f"""
        <style>:root{{--accent:{accent};}}</style>
        <div class="consulate-shell">
            <div class="consulate-top">
                <div style="display:flex;align-items:center;gap:.65rem;">
                    <div style="font-size:1.15rem;">{consulate.get("flag","📍")}</div>
                    <div>
                        <div style="font-family:'Instrument Serif',serif;font-size:1.15rem;color:#fff;line-height:1;">{consulate["city"]}</div>
                        <div style="font-family:'JetBrains Mono',monospace;font-size:.62rem;color:#444;margin-top:.18rem;">U.S. {consulate["name"]}</div>
                    </div>
                </div>
                <a href="https://www.google.com/maps/search/?api=1&query={consulate['lat']},{consulate['lng']}" target="_blank" style="font-family:'JetBrains Mono',monospace;font-size:.62rem;color:{accent};text-decoration:none;border:1px solid {accent}33;padding:.35rem .7rem;letter-spacing:.05em;">OPEN IN MAPS ↗</a>
            </div>
            <div class="cons-grid">
                <div class="cons-cell">
                    <div class="cons-label">Address</div>
                    <div class="cons-value">{consulate["addr"]}</div>
                </div>
                <div class="cons-cell">
                    <div class="cons-label">Scheduling wait</div>
                    <div class="cons-value cons-accent">{consulate["wait"]}</div>
                </div>
                <div class="cons-cell">
                    <div class="cons-label">Notes</div>
                    <div class="cons-value">{consulate["note"]}</div>
                </div>
            </div>
            {f'<div style="border-top:1px solid #1a1a1a;padding:.8rem 1.15rem;display:flex;align-items:center;justify-content:space-between;"><div class="cons-label" style="margin:0;">Estimated scheduling</div><div style="font-family:JetBrains Mono,monospace;font-size:.86rem;color:{accent};">{est_early.strftime("%b %Y")} — {est_late.strftime("%b %Y")}</div></div>' if est_early and est_late else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_links(n: int = 13):
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
    for item in out:
        key = (item["yr"], item["mi"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
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
            cat_key = next((c for c in ALL_CATEGORIES if c.replace("_", "") in cell_text.replace("_", "")), None)
            if not cat_key:
                continue
            target.setdefault(cat_key, {})
            for col_index, region in col_map.items():
                if col_index < len(cells):
                    target[cat_key][region] = cells[col_index].get_text(strip=True)
    return res

def fetch_bulletins(n: int = 13):
    links = fetch_links(n)
    records = []
    for link in links:
        bulletin_date = datetime(link["yr"], link["mi"], 1)
        try:
            data = parse_page(link["url"])
        except Exception:
            continue
        for table_type, cats in data.items():
            for cat, regs in cats.items():
                for region, cutoff in regs.items():
                    records.append(
                        {
                            "bulletin_date": bulletin_date,
                            "table_type": table_type,
                            "category": cat,
                            "region": region,
                            "cutoff_raw": cutoff,
                            "cutoff_date": parse_date(cutoff),
                        }
                    )
    df = pd.DataFrame(records)
    if not df.empty:
        df.sort_values(["category", "region", "bulletin_date"], inplace=True)
    return df

def movement(df: pd.DataFrame, category: str, region: str, table_type: str):
    mask = (
        (df["category"] == category)
        & (df["region"] == region)
        & (df["table_type"] == table_type)
        & df["cutoff_date"].notna()
    )
    out = df.loc[mask].copy().sort_values("bulletin_date")
    out["prev"] = out["cutoff_date"].shift(1)
    out["move"] = (out["cutoff_date"] - out["prev"]).dt.days
    return out

def forecast(df: pd.DataFrame, category: str, region: str, priority_date: datetime, table_type: str, confidence: float):
    mv = movement(df, category, region, table_type).dropna(subset=["move"])
    if mv.empty:
        return {"status": "NO_DATA"}

    last_row = mv.iloc[-1]
    last_cutoff = last_row["cutoff_date"]
    last_bulletin = last_row["bulletin_date"]
    days_remaining = (priority_date - last_cutoff).days

    if days_remaining <= 0:
        return {
            "status": "CURRENT",
            "last_cutoff": last_cutoff,
            "last_bulletin": last_bulletin,
        }

    movements = mv["move"].astype(float).values
    avg_move = float(np.mean(movements))
    std_move = float(np.std(movements, ddof=1)) if len(movements) > 1 else 0.0
    if avg_move <= 0:
        return {"status": "RETROGRESSION"}

    months_est = days_remaining / avg_move
    projected_current = last_bulletin + timedelta(days=months_est * 30.44)
    z = {0.8: 1.28, 0.9: 1.645, 0.95: 1.96}.get(confidence, 1.645)

    early_rate = max(avg_move + z * std_move, avg_move * 0.65)
    late_rate = max(avg_move - z * std_move, avg_move * 0.25)

    current_early = last_bulletin + timedelta(days=(days_remaining / early_rate) * 30.44)
    current_late = last_bulletin + timedelta(days=(days_remaining / late_rate) * 30.44)

    interview_early = current_early + timedelta(days=60)
    interview_late = current_late + timedelta(days=180)

    return {
        "status": "OK",
        "days_remaining": int(days_remaining),
        "avg_move": round(avg_move),
        "projected_current": projected_current,
        "current_early": current_early,
        "current_late": current_late,
        "interview_early": interview_early,
        "interview_late": interview_late,
        "months_est": max(1, int(round(months_est))),
        "n": len(movements),
        "last_cutoff": last_cutoff,
        "last_bulletin": last_bulletin,
        "std_move": round(std_move, 1),
    }

def build_progression_chart(mv: pd.DataFrame, priority_date: datetime, fc: dict, accent: str):
    mv = mv.copy().dropna(subset=["cutoff_date"])
    fig = go.Figure()

    if fc.get("status") == "OK":
        band_x = [fc["current_early"], fc["current_late"], fc["current_late"], fc["current_early"]]
        band_y = [priority_date - timedelta(days=35), priority_date - timedelta(days=35), priority_date + timedelta(days=35), priority_date + timedelta(days=35)]
        fig.add_trace(
            go.Scatter(
                x=band_x,
                y=band_y,
                fill="toself",
                mode="lines",
                line=dict(color="rgba(0,0,0,0)"),
                fillcolor="rgba(202,160,114,0.10)",
                name="Forecast range",
                hoverinfo="skip",
            )
        )

    fig.add_trace(
        go.Scatter(
            x=mv["bulletin_date"],
            y=mv["cutoff_date"],
            mode="lines+markers",
            name="Cutoff trend",
            line=dict(width=2.6, color=accent),
            marker=dict(size=6, color="#0a0a0a", line=dict(width=1.5, color=accent)),
        )
    )

    fig.add_hline(y=priority_date, line_color="#c0392b", line_dash="dash", line_width=1.2)

    if fc.get("status") == "OK":
        fig.add_trace(
            go.Scatter(
                x=[fc["last_bulletin"], fc["projected_current"]],
                y=[fc["last_cutoff"], priority_date],
                mode="lines",
                name="Projected path",
                line=dict(width=2.2, dash="dot", color="#6f532f"),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[fc["current_early"], fc["projected_current"], fc["current_late"]],
                y=[priority_date, priority_date, priority_date],
                mode="markers+lines",
                name="Estimated current window",
                line=dict(width=2.4, color=accent),
                marker=dict(size=[7, 10, 7], color=[accent, accent, accent]),
            )
        )
        fig.add_annotation(
            x=fc["projected_current"],
            y=priority_date,
            text="Estimated current",
            showarrow=True,
            arrowhead=2,
            ax=26,
            ay=-40,
            bgcolor="#111111",
            bordercolor="#222222",
            font=dict(color="#dddddd", size=10),
        )

    fig.update_layout(
        height=380,
        margin=dict(l=12, r=12, t=8, b=8),
        paper_bgcolor="#0a0a0a",
        plot_bgcolor="#0a0a0a",
        font=dict(color="#777", family="Karla, sans-serif"),
        legend=dict(orientation="h", y=1.07, x=0),
        xaxis=dict(gridcolor="#1a1a1a", title=None),
        yaxis=dict(gridcolor="#1a1a1a", title=None),
    )
    return fig

def build_movement_bar_chart(mv: pd.DataFrame, accent: str):
    bar = mv.dropna(subset=["move"]).copy()
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=bar["bulletin_date"],
            y=bar["move"],
            marker_color=accent,
            name="Monthly movement",
        )
    )
    fig.update_layout(
        height=280,
        margin=dict(l=12, r=12, t=8, b=8),
        paper_bgcolor="#0a0a0a",
        plot_bgcolor="#0a0a0a",
        font=dict(color="#777", family="Karla, sans-serif"),
        xaxis=dict(gridcolor="#1a1a1a", title=None),
        yaxis=dict(gridcolor="#1a1a1a", title=None),
    )
    return fig

def build_consulate_map(posts: list[dict], selected_id: str, accent: str):
    df_map = pd.DataFrame(posts)
    df_map["size"] = np.where(df_map["id"] == selected_id, 18, 11)
    df_map["opacity"] = np.where(df_map["id"] == selected_id, 1.0, 0.55)
    df_map["label"] = df_map["city"] + " · " + df_map["wait"]

    fig = go.Figure()
    selected = df_map[df_map["id"] == selected_id]
    others = df_map[df_map["id"] != selected_id]

    if not others.empty:
        fig.add_trace(
            go.Scattermap(
                lat=others["lat"],
                lon=others["lng"],
                mode="markers",
                text=others["label"],
                hovertemplate="%{text}<extra></extra>",
                marker=dict(size=others["size"], color="#7a7a7a", opacity=others["opacity"]),
                name="Other posts",
            )
        )

    if not selected.empty:
        fig.add_trace(
            go.Scattermap(
                lat=selected["lat"],
                lon=selected["lng"],
                mode="markers",
                text=selected["label"],
                hovertemplate="%{text}<extra></extra>",
                marker=dict(size=selected["size"], color=accent, opacity=1),
                name="Selected post",
            )
        )

    fig.update_layout(
        height=340,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="#0a0a0a",
        map=dict(
            style="carto-darkmatter",
            zoom=1.35,
            center=dict(lat=float(df_map["lat"].mean()), lon=float(df_map["lng"].mean())),
        ),
        legend=dict(orientation="h", y=1.03, x=0),
        font=dict(color="#777"),
    )
    return fig

# Sidebar
with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-brand">
            <div class="brand-kicker">VISA FORECAST</div>
            <div class="brand-sub">U.S. Department of State · Visa Bulletin Analysis</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    case_type = st.radio(
        "Category type",
        ["IR / CR", "Family", "Employment"],
        horizontal=True,
        key="case_type",
    )

    if case_type == "IR / CR":
        category = st.selectbox(
            "Preference",
            IR_CATEGORIES,
            key="category_ir",
            format_func=lambda c: CATEGORY_LABELS.get(c, c),
        )
    elif case_type == "Family":
        category = st.selectbox(
            "Preference",
            FAMILY_CATEGORIES,
            key="category_family",
            format_func=lambda c: CATEGORY_LABELS.get(c, c),
        )
    else:
        category = st.selectbox(
            "Preference",
            EMPLOYMENT_CATEGORIES,
            key="category_employment",
            format_func=lambda c: CATEGORY_LABELS.get(c, c),
        )

    region_label = st.selectbox(
        "Region",
        list(CHARGEABILITY_REGIONS.keys()),
        key="region_label",
    )
    region = CHARGEABILITY_REGIONS[region_label]

    posts = CONSULATES.get(region, [])
    post_options = [f'{p["city"]} — {p["name"]}' for p in posts]
    default_index = 0 if posts else None
    post_label = st.selectbox("Interview location", post_options, index=default_index, key="post_label") if posts else None
    selected_post = next((p for p in posts if f'{p["city"]} — {p["name"]}' == post_label), None)

    if case_type != "IR / CR":
        table_type = st.selectbox(
            "Chart",
            ["final_action", "dates_for_filing"],
            key="table_type",
            format_func=lambda x: "Final Action" if x == "final_action" else "Dates for Filing",
        )
        priority_date = st.date_input("Priority date", datetime(2022, 3, 15), key="priority_date")
        confidence = st.select_slider("Confidence", [0.8, 0.9, 0.95], value=0.8, key="confidence")
        history_months = st.slider("Bulletins", 6, 36, 13, key="history_months")
    else:
        table_type = "final_action"
        priority_date = datetime(2022, 3, 15).date()
        confidence = 0.8
        history_months = 13

    run = st.button("GENERATE FORECAST", use_container_width=True, type="primary")

accent = accent_for_case(case_type)

# Hero
st.markdown(
    f"""
    <style>:root{{--accent:{accent};}}</style>
    <div style="max-width:620px;margin-bottom:2rem;">
        <h1 class="hero-title">Visa Bulletin Forecast</h1>
        <p class="hero-copy">Closer to the editorial React layout you pasted: tighter typography, harder dark theme, mono labels, a cleaner metric grid, and forecast visuals that feel like a product instead of a generic dashboard.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if "has_run" not in st.session_state:
    st.session_state["has_run"] = False
if run:
    st.session_state["has_run"] = True

if not st.session_state["has_run"]:
    a, b, c = st.columns(3)
    with a:
        st.markdown('<div class="mini-stat"><div class="num">12+</div><div class="sub">months</div></div>', unsafe_allow_html=True)
    with b:
        st.markdown('<div class="mini-stat"><div class="num">15</div><div class="sub">categories</div></div>', unsafe_allow_html=True)
    with c:
        st.markdown('<div class="mini-stat"><div class="num">80+</div><div class="sub">consulates</div></div>', unsafe_allow_html=True)
    st.stop()

if case_type == "IR / CR":
    header_left, header_right = st.columns([8, 1.5])
    with header_left:
        st.markdown(
            f"""
            <div class="divider-head">
                <div>
                    <div style="font-family:'Instrument Serif',serif;font-size:1.9rem;color:#fff;">{CATEGORY_LABELS.get(category, category)}</div>
                    <div class="kicker">{region_label}{" · " + selected_post["city"] if selected_post else ""}</div>
                </div>
                <div class="live-pill">LIVE</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown(
        """
        <div class="section-shell">
            <div style="font-family:'Instrument Serif',serif;font-size:1.25rem;color:#fff;margin-bottom:.45rem;">Immediate relative visas are always current</div>
            <div class="small-muted">Processing still depends on petition approval, NVC document completion, interview capacity, and post-specific scheduling.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    x1, x2, x3, x4 = st.columns(4)
    with x1:
        metric_block("I-130 Petition", "6–14 mo")
    with x2:
        metric_block("NVC Processing", "2–6 mo")
    with x3:
        metric_block("Interview", "1–3 mo")
    with x4:
        metric_block("Total estimated", "9–23 mo")
    if selected_post:
        consulate_block(selected_post, None, None, accent)
        st.plotly_chart(build_consulate_map(posts, selected_post["id"], accent), use_container_width=True)
    st.stop()

df = fetch_bulletins(history_months)
if df.empty:
    st.error("No visa bulletin data loaded.")
    st.stop()

priority_dt = datetime.combine(priority_date, datetime.min.time())
fc = forecast(df, category, region, priority_dt, table_type, confidence)
mv = movement(df, category, region, table_type)

title_col, live_col = st.columns([8, 1.5])
with title_col:
    st.markdown(
        f"""
        <div class="divider-head">
            <div>
                <div style="font-family:'Instrument Serif',serif;font-size:1.9rem;color:#fff;">{region_label} · {CATEGORY_LABELS.get(category, category)}</div>
                <div class="kicker">{selected_post["city"] if selected_post else "No consulate selected"} · {history_months} bulletins loaded</div>
            </div>
            <div class="live-pill">LIVE</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

tab_forecast, tab_data, tab_export = st.tabs(["Forecast", "Data", "Export"])

with tab_forecast:
    if fc["status"] == "CURRENT":
        st.success("This priority date is already current based on the latest available bulletin trend.")
    elif fc["status"] == "NO_DATA":
        st.warning("Not enough movement data to generate a forecast.")
    elif fc["status"] == "RETROGRESSION":
        st.warning("Recent trend does not support a forward forecast right now.")

    if fc["status"] == "OK":
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            metric_block("Days remaining", f'{fc["days_remaining"]:,}')
        with m2:
            metric_block("Avg. movement", f'{fc["avg_move"]} d/mo')
        with m3:
            metric_block("Est. current", fc["projected_current"].strftime("%b %Y"))
        with m4:
            metric_block("Interview window", f'{fc["interview_early"].strftime("%b %Y")} — {fc["interview_late"].strftime("%b %Y")}')

    st.markdown('<div class="section-shell"><div class="kicker" style="margin-bottom:.6rem;">Cutoff date progression</div>', unsafe_allow_html=True)
    st.plotly_chart(build_progression_chart(mv, priority_dt, fc, accent), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    left, right = st.columns([1.25, 1])
    with left:
        st.markdown('<div class="section-shell"><div class="kicker" style="margin-bottom:.6rem;">Monthly movement</div>', unsafe_allow_html=True)
        st.plotly_chart(build_movement_bar_chart(mv, accent), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with right:
        if posts and selected_post:
            st.markdown('<div class="section-shell"><div class="kicker" style="margin-bottom:.6rem;">Consulate map</div>', unsafe_allow_html=True)
            st.plotly_chart(build_consulate_map(posts, selected_post["id"], accent), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

    if selected_post and fc["status"] == "OK":
        consulate_block(selected_post, fc["interview_early"], fc["interview_late"], accent)

    if fc["status"] == "OK":
        st.markdown(
            f"""
            <div class="note-shell">
                <div style="font-family:'Instrument Serif',serif;font-size:1.18rem;color:#fff;margin-bottom:.45rem;">Projected interview window</div>
                <div class="small-muted" style="margin-bottom:.9rem;">Based on {fc["n"]} historical movement periods at {int(confidence*100)}% confidence. Includes a rough 2 to 6 month NVC and scheduling buffer.</div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:1px;">
                    <div style="background:#111;padding:.95rem 1rem;">
                        <div class="metric-l">Become current</div>
                        <div style="font-family:'JetBrains Mono',monospace;color:#fff;margin-top:.3rem;">{fc["projected_current"].strftime("%B %Y")}</div>
                        <div class="small-muted" style="margin-top:.15rem;">about {fc["months_est"]} months from now</div>
                    </div>
                    <div style="background:#111;padding:.95rem 1rem;">
                        <div class="metric-l">Interview scheduling</div>
                        <div style="font-family:'JetBrains Mono',monospace;color:{accent};margin-top:.3rem;">{fc["interview_early"].strftime("%b %Y")} — {fc["interview_late"].strftime("%b %Y")}</div>
                        <div class="small-muted" style="margin-top:.15rem;">consulate capacity can still move this window</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

with tab_data:
    data_df = mv[["bulletin_date", "cutoff_date", "move"]].copy()
    data_df.columns = ["Month", "Cutoff", "Movement"]
    st.dataframe(data_df, hide_index=True, use_container_width=True)
    if fc["status"] == "OK":
        stats = st.columns(3)
        with stats[0]:
            metric_block("Mean", f'{fc["avg_move"]}d')
        with stats[1]:
            metric_block("Std dev", f'{fc["std_move"]}d')
        with stats[2]:
            median_move = int(pd.Series(mv["move"].dropna()).median()) if not mv["move"].dropna().empty else 0
            metric_block("Median", f'{median_move}d')

with tab_export:
    csv_data = df.to_csv(index=False)
    json_data = json.dumps(
        {
            "category": category,
            "region": region,
            "table_type": table_type,
            "priority_date": priority_dt.strftime("%Y-%m-%d"),
            "forecast_status": fc["status"],
            "projected_current": fc["projected_current"].strftime("%Y-%m-%d") if fc.get("projected_current") else None,
            "interview_early": fc["interview_early"].strftime("%Y-%m-%d") if fc.get("interview_early") else None,
            "interview_late": fc["interview_late"].strftime("%Y-%m-%d") if fc.get("interview_late") else None,
        },
        indent=2,
    )
    st.download_button("Download bulletin data CSV", csv_data, file_name="visa_bulletin_data.csv", mime="text/csv")
    st.download_button("Download forecast JSON", json_data, file_name="visa_forecast.json", mime="application/json")
