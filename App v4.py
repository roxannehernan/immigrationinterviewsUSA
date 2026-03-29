
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
    "en": {
        "label": "English", "flag": "🇺🇸", "brand": "VISA FORECAST",
        "sub": "U.S. Department of State · Visa Bulletin Analysis",
        "language": "LANGUAGE", "catType": "CATEGORY", "prefCat": "PREFERENCE", "region": "REGION",
        "consulate": "INTERVIEW LOCATION", "chartType": "CHART", "finalAction": "Final Action",
        "datesForFiling": "Dates for Filing", "priorityDate": "PRIORITY DATE", "confidence": "CONFIDENCE",
        "history": "BULLETINS", "nvcCompleteDate": "NVC COMPLETE DATE", "runBtn": "GENERATE FORECAST",
        "heroTitle": "Visa Bulletin Forecast", "months": "months", "categories": "categories", "consulates": "consulates",
        "liveData": "LIVE", "employmentBased": "Employment", "familyBased": "Family", "immediateRelative": "IR / CR",
        "irNote": "Immediate relative visas are always current.",
        "irExplain": "After NVC complete or documentarily qualified status, the interview depends on the selected consulate wait time.",
        "nvcComplete": "NVC COMPLETE", "avgWaitTime": "WAIT", "interviewStart": "INTERVIEW START", "interviewEnd": "INTERVIEW END",
        "days": "days", "interviewForecast": "INTERVIEW FORECAST", "startingPoint": "STARTING POINT",
        "estimatedWindow": "ESTIMATED WINDOW", "startingPointCopy": "NVC complete or documentarily qualified",
        "estimatedWindowCopy": "based on the selected consulate wait time", "address": "Address", "consulateNote": "Notes",
        "estimatedScheduling": "Estimated scheduling", "mapView": "Open in Maps ↗",
        "daysToCurrent": "DAYS REMAINING", "avgMovement": "AVG. MOVEMENT", "currentBy": "EST. CURRENT",
        "interviewWindow": "INTERVIEW WINDOW", "cutoffProgression": "CUTOFF DATE PROGRESSION",
        "forecast": "Forecast", "movement": "Data", "exportTab": "Export", "bulletinsLoaded": "bulletins",
        "projectedWindow": "PROJECTED INTERVIEW WINDOW", "basedOn": "Based on", "monthsOf": "months of data ·",
        "confidenceWord": "confidence", "becomeCurrent": "Become current", "monthsFromNow": "months from now",
        "interviewSched": "Interview scheduling", "nvcNote": "Includes 2–6 mo NVC buffer",
        "mean": "Mean", "median": "Median", "stddev": "Std dev",
        "bulletinData": "Download bulletin data CSV", "forecastReport": "Download forecast JSON",
        "alreadyCurrent": "This priority date is already current based on the latest available bulletin trend.",
        "notEnough": "Not enough movement data to generate a forecast.",
        "retro": "Recent trend does not support a forward forecast right now.",
        "noData": "No visa bulletin data loaded.", "consulateCapacity": "Consulate capacity can still move this window",
        "timeline": "Timeline", "dataFreshness": "Data freshness", "latestBulletin": "Latest bulletin",
        "lastRefresh": "Loaded now", "source": "Source", "categoryHelp": "Category help",
        "shareSummary": "Share summary", "selectedPost": "Selected post", "fastestPost": "Fastest post",
        "slowestPost": "Slowest post", "regionalAverage": "Regional average", "copyReady": "Copy ready summary",
        "uncertainty": "Higher confidence creates a wider forecast window when historical movement is more volatile.",
        "openSource": "travel.state.gov", "faq": "FAQ", "guide": "Process guide",
        "faq_pd_q": "What is a priority date?", "faq_pd_a": "The priority date is the placeholder date used to determine when a case can move forward for family and employment categories.",
        "faq_fa_q": "What is Final Action vs Dates for Filing?", "faq_fa_a": "Final Action usually controls when a visa can actually be issued. Dates for Filing can sometimes allow earlier document submission.",
        "faq_ir_q": "Why are IR and CR different?", "faq_ir_a": "Immediate relative categories are always current, so timing depends more on NVC completion and consulate scheduling than bulletin movement.",
        "faq_consulate_q": "Why do consulates change timing?", "faq_consulate_a": "Consulate capacity, local demand, staffing, and interview volume can all shift scheduling windows.",
        "guide_title": "How this process works", "guide_intro": "Use this as a directional guide so users understand what each stage means before trusting the forecast.",
        "step_filed": "Case filed", "step_filed_desc": "A petition is submitted and enters USCIS review.",
        "step_approved": "Petition approved", "step_approved_desc": "USCIS approval allows the case to move toward visa processing.",
        "step_nvc": "At NVC", "step_nvc_desc": "The case is gathered, reviewed, and prepared for documentary completion.",
        "step_dq": "Documentarily qualified", "step_dq_desc": "NVC has what it needs and the case can wait for interview scheduling.",
        "step_current": "Becomes current", "step_current_desc": "For preference categories, the priority date reaches the bulletin threshold.",
        "step_interview": "Interview scheduled", "step_interview_desc": "The consulate assigns an interview window based on backlog and capacity.",
    },
    "es": {
        "label": "Español", "flag": "🇲🇽", "brand": "VISA FORECAST",
        "sub": "Depto. de Estado · Boletín de Visas",
        "language": "IDIOMA", "catType": "CATEGORÍA", "prefCat": "PREFERENCIA", "region": "REGIÓN",
        "consulate": "LUGAR DE ENTREVISTA", "chartType": "GRÁFICO", "finalAction": "Acción Final",
        "datesForFiling": "Fechas de Presentación", "priorityDate": "FECHA DE PRIORIDAD", "confidence": "CONFIANZA",
        "history": "BOLETINES", "nvcCompleteDate": "FECHA DE NVC COMPLETE", "runBtn": "GENERAR PRONÓSTICO",
        "heroTitle": "Pronóstico del Boletín de Visas", "months": "meses", "categories": "categorías", "consulates": "consulados",
        "liveData": "VIVO", "employmentBased": "Empleo", "familyBased": "Familia", "immediateRelative": "IR / CR",
        "irNote": "Las visas IR/CR siempre están al día.",
        "irExplain": "Después de NVC complete o documentarily qualified, la entrevista depende del tiempo de espera del consulado seleccionado.",
        "nvcComplete": "NVC COMPLETE", "avgWaitTime": "ESPERA", "interviewStart": "ENTREVISTA INICIO", "interviewEnd": "ENTREVISTA FIN",
        "days": "días", "interviewForecast": "PRONÓSTICO DE ENTREVISTA", "startingPoint": "PUNTO DE PARTIDA",
        "estimatedWindow": "VENTANA ESTIMADA", "startingPointCopy": "NVC complete o documentarily qualified",
        "estimatedWindowCopy": "basada en la espera del consulado seleccionado", "address": "Dirección", "consulateNote": "Notas",
        "estimatedScheduling": "Programación estimada", "mapView": "Abrir en Maps ↗",
        "daysToCurrent": "DÍAS RESTANTES", "avgMovement": "MOV. PROM.", "currentBy": "EST. AL DÍA",
        "interviewWindow": "VENTANA DE ENTREVISTA", "cutoffProgression": "PROGRESIÓN DE FECHA LÍMITE",
        "forecast": "Pronóstico", "movement": "Datos", "exportTab": "Exportar", "bulletinsLoaded": "boletines",
        "projectedWindow": "VENTANA PROYECTADA DE ENTREVISTA", "basedOn": "Basado en", "monthsOf": "meses de datos ·",
        "confidenceWord": "confianza", "becomeCurrent": "Ponerse al día", "monthsFromNow": "meses desde ahora",
        "interviewSched": "Programación de entrevista", "nvcNote": "Incluye 2–6 meses de buffer NVC",
        "mean": "Media", "median": "Mediana", "stddev": "Desv. est.",
        "bulletinData": "Descargar datos CSV", "forecastReport": "Descargar pronóstico JSON",
        "alreadyCurrent": "Esta fecha de prioridad ya está al día según la tendencia más reciente del boletín.",
        "notEnough": "No hay suficiente movimiento para generar un pronóstico.",
        "retro": "La tendencia reciente no permite un pronóstico hacia adelante en este momento.",
        "noData": "No se cargaron datos del boletín de visas.", "consulateCapacity": "La capacidad del consulado todavía puede mover esta ventana",
        "timeline": "Cronología", "dataFreshness": "Actualización de datos", "latestBulletin": "Último boletín",
        "lastRefresh": "Cargado ahora", "source": "Fuente", "categoryHelp": "Ayuda de categoría",
        "shareSummary": "Resumen para compartir", "selectedPost": "Consulado seleccionado", "fastestPost": "Más rápido",
        "slowestPost": "Más lento", "regionalAverage": "Promedio regional", "copyReady": "Resumen listo para copiar",
        "uncertainty": "Una confianza más alta crea una ventana más amplia cuando el movimiento histórico es más volátil.",
        "openSource": "travel.state.gov", "faq": "Preguntas frecuentes", "guide": "Guía del proceso",
        "faq_pd_q": "¿Qué es la fecha de prioridad?", "faq_pd_a": "La fecha de prioridad es la fecha que reserva el lugar del caso para categorías familiares y de empleo.",
        "faq_fa_q": "¿Qué es Acción Final vs Fechas de Presentación?", "faq_fa_a": "Acción Final normalmente controla cuándo se puede emitir la visa. Fechas de Presentación a veces permite enviar documentos antes.",
        "faq_ir_q": "¿Por qué IR y CR son diferentes?", "faq_ir_a": "Las categorías de familiares inmediatos siempre están al día, así que el tiempo depende más de NVC complete y del consulado que del boletín.",
        "faq_consulate_q": "¿Por qué cambian los tiempos del consulado?", "faq_consulate_a": "La capacidad, la demanda local, el personal y el volumen de entrevistas pueden cambiar la programación.",
        "guide_title": "Cómo funciona este proceso", "guide_intro": "Úsalo como guía direccional para entender cada etapa antes de confiar en el pronóstico.",
        "step_filed": "Caso presentado", "step_filed_desc": "Se presenta una petición y entra a revisión de USCIS.",
        "step_approved": "Petición aprobada", "step_approved_desc": "La aprobación de USCIS permite que el caso avance al procesamiento de visa.",
        "step_nvc": "En NVC", "step_nvc_desc": "El caso se reúne, se revisa y se prepara para completar documentos.",
        "step_dq": "Documentarily qualified", "step_dq_desc": "NVC ya tiene lo necesario y el caso puede esperar programación de entrevista.",
        "step_current": "Se pone al día", "step_current_desc": "Para categorías de preferencia, la fecha de prioridad alcanza el umbral del boletín.",
        "step_interview": "Entrevista programada", "step_interview_desc": "El consulado asigna una ventana según su atraso y capacidad.",
    },
}

