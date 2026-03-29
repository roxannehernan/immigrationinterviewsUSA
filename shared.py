
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
        {"id": "cdmx", "name": "Embassy Mexico City", "city": "CDMX", "addr": "Paseo de la Reforma 305", "lat": 19.4276, "lng": -99.1677, "note": "Largest embassy in W. Hemisphere", "wait": "120–240 days", "flag": "🇲🇽"},
        {"id": "gdl", "name": "Consulate Guadalajara", "city": "Guadalajara", "addr": "Progreso 175", "lat": 20.6722, "lng": -103.3625, "note": "Western Mexico", "wait": "60–90 days", "flag": "🇲🇽"},
        {"id": "mty", "name": "Consulate Monterrey", "city": "Monterrey", "addr": "Av. Alfonso Reyes 150", "lat": 25.6714, "lng": -100.3091, "note": "Northeast Mexico", "wait": "60–90 days", "flag": "🇲🇽"},
        {"id": "tij", "name": "Consulate Tijuana", "city": "Tijuana", "addr": "Paseo de las Culturas", "lat": 32.5366, "lng": -116.9717, "note": "High volume border", "wait": "60–90 days", "flag": "🇲🇽"},
    ],
    "philippines": [{"id": "mnl", "name": "Embassy Manila", "city": "Manila", "addr": "1201 Roxas Blvd", "lat": 14.5619, "lng": 120.9801, "note": "Busiest IV post worldwide", "wait": "90–180 days", "flag": "🇵🇭"}],
    "el_salvador": [{"id": "ss", "name": "Embassy San Salvador", "city": "San Salvador", "addr": "Blvd. Santa Elena", "lat": 13.6664, "lng": -89.2530, "note": "Sole post", "wait": "60–120 days", "flag": "🇸🇻"}],
    "guatemala": [{"id": "gua", "name": "Embassy Guatemala City", "city": "Guatemala City", "addr": "Av. Reforma 7-01", "lat": 14.5980, "lng": -90.5137, "note": "Sole post", "wait": "60–120 days", "flag": "🇬🇹"}],
    "honduras": [{"id": "tgu", "name": "Embassy Tegucigalpa", "city": "Tegucigalpa", "addr": "Av. La Paz", "lat": 14.0910, "lng": -87.1963, "note": "Sole post", "wait": "60–120 days", "flag": "🇭🇳"}],
    "vietnam": [
        {"id": "hcm", "name": "Consulate HCMC", "city": "Ho Chi Minh City", "addr": "4 Le Duan Blvd", "lat": 10.7816, "lng": 106.7010, "note": "Primary IV post", "wait": "60–120 days", "flag": "🇻🇳"},
        {"id": "han", "name": "Embassy Hanoi", "city": "Hanoi", "addr": "7 Lang Ha St", "lat": 21.0170, "lng": 105.8132, "note": "Full IV processing", "wait": "45–90 days", "flag": "🇻🇳"},
    ],
    "korea": [{"id": "sel", "name": "Embassy Seoul", "city": "Seoul", "addr": "188 Sejong-daero", "lat": 37.5661, "lng": 126.9747, "note": "Sole post", "wait": "30–60 days", "flag": "🇰🇷"}],
    "brazil": [
        {"id": "sp", "name": "Consulate São Paulo", "city": "São Paulo", "addr": "Rua Henri Dunant 500", "lat": -23.6275, "lng": -46.6958, "note": "Highest volume Brazil", "wait": "60–120 days", "flag": "🇧🇷"},
        {"id": "rio", "name": "Consulate Rio", "city": "Rio de Janeiro", "addr": "Av. Pres. Wilson 147", "lat": -22.9028, "lng": -43.1722, "note": "Full IV", "wait": "45–90 days", "flag": "🇧🇷"},
    ],
    "bangladesh": [{"id": "dhk", "name": "Embassy Dhaka", "city": "Dhaka", "addr": "Madani Ave", "lat": 23.8103, "lng": 90.4125, "note": "High family volume", "wait": "90–180 days", "flag": "🇧🇩"}],
    "pakistan": [
        {"id": "isl", "name": "Embassy Islamabad", "city": "Islamabad", "addr": "Diplomatic Enclave", "lat": 33.7215, "lng": 73.0884, "note": "Primary post", "wait": "90–180 days", "flag": "🇵🇰"},
        {"id": "khi", "name": "Consulate Karachi", "city": "Karachi", "addr": "Mai Kolachi Rd", "lat": 24.8465, "lng": 67.0195, "note": "Sindh & Balochistan", "wait": "60–120 days", "flag": "🇵🇰"},
    ],
    "all": [
        {"id": "lon", "name": "Embassy London", "city": "London", "addr": "33 Nine Elms Ln", "lat": 51.48, "lng": -0.12, "note": "Major EU/UK post", "wait": "30–60 days", "flag": "🇬🇧"},
        {"id": "fra", "name": "Consulate Frankfurt", "city": "Frankfurt", "addr": "Gießener Str. 30", "lat": 50.12, "lng": 8.68, "note": "Germany high EB", "wait": "30–45 days", "flag": "🇩🇪"},
        {"id": "mtl", "name": "Consulate Montreal", "city": "Montreal", "addr": "Sainte-Catherine O", "lat": 45.50, "lng": -73.57, "note": "Primary Canadian IV", "wait": "30–60 days", "flag": "🇨🇦"},
        {"id": "syd", "name": "Consulate Sydney", "city": "Sydney", "addr": "19-29 Martin Pl", "lat": -33.87, "lng": 151.21, "note": "AU/NZ/Pacific", "wait": "30–45 days", "flag": "🇦🇺"},
        {"id": "acc", "name": "Embassy Accra", "city": "Accra", "addr": "Fourth Circular Rd", "lat": 5.57, "lng": -0.18, "note": "West Africa hub", "wait": "60–120 days", "flag": "🇬🇭"},
        {"id": "nbo", "name": "Embassy Nairobi", "city": "Nairobi", "addr": "United Nations Ave", "lat": -1.24, "lng": 36.81, "note": "East Africa hub", "wait": "60–90 days", "flag": "🇰🇪"},
        {"id": "dxb", "name": "Consulate Dubai", "city": "Dubai", "addr": "Al Seef Rd", "lat": 25.26, "lng": 55.30, "note": "UAE", "wait": "30–60 days", "flag": "🇦🇪"},
        {"id": "bkk", "name": "Embassy Bangkok", "city": "Bangkok", "addr": "95 Wireless Rd", "lat": 13.74, "lng": 100.55, "note": "Thailand/Laos/Cambodia", "wait": "45–90 days", "flag": "🇹🇭"},
        {"id": "sto", "name": "Embassy Santo Domingo", "city": "Santo Domingo", "addr": "Av. Colombia #57", "lat": 18.46, "lng": -69.93, "note": "High family based", "wait": "60–120 days", "flag": "🇩🇴"},
        {"id": "bog", "name": "Embassy Bogotá", "city": "Bogotá", "addr": "Calle 24 Bis #48-50", "lat": 4.64, "lng": -74.09, "note": "Colombia", "wait": "45–90 days", "flag": "🇨🇴"},
        {"id": "jnb", "name": "Consulate Johannesburg", "city": "Johannesburg", "addr": "1 Sandton Dr", "lat": -26.11, "lng": 28.06, "note": "Southern Africa", "wait": "30–60 days", "flag": "🇿🇦"},
        {"id": "war", "name": "Embassy Warsaw", "city": "Warsaw", "addr": "Aleje Ujazdowskie", "lat": 52.22, "lng": 21.02, "note": "Poland", "wait": "30–45 days", "flag": "🇵🇱"},
    ],
}

