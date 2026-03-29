
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

    if selected_post:
        wait_early, wait_late = parse_wait_time(selected_post["wait"])
    else:
        wait_early, wait_late = (60, 120)

    nvc_complete_dt = datetime.combine(nvc_complete_date, datetime.min.time())
    interview_early = nvc_complete_dt + timedelta(days=wait_early)
    interview_late = nvc_complete_dt + timedelta(days=wait_late)

    ir_timeline = pd.DataFrame(
        {
            "stage": ["NVC complete", "Interview window opens", "Interview window closes"],
            "date": [nvc_complete_dt, interview_early, interview_late],
        }
    )

    fig_ir = go.Figure()
    fig_ir.add_trace(
        go.Scatter(
            x=ir_timeline["date"],
            y=ir_timeline["stage"],
            mode="lines+markers",
            name="Forecast path",
            line=dict(width=2.8, color=accent),
            marker=dict(size=8, color=accent),
        )
    )
    fig_ir.add_shape(
        type="rect",
        x0=interview_early,
        x1=interview_late,
        y0=0.8,
        y1=2.2,
        xref="x",
        yref="y",
        line=dict(color="rgba(0,0,0,0)"),
        fillcolor="rgba(41,128,185,0.16)" if accent == "#2980b9" else "rgba(202,160,114,0.12)",
        layer="below",
    )
    fig_ir.add_vline(x=nvc_complete_dt, line_dash="dash", line_color="#c0392b", line_width=1.1)
    fig_ir.add_annotation(
        x=nvc_complete_dt,
        y="NVC complete",
        text="NVC complete",
        showarrow=False,
        yshift=18,
        font=dict(color="#c0392b", size=10),
        bgcolor="#111111",
        bordercolor="#222222",
    )
    fig_ir.update_layout(
        height=320,
        margin=dict(l=12, r=12, t=8, b=8),
        paper_bgcolor="#0a0a0a",
        plot_bgcolor="#0a0a0a",
        font=dict(color="#777", family="Karla, sans-serif"),
        legend=dict(orientation="h", y=1.07, x=0),
        xaxis=dict(gridcolor="#1a1a1a", title=None),
        yaxis=dict(
            gridcolor="#1a1a1a",
            title=None,
            categoryorder="array",
            categoryarray=list(ir_timeline["stage"]),
        ),
    )

    st.markdown(
        """
        <div class="section-shell">
            <div style="font-family:'Instrument Serif',serif;font-size:1.25rem;color:#fff;margin-bottom:.45rem;">Las visas IR/CR siempre están al día.</div>
            <div class="small-muted">Después de NVC complete o documentarily qualified, la entrevista depende del tiempo de espera del consulado seleccionado.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    x1, x2, x3, x4 = st.columns(4)
    with x1:
        metric_block("NVC COMPLETE", nvc_complete_dt.strftime("%b %d, %Y"), "#3498db")
    with x2:
        metric_block("ESPERA", f"{wait_early}–{wait_late} días", "#2ecc71")
    with x3:
        metric_block("ENTREVISTA INICIO", interview_early.strftime("%b %Y"), "#f39c12")
    with x4:
        metric_block("ENTREVISTA FIN", interview_late.strftime("%b %Y"), "#e74c3c")

    st.markdown(
        f"""
        <div class="section-shell">
            <div class="kicker" style="margin-bottom:.6rem;">PRONÓSTICO DE ENTREVISTA</div>
            <div class="small-muted" style="margin-bottom:.85rem;">Este cálculo toma como punto de partida tu fecha de NVC complete y luego aplica la espera del consulado seleccionado.</div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:1px;">
                <div style="background:#111;padding:.95rem 1rem;">
                    <div class="metric-l">PUNTO DE PARTIDA</div>
                    <div style="font-family:'JetBrains Mono',monospace;color:#fff;margin-top:.3rem;">{nvc_complete_dt.strftime("%B %d, %Y")}</div>
                    <div class="small-muted" style="margin-top:.15rem;">NVC complete o documentarily qualified</div>
                </div>
                <div style="background:#111;padding:.95rem 1rem;">
                    <div class="metric-l">VENTANA ESTIMADA</div>
                    <div style="font-family:'JetBrains Mono',monospace;color:{accent};margin-top:.3rem;">{interview_early.strftime("%b %d, %Y")} — {interview_late.strftime("%b %d, %Y")}</div>
                    <div class="small-muted" style="margin-top:.15rem;">basada en la espera del consulado seleccionado</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


    if selected_post:
        consulate_block(selected_post, interview_early, interview_late, accent)
        st.plotly_chart(build_consulate_map(posts, selected_post["id"], accent), use_container_width=True)
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

    today_dt = datetime.today()
    petition_early = today_dt + timedelta(days=30 * 6)
    petition_late = today_dt + timedelta(days=30 * 14)
    nvc_early = petition_early + timedelta(days=30 * 2)
    nvc_late = petition_late + timedelta(days=30 * 6)

    if selected_post:
        wait_early, wait_late = parse_wait_time(selected_post["wait"])
    else:
        wait_early, wait_late = (60, 120)

    interview_early = nvc_early + timedelta(days=wait_early)
    interview_late = nvc_late + timedelta(days=wait_late)

    ir_timeline = pd.DataFrame(
        {
            "stage": ["Petition filed", "I-130 approved", "NVC complete", "Interview scheduled"],
            "early": [today_dt, petition_early, nvc_early, interview_early],
            "late": [today_dt, petition_late, nvc_late, interview_late],
        }
    )

    fig_ir = go.Figure()
    fig_ir.add_trace(
        go.Scatter(
            x=ir_timeline["early"],
            y=ir_timeline["stage"],
            mode="lines+markers",
            name="Early path",
            line=dict(width=2.5, color=accent),
            marker=dict(size=8, color=accent),
        )
    )
    fig_ir.add_trace(
        go.Scatter(
            x=ir_timeline["late"],
            y=ir_timeline["stage"],
            mode="lines+markers",
            name="Late path",
            line=dict(width=2.5, color="#6f532f", dash="dot"),
            marker=dict(size=8, color="#6f532f"),
        )
    )
    for idx, row in ir_timeline.iterrows():
        fig_ir.add_shape(
            type="rect",
            x0=row["early"],
            x1=row["late"],
            y0=idx - 0.22,
            y1=idx + 0.22,
            xref="x",
            yref="y",
            line=dict(color="rgba(0,0,0,0)"),
            fillcolor="rgba(202,160,114,0.12)",
            layer="below",
        )
    fig_ir.add_vline(x=today_dt, line_dash="dash", line_color="#c0392b", line_width=1.1)
    fig_ir.add_annotation(
        x=today_dt,
        y="Petition filed",
        text="Today",
        showarrow=False,
        yshift=18,
        font=dict(color="#c0392b", size=10),
        bgcolor="#111111",
        bordercolor="#222222",
    )
    fig_ir.update_layout(
        height=330,
        margin=dict(l=12, r=12, t=8, b=8),
        paper_bgcolor="#0a0a0a",
        plot_bgcolor="#0a0a0a",
        font=dict(color="#777", family="Karla, sans-serif"),
        legend=dict(orientation="h", y=1.07, x=0),
        xaxis=dict(gridcolor="#1a1a1a", title=None),
        yaxis=dict(gridcolor="#1a1a1a", title=None, categoryorder="array", categoryarray=list(ir_timeline["stage"])),
    )

    st.markdown(
        """
        <div class="section-shell">
            <div style="font-family:'Instrument Serif',serif;font-size:1.25rem;color:#fff;margin-bottom:.45rem;">Immediate relative visas are always current</div>
            <div class="small-muted">There is no visa bulletin cutoff, but interview timing still depends on petition approval, NVC completion, and the selected consulate's scheduling range.</div>
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
        metric_block("ESPERA", f"{wait_early}–{wait_late} días", "#2ecc71")
    with x4:
        metric_block("Interview window", f'{interview_early.strftime("%b %Y")} — {interview_late.strftime("%b %Y")}')

    st.markdown('<div class="section-shell"><div class="kicker" style="margin-bottom:.6rem;">IR / CR forecast timeline</div>', unsafe_allow_html=True)
    st.plotly_chart(fig_ir, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="note-shell">
            <div style="font-family:'Instrument Serif',serif;font-size:1.18rem;color:#fff;margin-bottom:.45rem;">Projected processing window</div>
            <div class="small-muted" style="margin-bottom:.9rem;">This forecast is based on petition timing, NVC timing, and the selected consulate's scheduling wait of {wait_early} to {wait_late} days.</div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:1px;">
                <div style="background:#111;padding:.95rem 1rem;">
                    <div class="metric-l">Case completion range</div>
                    <div style="font-family:'JetBrains Mono',monospace;color:#fff;margin-top:.3rem;">{petition_early.strftime("%b %Y")} — {nvc_late.strftime("%b %Y")}</div>
                    <div class="small-muted" style="margin-top:.15rem;">petition approval through NVC completion</div>
                </div>
                <div style="background:#111;padding:.95rem 1rem;">
                    <div class="metric-l">Interview scheduling</div>
                    <div style="font-family:'JetBrains Mono',monospace;color:{accent};margin-top:.3rem;">{interview_early.strftime("%b %Y")} — {interview_late.strftime("%b %Y")}</div>
                    <div class="small-muted" style="margin-top:.15rem;">driven by the selected consulate wait time</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if selected_post:
        consulate_block(selected_post, interview_early, interview_late, accent)
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


st.markdown(
    '''
    <div style="position:fixed;bottom:10px;right:20px;font-size:10px;color:#555;font-family:'JetBrains Mono', monospace;">
        github.com/roxannehernan
    </div>
    ''',
    unsafe_allow_html=True
)