REQUIRED_TRANSLATION_DEFAULTS = TRANSLATIONS["en"].copy()
for lang_key, bundle in TRANSLATIONS.items():
    for k, v in REQUIRED_TRANSLATION_DEFAULTS.items():
        bundle.setdefault(k, v)

MONTH_MAP = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}

st.markdown("""
<style>
@import url("https://fonts.googleapis.com/css2?family=Instrument+Serif&family=JetBrains+Mono:wght@400;500;600&family=Karla:wght@400;500;600;700&display=swap");
:root{--bg:#0a0a0a;--panel:#0e0e0e;--line:#1a1a1a;--text:#cccccc;--muted:#444444;--accent:#caa072;}
html, body, [class*="css"] { font-family:"Karla", sans-serif; }
.stApp { background: var(--bg); color: var(--text); }
[data-testid="stSidebar"] { background: #0a0a0a; border-right: 1px solid var(--line); }
[data-testid="stSidebar"] > div:first-child { padding-top: 0.8rem; }
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stDateInput label,
section[data-testid="stSidebar"] .stSlider label,
section[data-testid="stSidebar"] .stRadio label {
    font-family: "JetBrains Mono", monospace;
    font-size: 0.64rem !important;
    letter-spacing: .11em;
    color: var(--muted) !important;
    font-weight: 600;
}
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
""", unsafe_allow_html=True)