TRANSLATIONS = {
    "en": {"label":"English","flag":"🇺🇸","brand":"VISA FORECAST","sub":"U.S. Department of State · Visa Bulletin Analysis","language":"LANGUAGE","catType":"CATEGORY","prefCat":"PREFERENCE","region":"REGION","consulate":"INTERVIEW LOCATION","chartType":"CHART","finalAction":"Final Action","datesForFiling":"Dates for Filing","priorityDate":"PRIORITY DATE","history":"BULLETINS","nvcCompleteDate":"NVC COMPLETE DATE","runBtn":"GENERATE FORECAST","heroTitle":"Visa Bulletin Forecast","months":"months","categories":"categories","consulates":"consulates","liveData":"LIVE","employmentBased":"Employment","familyBased":"Family","immediateRelative":"IR / CR","irNote":"Immediate relative visas are always current.","irExplain":"After NVC complete or documentarily qualified status, the interview depends on the selected consulate wait time.","nvcComplete":"NVC COMPLETE","avgWaitTime":"WAIT","interviewStart":"INTERVIEW START","interviewEnd":"INTERVIEW END","days":"days","interviewForecast":"INTERVIEW FORECAST","startingPoint":"STARTING POINT","estimatedWindow":"ESTIMATED WINDOW","startingPointCopy":"NVC complete or documentarily qualified","estimatedWindowCopy":"based on the selected consulate wait time","address":"Address","consulateNote":"Notes","estimatedScheduling":"Estimated scheduling","mapView":"Open in Maps ↗","daysToCurrent":"DAYS REMAINING","avgMovement":"TREND","currentBy":"CURRENT ESTIMATE","interviewWindow":"INTERVIEW WINDOW","cutoffProgression":"CUTOFF DATE PROGRESSION","forecast":"Forecast","movement":"Data","exportTab":"Export","bulletinsLoaded":"bulletins","projectedWindow":"FORECAST","becomeCurrent":"BECOME CURRENT","monthsFromNow":"months from now","interviewSched":"INTERVIEW WINDOW","mean":"Mean","median":"Median","stddev":"Std dev","bulletinData":"Download bulletin data CSV","forecastReport":"Download forecast JSON","alreadyCurrent":"This priority date is already current based on the latest available trend.","notEnough":"Not enough movement data to generate a forecast.","retro":"Recent trend does not support a forward forecast right now.","noData":"No visa bulletin data loaded.","consulateCapacity":"Consulate capacity can still move this window","timeline":"Timeline","dataFreshness":"Data freshness","latestBulletin":"Latest bulletin","lastRefresh":"Loaded now","source":"Source","categoryHelp":"Category help","shareSummary":"Share summary","selectedPost":"Selected post","fastestPost":"Fastest post","slowestPost":"Slowest post","regionalAverage":"Regional average","copyReady":"Copy ready summary","openSource":"travel.state.gov","faq":"FAQ","guide":"Process guide","faq_pd_q":"What is a priority date?","faq_pd_a":"The priority date is the placeholder date used to determine when a case can move forward for family and employment categories.","faq_fa_q":"What is Final Action vs Dates for Filing?","faq_fa_a":"Final Action usually controls when a visa can actually be issued. Dates for Filing can sometimes allow earlier document submission.","faq_ir_q":"Why are IR and CR different?","faq_ir_a":"Immediate relative categories are always current, so timing depends more on NVC completion and consulate scheduling than bulletin movement.","faq_consulate_q":"Why do consulates change timing?","faq_consulate_a":"Consulate capacity, local demand, staffing, and interview volume can all shift scheduling windows.","guide_title":"How this process works","guide_intro":"Use this as a directional guide so users understand what each stage means before trusting the forecast.","step_filed":"Case filed","step_filed_desc":"A petition is submitted and enters USCIS review.","step_approved":"Petition approved","step_approved_desc":"USCIS approval allows the case to move toward visa processing.","step_nvc":"At NVC","step_nvc_desc":"The case is gathered, reviewed, and prepared for documentary completion.","step_dq":"Documentarily qualified","step_dq_desc":"NVC has what it needs and the case can wait for interview scheduling.","step_current":"Becomes current","step_current_desc":"For preference categories, the priority date reaches the bulletin threshold.","step_interview":"Interview scheduled","step_interview_desc":"The consulate assigns an interview window based on backlog and capacity."},
    "es": {"label":"Español","flag":"🇲🇽","brand":"VISA FORECAST","sub":"Depto. de Estado · Boletín de Visas","language":"IDIOMA","catType":"CATEGORÍA","prefCat":"PREFERENCIA","region":"REGIÓN","consulate":"LUGAR DE ENTREVISTA","chartType":"GRÁFICO","finalAction":"Acción Final","datesForFiling":"Fechas de Presentación","priorityDate":"FECHA DE PRIORIDAD","history":"BOLETINES","nvcCompleteDate":"FECHA DE NVC COMPLETE","runBtn":"GENERAR PRONÓSTICO","heroTitle":"Pronóstico del Boletín de Visas","months":"meses","categories":"categorías","consulates":"consulados","liveData":"VIVO","employmentBased":"Empleo","familyBased":"Familia","immediateRelative":"IR / CR","irNote":"Las visas IR/CR siempre están al día.","irExplain":"Después de NVC complete o documentarily qualified, la entrevista depende del tiempo de espera del consulado seleccionado.","nvcComplete":"NVC COMPLETE","avgWaitTime":"ESPERA","interviewStart":"ENTREVISTA INICIO","interviewEnd":"ENTREVISTA FIN","days":"días","interviewForecast":"PRONÓSTICO DE ENTREVISTA","startingPoint":"PUNTO DE PARTIDA","estimatedWindow":"VENTANA ESTIMADA","startingPointCopy":"NVC complete o documentarily qualified","estimatedWindowCopy":"basada en la espera del consulado seleccionado","address":"Dirección","consulateNote":"Notas","estimatedScheduling":"Programación estimada","mapView":"Abrir en Maps ↗","daysToCurrent":"DÍAS RESTANTES","avgMovement":"TENDENCIA","currentBy":"ESTIMADO ACTUAL","interviewWindow":"VENTANA DE ENTREVISTA","cutoffProgression":"PROGRESIÓN DE FECHA LÍMITE","forecast":"Pronóstico","movement":"Datos","exportTab":"Exportar","bulletinsLoaded":"boletines","projectedWindow":"PRONÓSTICO","becomeCurrent":"SE PONE AL DÍA","monthsFromNow":"meses desde ahora","interviewSched":"VENTANA DE ENTREVISTA","mean":"Media","median":"Mediana","stddev":"Desv. est.","bulletinData":"Descargar datos CSV","forecastReport":"Descargar pronóstico JSON","alreadyCurrent":"Esta fecha de prioridad ya está al día según la tendencia más reciente.","notEnough":"No hay suficiente movimiento para generar un pronóstico.","retro":"La tendencia reciente no permite un pronóstico hacia adelante en este momento.","noData":"No se cargaron datos del boletín de visas.","consulateCapacity":"La capacidad del consulado todavía puede mover esta ventana","timeline":"Cronología","dataFreshness":"Actualización de datos","latestBulletin":"Último boletín","lastRefresh":"Cargado ahora","source":"Fuente","categoryHelp":"Ayuda de categoría","shareSummary":"Resumen para compartir","selectedPost":"Consulado seleccionado","fastestPost":"Más rápido","slowestPost":"Más lento","regionalAverage":"Promedio regional","copyReady":"Resumen listo para copiar","openSource":"travel.state.gov","faq":"Preguntas frecuentes","guide":"Guía del proceso","faq_pd_q":"¿Qué es la fecha de prioridad?","faq_pd_a":"La fecha de prioridad es la fecha que reserva el lugar del caso para categorías familiares y de empleo.","faq_fa_q":"¿Qué es Acción Final vs Fechas de Presentación?","faq_fa_a":"Acción Final normalmente controla cuándo se puede emitir la visa. Fechas de Presentación a veces permite enviar documentos antes.","faq_ir_q":"¿Por qué IR y CR son diferentes?","faq_ir_a":"Las categorías de familiares inmediatos siempre están al día, así que el tiempo depende más de NVC complete y del consulado que del boletín.","faq_consulate_q":"¿Por qué cambian los tiempos del consulado?","faq_consulate_a":"La capacidad, la demanda local, el personal y el volumen de entrevistas pueden cambiar la programación.","guide_title":"Cómo funciona este proceso","guide_intro":"Úsalo como guía direccional para entender cada etapa antes de confiar en el pronóstico.","step_filed":"Caso presentado","step_filed_desc":"Se presenta una petición y entra a revisión de USCIS.","step_approved":"Petición aprobada","step_approved_desc":"La aprobación de USCIS permite que el caso avance al procesamiento de visa.","step_nvc":"En NVC","step_nvc_desc":"El caso se reúne, se revisa y se prepara para completar documentos.","step_dq":"Documentarily qualified","step_dq_desc":"NVC ya tiene lo necesario y el caso puede esperar programación de entrevista.","step_current":"Se pone al día","step_current_desc":"Para categorías de preferencia, la fecha de prioridad alcanza el umbral del boletín.","step_interview":"Entrevista programada","step_interview_desc":"El consulado asigna una ventana según su atraso y capacidad."},
}