def accent_for_case(case_type: str) -> str:
    if case_type == "ir":
        return "#2980b9"
    if case_type == "family":
        return "#8e44ad"
    return "#caa072"

def parse_wait_time(wait_str: str) -> tuple[int, int]:
    nums = re.findall(r"\d+", wait_str or "")
    if len(nums) >= 2:
        return int(nums[0]), int(nums[1])
    if len(nums) == 1:
        val = int(nums[0])
        return val, val
    return 60, 120

def parse_wait_mid(wait_str: str) -> int:
    low, high = parse_wait_time(wait_str)
    return int(round((low + high) / 2))

def metric_block(label: str, value: str, border_color: Optional[str] = None):
    border_style = f"border-left:3px solid {border_color};" if border_color else ""
    st.markdown(
        f'<div class="metric-shell" style="{border_style}"><div class="metric-l">{label}</div><div class="metric-v">{value}</div></div>',
        unsafe_allow_html=True,
    )

def consulate_block(consulate: dict, est_early: Optional[datetime], est_late: Optional[datetime], accent: str, tr: dict):
    footer = ""
    if est_early and est_late:
        footer = (
            f'<div style="border-top:1px solid #1a1a1a;padding:.8rem 1.15rem;display:flex;align-items:center;justify-content:space-between;">'
            f'<div class="cons-label" style="margin:0;">{tr["estimatedScheduling"]}</div>'
            f'<div style="font-family:JetBrains Mono, monospace;font-size:.86rem;color:{accent};">{est_early.strftime("%b %Y")} — {est_late.strftime("%b %Y")}</div>'
            f'</div>'
        )
    st.markdown(
        f'<div class="consulate-shell">'
        f'<div class="consulate-top">'
        f'<div style="display:flex;align-items:center;gap:.65rem;"><div style="font-size:1.15rem;">{consulate.get("flag","📍")}</div>'
        f'<div><div style="font-family:Instrument Serif, serif;font-size:1.15rem;color:#fff;line-height:1;">{consulate["city"]}</div>'
        f'<div style="font-family:JetBrains Mono, monospace;font-size:.62rem;color:#444;margin-top:.18rem;">U.S. {consulate["name"]}</div></div></div>'
        f'<a href="https://www.google.com/maps/search/?api=1&query={consulate["lat"]},{consulate["lng"]}" target="_blank" style="font-family:JetBrains Mono, monospace;font-size:.62rem;color:{accent};text-decoration:none;border:1px solid {accent}33;padding:.35rem .7rem;letter-spacing:.05em;">{tr["mapView"]}</a>'
        f'</div>'
        f'<div class="cons-grid">'
        f'<div class="cons-cell"><div class="cons-label">{tr["address"]}</div><div class="cons-value">{consulate["addr"]}</div></div>'
        f'<div class="cons-cell"><div class="cons-label">{tr["avgWaitTime"]}</div><div class="cons-value" style="color:{accent};">{consulate["wait"]}</div></div>'
        f'<div class="cons-cell"><div class="cons-label">{tr["consulateNote"]}</div><div class="cons-value">{consulate["note"]}</div></div>'
        f'</div>{footer}</div>',
        unsafe_allow_html=True,
    )

def build_timeline_html(items: list[dict], accent: str) -> str:
    parts = []
    for idx, item in enumerate(items):
        connector = '<div style="width:2px;flex:1;background:#222;min-height:36px;margin-top:6px;"></div>' if idx < len(items) - 1 else ''
        parts.append(
            f'<div style="display:flex;align-items:flex-start;gap:.8rem;flex:1;">'
            f'<div style="display:flex;flex-direction:column;align-items:center;min-width:16px;">'
            f'<div style="width:12px;height:12px;border-radius:999px;background:{accent};margin-top:4px;"></div>{connector}</div>'
            f'<div style="padding-bottom:.6rem;">'
            f'<div class="metric-l" style="margin-bottom:.2rem;">{item["label"]}</div>'
            f'<div style="font-family:JetBrains Mono, monospace;color:#fff;font-size:.9rem;">{item["value"]}</div>'
            f'<div class="small-muted" style="margin-top:.15rem;">{item.get("note","")}</div>'
            f'</div></div>'
        )
    return '<div class="section-shell">' + ''.join(parts) + '</div>'

def consulate_comparison(posts: list[dict], selected_post: Optional[dict]) -> Optional[dict]:
    if not posts:
        return None
    ranked = sorted(posts, key=lambda p: parse_wait_mid(p["wait"]))
    avg = round(sum(parse_wait_mid(p["wait"]) for p in posts) / len(posts))
    return {
        "selected": (selected_post["city"] + " · " + selected_post["wait"]) if selected_post else "—",
        "fastest": ranked[0]["city"] + " · " + ranked[0]["wait"],
        "slowest": ranked[-1]["city"] + " · " + ranked[-1]["wait"],
        "average": f"{avg} days",
    }

def category_help_text(category: str) -> str:
    mapping = {
        "F1": "Family first preference for unmarried sons and daughters of U.S. citizens.",
        "F2A": "Spouses and children of lawful permanent residents.",
        "F2B": "Unmarried adult sons and daughters of lawful permanent residents.",
        "F3": "Married sons and daughters of U.S. citizens.",
        "F4": "Brothers and sisters of adult U.S. citizens.",
        "EB1": "Priority workers including extraordinary ability and multinational managers.",
        "EB2": "Advanced degree professionals and exceptional ability.",
        "EB3": "Skilled workers, professionals, and some other workers.",
        "EB4": "Special immigrants.",
        "EB5": "Immigrant investors.",
        "IR1": "Spouse of a U.S. citizen.",
        "CR1": "Conditional spouse of a U.S. citizen.",
        "IR2": "Child of a U.S. citizen.",
        "IR5": "Parent of a U.S. citizen.",
        "K1": "Fiancé(e) visa path leading to adjustment after entry.",
    }
    return mapping.get(category, "")

def build_guide_html(tr: dict, case_type: str) -> str:
    steps = [
        (tr["step_filed"], tr["step_filed_desc"]),
        (tr["step_approved"], tr["step_approved_desc"]),
        (tr["step_nvc"], tr["step_nvc_desc"]),
    ]
    if case_type != "ir":
        steps.append((tr["step_current"], tr["step_current_desc"]))
    steps.extend([
        (tr["step_dq"], tr["step_dq_desc"]),
        (tr["step_interview"], tr["step_interview_desc"]),
    ])
    blocks = ''.join(
        f'<div style="padding:.9rem 1rem;border-top:1px solid #1a1a1a;"><div class="metric-l" style="margin-bottom:.25rem;">{title}</div><div class="small-muted">{desc}</div></div>'
        for title, desc in steps
    )
    return (
        f'<div class="section-shell"><div style="font-family:Instrument Serif, serif;font-size:1.2rem;color:#fff;margin-bottom:.35rem;">{tr["guide_title"]}</div>'
        f'<div class="small-muted" style="margin-bottom:.65rem;">{tr["guide_intro"]}</div>{blocks}</div>'
    )