APP_CSS = """
<style>
@import url("https://fonts.googleapis.com/css2?family=Instrument+Serif&family=JetBrains+Mono:wght@400;500;600&family=Karla:wght@400;500;600;700&display=swap");
:root{--bg:#0a0a0a;--panel:#0e0e0e;--line:#1a1a1a;--text:#cccccc;--muted:#444444;--accent:#caa072;}
html, body, [class*="css"] { font-family:"Karla", sans-serif; }
.stApp { background: var(--bg); color: var(--text); }
[data-testid="stSidebar"] { background: #0a0a0a; border-right: 1px solid var(--line); }
[data-testid="stSidebar"] > div:first-child { padding-top: 0.8rem; }
section[data-testid="stSidebar"] .stSelectbox label, section[data-testid="stSidebar"] .stDateInput label, section[data-testid="stSidebar"] .stSlider label, section[data-testid="stSidebar"] .stRadio label { font-family: "JetBrains Mono", monospace; font-size: 0.64rem !important; letter-spacing: .11em; color: var(--muted) !important; font-weight: 600; }
div[data-baseweb="select"] > div, .stDateInput > div > div { background: var(--panel); border: 1px solid var(--line); }
.stButton > button { width: 100%; background: #fff; color: #000; border: none; border-radius: 0; font-size: 0.76rem; font-weight: 700; letter-spacing: .10em; min-height: 2.7rem; }
.sidebar-brand{ border-bottom:1px solid var(--line); padding-bottom:0.9rem; margin-bottom:0.9rem; }
.brand-kicker{ font-family:"JetBrains Mono", monospace; font-size:.70rem; letter-spacing:.18em; color:#fff; font-weight:600; }
.brand-sub{ font-size:.70rem; color:var(--muted); line-height:1.5; margin-top:.2rem; }
.hero-title{ font-family:"Instrument Serif", serif; font-size:3rem; line-height:1.02; color:#fff; font-weight:400; letter-spacing:-.03em; margin:0; }
.mini-stat{ border:1px solid var(--line); padding:1rem 1.1rem; height:100%; }
.mini-stat .num{ font-family:"Instrument Serif", serif; font-size:2rem; color:#fff; }
.mini-stat .sub{ font-size:.67rem; color:#444; text-transform:uppercase; letter-spacing:.08em; margin-top:.15rem; }
.divider-head{ display:flex; align-items:baseline; justify-content:space-between; margin-bottom:.25rem; border-bottom:1px solid var(--line); padding-bottom:.75rem; }
.kicker{ font-family:"JetBrains Mono", monospace; font-size:.62rem; color:#444; letter-spacing:.10em; text-transform:uppercase; }
.live-pill{ font-family:"JetBrains Mono", monospace; font-size:.60rem; letter-spacing:.14em; color:var(--accent); border:1px solid rgba(202,160,114,.2); padding:.30rem .65rem; }
.metric-shell{ border:1px solid var(--line); padding:.95rem 1rem; height:100%; }
.metric-l{ font-size:.56rem; color:#444; text-transform:uppercase; letter-spacing:.11em; font-weight:600; }
.metric-v{ font-family:"JetBrains Mono", monospace; color:#fff; margin-top:.28rem; }
.section-shell{ border:1px solid var(--line); padding:1rem 1.05rem .8rem 1.05rem; margin-bottom:1rem; }
.consulate-shell{ border:1px solid var(--line); margin-top:1rem; }
.consulate-top{ display:flex; align-items:center; justify-content:space-between; padding:.95rem 1.15rem; border-bottom:1px solid var(--line); background:#0e0e0e; }
.cons-grid{ display:grid; grid-template-columns:1fr 1fr 1fr; }
.cons-cell{ padding:.8rem 1rem; border-right:1px solid var(--line); }
.cons-cell:last-child{ border-right:none; }
.cons-label{ font-size:.56rem; color:#444; text-transform:uppercase; letter-spacing:.09em; font-weight:600; margin-bottom:.2rem; }
.cons-value{ font-size:.75rem; color:#777; line-height:1.55; }
.small-muted{ font-size:.72rem; color:#555; }
</style>
"""