def render_faq_and_guide(tr: dict, case_type: str):
    faq_tab, guide_tab = st.tabs([tr["faq"], tr["guide"]])
    with faq_tab:
        with st.expander(tr["faq_pd_q"]):
            st.write(tr["faq_pd_a"])
        with st.expander(tr["faq_fa_q"]):
            st.write(tr["faq_fa_a"])
        with st.expander(tr["faq_ir_q"]):
            st.write(tr["faq_ir_a"])
        with st.expander(tr["faq_consulate_q"]):
            st.write(tr["faq_consulate_a"])
    with guide_tab:
        st.markdown(build_guide_html(tr, case_type), unsafe_allow_html=True)

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
    seen = set()
    unique = []
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
            if "china" in header:
                col_map[idx] = "china_mainland"
            elif "india" in header:
                col_map[idx] = "india"
            elif "mexico" in header:
                col_map[idx] = "mexico"
            elif "philippines" in header:
                col_map[idx] = "philippines"
            elif any(x in header for x in ["all", "world", "other"]):
                col_map[idx] = "all"

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
                    records.append(
                        {
                            "bulletin_date": bulletin_date,
                            "table_type": table_type,
                            "category": category,
                            "region": region,
                            "cutoff_raw": cutoff,
                            "cutoff_date": parse_date(cutoff),
                        }
                    )
    df = pd.DataFrame(records)
    if not df.empty:
        df.sort_values(["category", "region", "bulletin_date"], inplace=True)
    return df

def movement(df: pd.DataFrame, category: str, region: str, table_type: str) -> pd.DataFrame:
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

def forecast(df: pd.DataFrame, category: str, region: str, priority_date: datetime, table_type: str, confidence: float) -> dict:
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
        "std_move": round(std_move, 1),
        "projected_current": projected_current,
        "current_early": current_early,
        "current_late": current_late,
        "interview_early": interview_early,
        "interview_late": interview_late,
        "months_est": max(1, int(round(months_est))),
        "n": len(moves),
    }

def build_progression_chart(mv: pd.DataFrame, priority_date: datetime, fc: dict, accent: str):
    mv = mv.copy().dropna(subset=["cutoff_date"])
    fig = go.Figure()
    if fc.get("status") == "OK":
        band_x = [fc["current_early"], fc["current_late"], fc["current_late"], fc["current_early"]]
        band_y = [priority_date - timedelta(days=35), priority_date - timedelta(days=35), priority_date + timedelta(days=35), priority_date + timedelta(days=35)]
        fig.add_trace(go.Scatter(x=band_x, y=band_y, fill="toself", mode="lines", line=dict(color="rgba(0,0,0,0)"), fillcolor="rgba(202,160,114,0.10)", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=mv["bulletin_date"], y=mv["cutoff_date"], mode="lines+markers", line=dict(width=2.6, color=accent), marker=dict(size=6, color="#0a0a0a", line=dict(width=1.5, color=accent))))
    fig.add_hline(y=priority_date, line_color="#c0392b", line_dash="dash", line_width=1.2)
    fig.update_layout(height=380, margin=dict(l=12, r=12, t=8, b=8), paper_bgcolor="#0a0a0a", plot_bgcolor="#0a0a0a", font=dict(color="#777", family="Karla, sans-serif"), xaxis=dict(gridcolor="#1a1a1a", title=None), yaxis=dict(gridcolor="#1a1a1a", title=None))
    return fig

def build_consulate_map(posts: list[dict], selected_id: str, accent: str):
    if not posts:
        return go.Figure()
    df_map = pd.DataFrame(posts)
    df_map["size"] = np.where(df_map["id"] == selected_id, 18, 11)
    fig = go.Figure()
    fig.add_trace(go.Scattermap(lat=df_map["lat"], lon=df_map["lng"], mode="markers", text=df_map["city"] + " · " + df_map["wait"], hovertemplate="%{text}<extra></extra>", marker=dict(size=df_map["size"], color=np.where(df_map["id"] == selected_id, accent, "#7a7a7a"))))
    fig.update_layout(height=340, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="#0a0a0a", map=dict(style="carto-darkmatter", zoom=1.35, center=dict(lat=float(df_map["lat"].mean()), lon=float(df_map["lng"].mean()))), font=dict(color="#777"))
    return fig