def setup_page(title: str = "Visa Bulletin Forecast"):
    st.set_page_config(page_title=title, page_icon="📍", layout="wide", initial_sidebar_state="expanded")
    st.markdown(APP_CSS, unsafe_allow_html=True)

def get_lang():
    if "lang_code" not in st.session_state:
        st.session_state["lang_code"] = "en"
    return st.session_state["lang_code"], TRANSLATIONS[st.session_state["lang_code"]]

def render_lang_picker():
    current = st.session_state.get("lang_code", "en")
    st.session_state["lang_code"] = st.selectbox("LANGUAGE", list(TRANSLATIONS.keys()), index=list(TRANSLATIONS.keys()).index(current), format_func=lambda k: f'{TRANSLATIONS[k]["flag"]} {TRANSLATIONS[k]["label"]}', key="global_lang_code")
    return get_lang()

def render_sidebar_brand(tr: dict):
    st.markdown(f'<div class="sidebar-brand"><div class="brand-kicker">{tr["brand"]}</div><div class="brand-sub">{tr["sub"]}</div></div>', unsafe_allow_html=True)

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_links(n: int = 13):
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0"
    resp = session.get(VISA_BULLETIN_INDEX, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    out = []
    for anchor in soup.find_all("a", href=True):
        match = re.search(r"visa-bulletin-for-(\w+)-(\d{4})", anchor["href"], re.I)
        if match and match.group(1).lower() in MONTH_MAP:
            url = anchor["href"] if anchor["href"].startswith("http") else BASE_URL + anchor["href"]
            out.append({"mn": match.group(1).lower(), "mi": MONTH_MAP[match.group(1).lower()], "yr": int(match.group(2)), "url": url})
    seen, unique = set(), []
    for item in out:
        key = (item["yr"], item["mi"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    unique.sort(key=lambda x: (x["yr"], x["mi"]), reverse=True)
    return unique[:n]

def parse_date(raw: str) -> Optional[datetime]:
    raw = (raw or "").strip().upper()
    if raw in ("C", "CURRENT", ""):
        return datetime.today()
    if raw in ("U", "UNAVAILABLE"):
        return None
    for fmt in ("%d%b%y", "%d%b%Y", "%d-%b-%y", "%d-%b-%Y", "%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(raw, fmt)
        except Exception:
            continue
    return None

@st.cache_data(ttl=3600, show_spinner=False)
def parse_page(url: str):
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0"
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    tables = soup.find_all("table")
    results = {"final_action": {}, "dates_for_filing": {}}
    for table in tables:
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue
        headers = [h.get_text(strip=True).lower() for h in rows[0].find_all(["th", "td"])]
        prev = table.find_previous(["h2", "h3", "h4", "p", "strong"])
        target = results["dates_for_filing"] if prev and "filing" in prev.get_text(strip=True).lower() else results["final_action"]
        col_map = {}
        for idx, header in enumerate(headers):
            if idx == 0:
                continue
            if "china" in header: col_map[idx] = "china_mainland"
            elif "india" in header: col_map[idx] = "india"
            elif "mexico" in header: col_map[idx] = "mexico"
            elif "philippines" in header: col_map[idx] = "philippines"
            elif any(x in header for x in ["all", "world", "other"]): col_map[idx] = "all"
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
    return results

@st.cache_data(ttl=3600, show_spinner=False)
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
            for category, regions in cats.items():
                for region, cutoff in regions.items():
                    records.append({"bulletin_date": bulletin_date, "table_type": table_type, "category": category, "region": region, "cutoff_raw": cutoff, "cutoff_date": parse_date(cutoff)})
    df = pd.DataFrame(records)
    if not df.empty:
        df.sort_values(["category", "region", "bulletin_date"], inplace=True)
    return df

def movement(df: pd.DataFrame, category: str, region: str, table_type: str) -> pd.DataFrame:
    mask = (df["category"] == category) & (df["region"] == region) & (df["table_type"] == table_type) & df["cutoff_date"].notna()
    out = df.loc[mask].copy().sort_values("bulletin_date")
    out["prev"] = out["cutoff_date"].shift(1)
    out["move"] = (out["cutoff_date"] - out["prev"]).dt.days
    return out

def forecast(df: pd.DataFrame, category: str, region: str, priority_date: datetime, table_type: str) -> dict:
    mv = movement(df, category, region, table_type).dropna(subset=["move"])
    if mv.empty:
        return {"status": "NO_DATA"}
    last_row = mv.iloc[-1]
    last_cutoff = last_row["cutoff_date"]
    last_bulletin = last_row["bulletin_date"]
    days_remaining = (priority_date - last_cutoff).days
    if days_remaining <= 0:
        return {"status": "CURRENT"}
    moves = mv["move"].astype(float).values
    avg_move = float(np.mean(moves))
    std_move = float(np.std(moves, ddof=1)) if len(moves) > 1 else 0.0
    if avg_move <= 0:
        return {"status": "RETROGRESSION"}
    months_est = days_remaining / avg_move
    projected_current = last_bulletin + timedelta(days=months_est * 30.44)
    early_rate = max(avg_move + std_move, avg_move * 0.65)
    late_rate = max(avg_move - std_move, avg_move * 0.25)
    current_early = last_bulletin + timedelta(days=(days_remaining / early_rate) * 30.44)
    current_late = last_bulletin + timedelta(days=(days_remaining / late_rate) * 30.44)
    interview_early = current_early + timedelta(days=60)
    interview_late = current_late + timedelta(days=180)
    return {"status":"OK","days_remaining":int(days_remaining),"avg_move":round(avg_move),"std_move":round(std_move,1),"projected_current":projected_current,"current_early":current_early,"current_late":current_late,"interview_early":interview_early,"interview_late":interview_late,"months_est":max(1,int(round(months_est))),"n":len(moves)}

def build_progression_chart(mv: pd.DataFrame, priority_date: datetime, fc: dict, accent: str):
    mv = mv.copy().dropna(subset=["cutoff_date"])
    fig = go.Figure()
    if fc.get("status") == "OK":
        band_x = [fc["current_early"], fc["current_late"], fc["current_late"], fc["current_early"]]
        band_y = [priority_date - timedelta(days=35), priority_date - timedelta(days=35), priority_date + timedelta(days=35), priority_date + timedelta(days=35)]
        fig.add_trace(go.Scatter(x=band_x, y=band_y, fill="toself", mode="lines", line=dict(color="rgba(0,0,0,0)"), fillcolor="rgba(202,160,114,0.10)", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=mv["bulletin_date"], y=mv["cutoff_date"], mode="lines+markers", line=dict(width=2.6, color="#caa072"), marker=dict(size=6, color="#0a0a0a", line=dict(width=1.5, color="#caa072"))))
    fig.add_hline(y=priority_date, line_color="#c0392b", line_dash="dash", line_width=1.2)
    fig.update_layout(height=380, margin=dict(l=12, r=12, t=8, b=8), paper_bgcolor="#0a0a0a", plot_bgcolor="#0a0a0a", font=dict(color="#777", family="Karla, sans-serif"), xaxis=dict(gridcolor="#1a1a1a", title=None), yaxis=dict(gridcolor="#1a1a1a", title=None))
    return fig