with st.sidebar:
    lang_code = st.selectbox("LANGUAGE", list(TRANSLATIONS.keys()), format_func=lambda k: f'{TRANSLATIONS[k]["flag"]} {TRANSLATIONS[k]["label"]}', key="lang_code")
    tr = TRANSLATIONS[lang_code]

    st.markdown(f'<div class="sidebar-brand"><div class="brand-kicker">{tr["brand"]}</div><div class="brand-sub">{tr["sub"]}</div></div>', unsafe_allow_html=True)

    case_type = st.radio(
        tr["catType"],
        ["ir", "family", "employment"],
        horizontal=True,
        format_func=lambda v: tr["immediateRelative"] if v == "ir" else tr["familyBased"] if v == "family" else tr["employmentBased"],
        key="case_type",
    )

    if case_type == "ir":
        category = st.selectbox(tr["prefCat"], IR_CATEGORIES, format_func=lambda c: CATEGORY_LABELS.get(c, c), key="ir_category")
    elif case_type == "family":
        category = st.selectbox(tr["prefCat"], FAMILY_CATEGORIES, format_func=lambda c: CATEGORY_LABELS.get(c, c), key="family_category")
    else:
        category = st.selectbox(tr["prefCat"], EMPLOYMENT_CATEGORIES, format_func=lambda c: CATEGORY_LABELS.get(c, c), key="employment_category")

    region_label = st.selectbox(tr["region"], list(CHARGEABILITY_REGIONS.keys()), key="region_label")
    region = CHARGEABILITY_REGIONS[region_label]
    posts = CONSULATES.get(region, [])
    post_label = st.selectbox(tr["consulate"], [f'{p["city"]} — {p["name"]}' for p in posts], key="post_label") if posts else None
    selected_post = next((p for p in posts if f'{p["city"]} — {p["name"]}' == post_label), None)

    if case_type != "ir":
        table_type = st.selectbox(tr["chartType"], ["final_action", "dates_for_filing"], format_func=lambda x: tr["finalAction"] if x == "final_action" else tr["datesForFiling"], key="table_type")
        priority_date = st.date_input(tr["priorityDate"], datetime(2022, 3, 15), key="priority_date")
        confidence = 0.9
        history_months = 13
        nvc_complete_date = None
    else:
        table_type = "final_action"
        priority_date = datetime.today().date()
        confidence = 0.8
        history_months = 13
        nvc_complete_date = st.date_input(tr["nvcCompleteDate"], datetime.today().date(), key="nvc_complete_date")

    run = st.button(tr["runBtn"], use_container_width=True, type="primary")

accent = accent_for_case(case_type)

st.markdown(f'<div style="max-width:620px;margin-bottom:2rem;"><h1 class="hero-title">{tr["heroTitle"]}</h1></div>', unsafe_allow_html=True)

if "has_run" not in st.session_state:
    st.session_state["has_run"] = False
if run:
    st.session_state["has_run"] = True

if not st.session_state["has_run"]:
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div class="mini-stat"><div class="num">12+</div><div class="sub">{tr["months"]}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="mini-stat"><div class="num">15</div><div class="sub">{tr["categories"]}</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="mini-stat"><div class="num">80+</div><div class="sub">{tr["consulates"]}</div></div>', unsafe_allow_html=True)
    st.stop()

latest_bulletin_dt = datetime.today()
try:
    df_latest = fetch_bulletins(3)
    if not df_latest.empty:
        latest_bulletin_dt = df_latest["bulletin_date"].max()
except Exception:
    latest_bulletin_dt = datetime.today()

if case_type == "ir":
    st.markdown(
        f'<div class="divider-head"><div><div style="font-family:Instrument Serif, serif;font-size:1.9rem;color:#fff;">{CATEGORY_LABELS.get(category, category)}</div>'
        f'<div class="kicker">{region_label}{" · " + selected_post["city"] if selected_post else ""}</div></div><div class="live-pill">{tr["liveData"]}</div></div>',
        unsafe_allow_html=True,
    )

    wait_early, wait_late = parse_wait_time(selected_post["wait"]) if selected_post else (60, 120)
    nvc_complete_dt = datetime.combine(nvc_complete_date, datetime.min.time())
    interview_early = nvc_complete_dt + timedelta(days=wait_early)
    interview_late = nvc_complete_dt + timedelta(days=wait_late)

    st.markdown(f'<div class="section-shell"><div style="font-family:Instrument Serif, serif;font-size:1.25rem;color:#fff;margin-bottom:.45rem;">{tr["irNote"]}</div><div class="small-muted">{tr["irExplain"]}</div></div>', unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    with m1: metric_block(tr["nvcComplete"], nvc_complete_dt.strftime("%b %d, %Y"), "#3498db")
    with m2: metric_block(tr["avgWaitTime"], f"{wait_early}–{wait_late} {tr['days']}", "#2ecc71")
    with m3: metric_block(tr["interviewStart"], interview_early.strftime("%b %Y"), "#f39c12")
    with m4: metric_block(tr["interviewEnd"], interview_late.strftime("%b %Y"), "#e74c3c")

    st.markdown(f'<div class="kicker" style="margin-bottom:.5rem;">{tr["timeline"]}</div>', unsafe_allow_html=True)
    timeline_items = [
        {"label": tr["nvcComplete"], "value": nvc_complete_dt.strftime("%b %d, %Y"), "note": tr["startingPointCopy"]},
        {"label": tr["avgWaitTime"], "value": f"{wait_early}–{wait_late} {tr['days']}", "note": tr["estimatedWindowCopy"]},
        {"label": tr["interviewWindow"], "value": f"{interview_early.strftime('%b %d, %Y')} — {interview_late.strftime('%b %d, %Y')}", "note": tr["estimatedScheduling"]},
    ]
    st.markdown(build_timeline_html(timeline_items, accent), unsafe_allow_html=True)

    comp = consulate_comparison(posts, selected_post)
    if comp:
        c1, c2, c3, c4 = st.columns(4)
        with c1: metric_block(tr["selectedPost"], comp["selected"])
        with c2: metric_block(tr["fastestPost"], comp["fastest"])
        with c3: metric_block(tr["slowestPost"], comp["slowest"])
        with c4: metric_block(tr["regionalAverage"], comp["average"])

    with st.expander(tr["shareSummary"]):
        summary = f"{CATEGORY_LABELS.get(category, category)} | {region_label} | {selected_post['city'] if selected_post else '—'} | NVC complete: {nvc_complete_dt.strftime('%Y-%m-%d')} | Interview estimate: {interview_early.strftime('%Y-%m-%d')} to {interview_late.strftime('%Y-%m-%d')}"
        st.text_area(tr["copyReady"], summary, height=90)

    if selected_post:
        consulate_block(selected_post, interview_early, interview_late, accent, tr)
        st.plotly_chart(build_consulate_map(posts, selected_post["id"], accent), use_container_width=True)

    st.markdown(f'<div class="kicker" style="margin-bottom:.5rem;">{tr["dataFreshness"]}</div>', unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)
    with f1: metric_block(tr["latestBulletin"], latest_bulletin_dt.strftime("%b %Y"))
    with f2: metric_block(tr["lastRefresh"], datetime.now().strftime("%Y-%m-%d %H:%M"))
    with f3: metric_block(tr["source"], tr["openSource"])

    render_faq_and_guide(tr, case_type)

    st.markdown('<div style="position:fixed;bottom:10px;right:20px;font-size:10px;color:#555;font-family:JetBrains Mono, monospace;">github.com/roxannehernan</div>', unsafe_allow_html=True)
    st.stop()

df = fetch_bulletins(history_months)
if df.empty:
    st.error(tr["noData"])
    st.stop()

latest_bulletin_dt = df["bulletin_date"].max()
priority_dt = datetime.combine(priority_date, datetime.min.time())
fc = forecast(df, category, region, priority_dt, table_type, confidence)
mv = movement(df, category, region, table_type)

st.markdown(
    f'<div class="divider-head"><div><div style="font-family:Instrument Serif, serif;font-size:1.9rem;color:#fff;">{region_label} · {CATEGORY_LABELS.get(category, category)}</div>'
    f'<div class="kicker">{selected_post["city"] if selected_post else ""} · {history_months} {tr["bulletinsLoaded"]}</div></div><div class="live-pill">{tr["liveData"]}</div></div>',
    unsafe_allow_html=True,
)

tab_forecast, tab_data, tab_export = st.tabs([tr["forecast"], tr["movement"], tr["exportTab"]])

with tab_forecast:
    if fc["status"] == "CURRENT":
        st.success(tr["alreadyCurrent"])
    elif fc["status"] == "NO_DATA":
        st.warning(tr["notEnough"])
    elif fc["status"] == "RETROGRESSION":
        st.warning(tr["retro"])

    if fc["status"] == "OK":
        m1, m2, m3, m4 = st.columns(4)
        with m1: metric_block(tr["daysToCurrent"], f'{fc["days_remaining"]:,}')
        with m2: metric_block("TREND", f'{fc["avg_move"]} d/mo')
        with m3: metric_block(tr["currentBy"], fc["projected_current"].strftime("%b %Y"))
        with m4: metric_block(tr["interviewWindow"], f'{fc["interview_early"].strftime("%b %Y")} — {fc["interview_late"].strftime("%b %Y")}')
        st.markdown('<div class="small-muted" style="margin:.55rem 0 1rem 0;">Forecast shows an expected timeline based on recent movement and scheduling patterns.</div>', unsafe_allow_html=True)

    st.markdown(f'<div class="section-shell"><div class="kicker" style="margin-bottom:.6rem;">{tr["cutoffProgression"]}</div>', unsafe_allow_html=True)
    st.plotly_chart(build_progression_chart(mv, priority_dt, fc, accent), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if selected_post and fc["status"] == "OK":
        consulate_block(selected_post, fc["interview_early"], fc["interview_late"], accent, tr)
        st.plotly_chart(build_consulate_map(posts, selected_post["id"], accent), use_container_width=True)

    if fc["status"] == "OK":
        st.markdown(
            f'<div class="section-shell">'
            f'<div style="font-family:Instrument Serif, serif;font-size:1.2rem;color:#fff;margin-bottom:.6rem;">{tr["forecast"]}</div>'
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:1px;">'
            f'<div style="background:#111;padding:.95rem 1rem;">'
            f'<div class="metric-l">{tr["becomeCurrent"]}</div>'
            f'<div style="font-family:JetBrains Mono, monospace;color:#fff;margin-top:.3rem;">{fc["projected_current"].strftime("%B %Y")}</div>'
            f'<div class="small-muted" style="margin-top:.15rem;">{fc["months_est"]} {tr["monthsFromNow"]}</div>'
            f'</div>'
            f'<div style="background:#111;padding:.95rem 1rem;">'
            f'<div class="metric-l">{tr["interviewWindow"]}</div>'
            f'<div style="font-family:JetBrains Mono, monospace;color:{accent};margin-top:.3rem;">{fc["interview_early"].strftime("%b %Y")} — {fc["interview_late"].strftime("%b %Y")}</div>'
            f'<div class="small-muted" style="margin-top:.15rem;">{tr["consulateCapacity"]}</div>'
            f'</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        st.markdown(f'<div class="kicker" style="margin-bottom:.5rem;">{tr["timeline"]}</div>', unsafe_allow_html=True)
        timeline_items = [
            {"label": tr["priorityDate"], "value": priority_dt.strftime("%b %d, %Y"), "note": CATEGORY_LABELS.get(category, category)},
            {"label": "CURRENT ESTIMATE", "value": fc["projected_current"].strftime("%b %Y"), "note": tr["becomeCurrent"]},
            {"label": tr["interviewWindow"], "value": f'{fc["interview_early"].strftime("%b %Y")} — {fc["interview_late"].strftime("%b %Y")}', "note": tr["interviewSched"]},
        ]
        st.markdown(build_timeline_html(timeline_items, accent), unsafe_allow_html=True)

        comp = consulate_comparison(posts, selected_post)
        if comp:
            c1, c2, c3, c4 = st.columns(4)
            with c1: metric_block(tr["selectedPost"], comp["selected"])
            with c2: metric_block(tr["fastestPost"], comp["fastest"])
            with c3: metric_block(tr["slowestPost"], comp["slowest"])
            with c4: metric_block(tr["regionalAverage"], comp["average"])

        with st.expander(tr["categoryHelp"]):
            st.write(category_help_text(category))

        with st.expander(tr["shareSummary"]):
            summary = f"{CATEGORY_LABELS.get(category, category)} | {region_label} | {selected_post['city'] if selected_post else '—'} | Priority date: {priority_dt.strftime('%Y-%m-%d')} | Current estimate: {fc['projected_current'].strftime('%Y-%m-%d')} | Interview estimate: {fc['interview_early'].strftime('%Y-%m-%d')} to {fc['interview_late'].strftime('%Y-%m-%d')}"
            st.text_area(tr["copyReady"], summary, height=90)

        st.markdown(f'<div class="kicker" style="margin-bottom:.5rem;">{tr["dataFreshness"]}</div>', unsafe_allow_html=True)
        f1, f2, f3 = st.columns(3)
        with f1: metric_block(tr["latestBulletin"], latest_bulletin_dt.strftime("%b %Y"))
        with f2: metric_block(tr["lastRefresh"], datetime.now().strftime("%Y-%m-%d %H:%M"))
        with f3: metric_block(tr["source"], tr["openSource"])

        render_faq_and_guide(tr, case_type)

with tab_data:
    data_df = mv[["bulletin_date", "cutoff_date", "move"]].copy()
    data_df.columns = ["Month", "Cutoff", "Movement"]
    st.dataframe(data_df, hide_index=True, use_container_width=True)
    if fc["status"] == "OK":
        s1, s2, s3 = st.columns(3)
        with s1: metric_block(tr["mean"], f'{fc["avg_move"]}d')
        with s2: metric_block(tr["stddev"], f'{fc["std_move"]}d')
        with s3:
            med = int(pd.Series(mv["move"].dropna()).median()) if not mv["move"].dropna().empty else 0
            metric_block(tr["median"], f'{med}d')

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
    st.download_button(tr["bulletinData"], csv_data, file_name="visa_bulletin_data.csv", mime="text/csv")
    st.download_button(tr["forecastReport"], json_data, file_name="visa_forecast.json", mime="application/json")

st.markdown('<div style="position:fixed;bottom:10px;right:20px;font-size:10px;color:#555;font-family:JetBrains Mono, monospace;">github.com/roxannehernan</div>', unsafe_allow_html=True)
