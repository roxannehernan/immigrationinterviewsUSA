
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

st.set_page_config(page_title="Visa Bulletin Forecast", page_icon="📍", layout="wide", initial_sidebar_state="expanded")

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
        {"id": "fra", "name": "Consulate Frankfurt", "city": "Frankfurt", "addr": "Gießener Str. 30", "lat": 50.12, "lng": 8.68, "note": "Germany — high EB", "wait": "30–45 days", "flag": "🇩🇪"},
        {"id": "mtl", "name": "Consulate Montreal", "city": "Montreal", "addr": "Sainte-Catherine O", "lat": 45.50, "lng": -73.57, "note": "Primary Canadian IV", "wait": "30–60 days", "flag": "🇨🇦"},
        {"id": "syd", "name": "Consulate Sydney", "city": "Sydney", "addr": "19-29 Martin Pl", "lat": -33.87, "lng": 151.21, "note": "AU/NZ/Pacific", "wait": "30–45 days", "flag": "🇦🇺"},
        {"id": "acc", "name": "Embassy Accra", "city": "Accra", "addr": "Fourth Circular Rd", "lat": 5.57, "lng": -0.18, "note": "West Africa hub", "wait": "60–120 days", "flag": "🇬🇭"},
        {"id": "nbo", "name": "Embassy Nairobi", "city": "Nairobi", "addr": "United Nations Ave", "lat": -1.24, "lng": 36.81, "note": "East Africa hub", "wait": "60–90 days", "flag": "🇰🇪"},
        {"id": "dxb", "name": "Consulate Dubai", "city": "Dubai", "addr": "Al Seef Rd", "lat": 25.26, "lng": 55.30, "note": "UAE", "wait": "30–60 days", "flag": "🇦🇪"},
        {"id": "bkk", "name": "Embassy Bangkok", "city": "Bangkok", "addr": "95 Wireless Rd", "lat": 13.74, "lng": 100.55, "note": "Thailand/Laos/Cambodia", "wait": "45–90 days", "flag": "🇹🇭"},
        {"id": "sto", "name": "Embassy Santo Domingo", "city": "Santo Domingo", "addr": "Av. Colombia #57", "lat": 18.46, "lng": -69.93, "note": "High family-based", "wait": "60–120 days", "flag": "🇩🇴"},
        {"id": "bog", "name": "Embassy Bogotá", "city": "Bogotá", "addr": "Calle 24 Bis #48-50", "lat": 4.64, "lng": -74.09, "note": "Colombia", "wait": "45–90 days", "flag": "🇨🇴"},
        {"id": "jnb", "name": "Consulate Johannesburg", "city": "Johannesburg", "addr": "1 Sandton Dr", "lat": -26.11, "lng": 28.06, "note": "Southern Africa", "wait": "30–60 days", "flag": "🇿🇦"},
        {"id": "war", "name": "Embassy Warsaw", "city": "Warsaw", "addr": "Aleje Ujazdowskie", "lat": 52.22, "lng": 21.02, "note": "Poland", "wait": "30–45 days", "flag": "🇵🇱"},
    ],
}

MONTH_MAP = {"january":1,"february":2,"march":3,"april":4,"may":5,"june":6,"july":7,"august":8,"september":9,"october":10,"november":11,"december":12}

TRANSLATIONS = {'en': {'label': 'English', 'flag': '🇺🇸', 'brand': 'VISA FORECAST', 'sub': 'U.S. Department of State · Visa Bulletin Analysis', 'language': 'LANGUAGE', 'catType': 'CATEGORY', 'prefCat': 'PREFERENCE', 'region': 'REGION', 'consulate': 'INTERVIEW LOCATION', 'chartType': 'CHART', 'finalAction': 'Final Action', 'datesForFiling': 'Dates for Filing', 'priorityDate': 'PRIORITY DATE', 'confidence': 'CONFIDENCE', 'history': 'BULLETINS', 'nvcCompleteDate': 'NVC COMPLETE DATE', 'runBtn': 'GENERATE FORECAST', 'heroTitle': 'Visa Bulletin Forecast', 'months': 'months', 'categories': 'categories', 'consulates': 'consulates', 'liveData': 'LIVE', 'employmentBased': 'Employment', 'familyBased': 'Family', 'immediateRelative': 'IR / CR', 'irNote': 'Immediate relative visas are always current.', 'irExplain': 'After NVC complete or documentarily qualified status, the interview depends on the wait time at the selected consulate.', 'nvcComplete': 'NVC COMPLETE', 'avgWaitTime': 'WAIT', 'interviewStart': 'INTERVIEW START', 'interviewEnd': 'INTERVIEW END', 'days': 'days', 'interviewForecast': 'INTERVIEW FORECAST', 'startingPoint': 'STARTING POINT', 'estimatedWindow': 'ESTIMATED WINDOW', 'startingPointCopy': 'NVC complete or documentarily qualified', 'estimatedWindowCopy': 'based on the selected consulate wait time', 'address': 'Address', 'consulateNote': 'Notes', 'estimatedScheduling': 'Estimated scheduling', 'mapView': 'Open in Maps ↗', 'daysToCurrent': 'DAYS REMAINING', 'avgMovement': 'AVG. MOVEMENT', 'currentBy': 'EST. CURRENT', 'interviewWindow': 'INTERVIEW WINDOW', 'cutoffProgression': 'CUTOFF DATE PROGRESSION', 'forecast': 'Forecast', 'movement': 'Data', 'exportTab': 'Export', 'bulletinsLoaded': 'bulletins', 'projectedWindow': 'PROJECTED INTERVIEW WINDOW', 'basedOn': 'Based on', 'monthsOf': 'months of data ·', 'confidenceWord': 'confidence', 'becomeCurrent': 'Become current', 'monthsFromNow': 'months from now', 'interviewSched': 'Interview scheduling', 'nvcNote': 'Includes 2–6 mo NVC buffer', 'mean': 'Mean', 'median': 'Median', 'stddev': 'Std dev', 'bulletinData': 'Download bulletin data CSV', 'forecastReport': 'Download forecast JSON', 'alreadyCurrent': 'This priority date is already current based on the latest available bulletin trend.', 'notEnough': 'Not enough movement data to generate a forecast.', 'retro': 'Recent trend does not support a forward forecast right now.', 'noData': 'No visa bulletin data loaded.', 'consulateCapacity': 'consulate capacity can still move this window'}, 'es': {'label': 'Español', 'flag': '🇲🇽', 'brand': 'VISA FORECAST', 'sub': 'Depto. de Estado · Boletín de Visas', 'language': 'IDIOMA', 'catType': 'CATEGORÍA', 'prefCat': 'PREFERENCIA', 'region': 'REGIÓN', 'consulate': 'LUGAR DE ENTREVISTA', 'chartType': 'GRÁFICO', 'finalAction': 'Acción Final', 'datesForFiling': 'Fechas de Presentación', 'priorityDate': 'FECHA DE PRIORIDAD', 'confidence': 'CONFIANZA', 'history': 'BOLETINES', 'nvcCompleteDate': 'FECHA DE NVC COMPLETE', 'runBtn': 'GENERAR PRONÓSTICO', 'heroTitle': 'Pronóstico del Boletín de Visas', 'months': 'meses', 'categories': 'categorías', 'consulates': 'consulados', 'liveData': 'VIVO', 'employmentBased': 'Empleo', 'familyBased': 'Familia', 'immediateRelative': 'IR / CR', 'irNote': 'Las visas IR/CR siempre están al día.', 'irExplain': 'Después de NVC complete o documentarily qualified, la entrevista depende del tiempo de espera del consulado seleccionado.', 'nvcComplete': 'NVC COMPLETE', 'avgWaitTime': 'ESPERA', 'interviewStart': 'ENTREVISTA INICIO', 'interviewEnd': 'ENTREVISTA FIN', 'days': 'días', 'interviewForecast': 'PRONÓSTICO DE ENTREVISTA', 'startingPoint': 'PUNTO DE PARTIDA', 'estimatedWindow': 'VENTANA ESTIMADA', 'startingPointCopy': 'NVC complete o documentarily qualified', 'estimatedWindowCopy': 'basada en la espera del consulado seleccionado', 'address': 'Dirección', 'consulateNote': 'Notas', 'estimatedScheduling': 'Programación estimada', 'mapView': 'Abrir en Maps ↗', 'daysToCurrent': 'DÍAS RESTANTES', 'avgMovement': 'MOV. PROM.', 'currentBy': 'EST. AL DÍA', 'interviewWindow': 'VENTANA DE ENTREVISTA', 'cutoffProgression': 'PROGRESIÓN DE FECHA LÍMITE', 'forecast': 'Pronóstico', 'movement': 'Datos', 'exportTab': 'Exportar', 'bulletinsLoaded': 'boletines', 'projectedWindow': 'VENTANA PROYECTADA DE ENTREVISTA', 'basedOn': 'Basado en', 'monthsOf': 'meses de datos ·', 'confidenceWord': 'confianza', 'becomeCurrent': 'Ponerse al día', 'monthsFromNow': 'meses desde ahora', 'interviewSched': 'Programación de entrevista', 'nvcNote': 'Incluye 2–6 meses de buffer NVC', 'mean': 'Media', 'median': 'Mediana', 'stddev': 'Desv. est.', 'bulletinData': 'Descargar datos CSV', 'forecastReport': 'Descargar pronóstico JSON', 'alreadyCurrent': 'Esta fecha de prioridad ya está al día según la tendencia más reciente del boletín.', 'notEnough': 'No hay suficiente movimiento para generar un pronóstico.', 'retro': 'La tendencia reciente no permite un pronóstico hacia adelante en este momento.', 'noData': 'No se cargaron datos del boletín de visas.', 'consulateCapacity': 'la capacidad del consulado todavía puede mover esta ventana'}, 'zh': {'label': '中文', 'flag': '🇨🇳', 'brand': '签证预测', 'sub': '美国国务院 · 签证公告分析', 'language': '语言', 'catType': '类别', 'prefCat': '优先类别', 'region': '地区', 'consulate': '面试地点', 'chartType': '图表', 'finalAction': '最终行动', 'datesForFiling': '递交日期', 'priorityDate': '优先日期', 'confidence': '置信度', 'history': '公告数量', 'nvcCompleteDate': 'NVC 完成日期', 'runBtn': '生成预测', 'heroTitle': '签证公告预测', 'months': '月', 'categories': '类别', 'consulates': '领馆', 'liveData': '实时', 'employmentBased': '职业移民', 'familyBased': '家庭移民', 'immediateRelative': 'IR / CR', 'irNote': '直系亲属签证始终当前。', 'irExplain': '在 NVC complete 或 documentarily qualified 之后，面试取决于所选领馆的等待时间。', 'nvcComplete': 'NVC 完成', 'avgWaitTime': '等待时间', 'interviewStart': '面试开始', 'interviewEnd': '面试结束', 'days': '天', 'interviewForecast': '面试预测', 'startingPoint': '起点', 'estimatedWindow': '预计窗口', 'startingPointCopy': 'NVC complete 或 documentarily qualified', 'estimatedWindowCopy': '基于所选领馆等待时间', 'address': '地址', 'consulateNote': '备注', 'estimatedScheduling': '预计安排', 'mapView': '打开地图 ↗', 'daysToCurrent': '剩余天数', 'avgMovement': '平均推进', 'currentBy': '预计当前', 'interviewWindow': '面试窗口', 'cutoffProgression': '截止日期走势', 'forecast': '预测', 'movement': '数据', 'exportTab': '导出', 'bulletinsLoaded': '公告', 'projectedWindow': '预计面试窗口', 'basedOn': '基于', 'monthsOf': '个月数据 ·', 'confidenceWord': '置信度', 'becomeCurrent': '变为当前', 'monthsFromNow': '个月后', 'interviewSched': '面试安排', 'nvcNote': '包含 2–6 个月 NVC 缓冲', 'mean': '均值', 'median': '中位数', 'stddev': '标准差', 'bulletinData': '下载 CSV 数据', 'forecastReport': '下载 JSON 预测', 'alreadyCurrent': '根据最新公告趋势，该优先日期已经当前。', 'notEnough': '没有足够的推进数据来生成预测。', 'retro': '近期趋势暂不支持向前预测。', 'noData': '未加载签证公告数据。', 'consulateCapacity': '领馆容量仍可能改变这个窗口'}, 'hi': {'label': 'हिन्दी', 'flag': '🇮🇳', 'brand': 'VISA FORECAST', 'sub': 'U.S. Department of State · Visa Bulletin Analysis', 'language': 'LANGUAGE', 'catType': 'CATEGORY', 'prefCat': 'PREFERENCE', 'region': 'REGION', 'consulate': 'INTERVIEW LOCATION', 'chartType': 'CHART', 'finalAction': 'Final Action', 'datesForFiling': 'Dates for Filing', 'priorityDate': 'PRIORITY DATE', 'confidence': 'CONFIDENCE', 'history': 'BULLETINS', 'nvcCompleteDate': 'NVC COMPLETE DATE', 'runBtn': 'GENERATE FORECAST', 'heroTitle': 'Visa Bulletin Forecast', 'months': 'months', 'categories': 'categories', 'consulates': 'consulates', 'liveData': 'LIVE', 'employmentBased': 'Employment', 'familyBased': 'Family', 'immediateRelative': 'IR / CR', 'irNote': 'Immediate relative visas are always current.', 'irExplain': 'After NVC complete or documentarily qualified status, the interview depends on the wait time at the selected consulate.', 'nvcComplete': 'NVC COMPLETE', 'avgWaitTime': 'WAIT', 'interviewStart': 'INTERVIEW START', 'interviewEnd': 'INTERVIEW END', 'days': 'days', 'interviewForecast': 'INTERVIEW FORECAST', 'startingPoint': 'STARTING POINT', 'estimatedWindow': 'ESTIMATED WINDOW', 'startingPointCopy': 'NVC complete or documentarily qualified', 'estimatedWindowCopy': 'based on the selected consulate wait time', 'address': 'Address', 'consulateNote': 'Notes', 'estimatedScheduling': 'Estimated scheduling', 'mapView': 'Open in Maps ↗', 'daysToCurrent': 'DAYS REMAINING', 'avgMovement': 'AVG. MOVEMENT', 'currentBy': 'EST. CURRENT', 'interviewWindow': 'INTERVIEW WINDOW', 'cutoffProgression': 'CUTOFF DATE PROGRESSION', 'forecast': 'Forecast', 'movement': 'Data', 'exportTab': 'Export', 'bulletinsLoaded': 'bulletins', 'projectedWindow': 'PROJECTED INTERVIEW WINDOW', 'basedOn': 'Based on', 'monthsOf': 'months of data ·', 'confidenceWord': 'confidence', 'becomeCurrent': 'Become current', 'monthsFromNow': 'months from now', 'interviewSched': 'Interview scheduling', 'nvcNote': 'Includes 2–6 mo NVC buffer', 'mean': 'Mean', 'median': 'Median', 'stddev': 'Std dev', 'bulletinData': 'Download bulletin data CSV', 'forecastReport': 'Download forecast JSON', 'alreadyCurrent': 'This priority date is already current based on the latest available bulletin trend.', 'notEnough': 'Not enough movement data to generate a forecast.', 'retro': 'Recent trend does not support a forward forecast right now.', 'noData': 'No visa bulletin data loaded.', 'consulateCapacity': 'consulate capacity can still move this window'}, 'tl': {'label': 'Filipino', 'flag': '🇵🇭', 'brand': 'VISA FORECAST', 'sub': 'U.S. Department of State · Visa Bulletin Analysis', 'language': 'LANGUAGE', 'catType': 'CATEGORY', 'prefCat': 'PREFERENCE', 'region': 'REGION', 'consulate': 'INTERVIEW LOCATION', 'chartType': 'CHART', 'finalAction': 'Final Action', 'datesForFiling': 'Dates for Filing', 'priorityDate': 'PRIORITY DATE', 'confidence': 'CONFIDENCE', 'history': 'BULLETINS', 'nvcCompleteDate': 'NVC COMPLETE DATE', 'runBtn': 'GENERATE FORECAST', 'heroTitle': 'Visa Bulletin Forecast', 'months': 'months', 'categories': 'categories', 'consulates': 'consulates', 'liveData': 'LIVE', 'employmentBased': 'Employment', 'familyBased': 'Family', 'immediateRelative': 'IR / CR', 'irNote': 'Immediate relative visas are always current.', 'irExplain': 'After NVC complete or documentarily qualified status, the interview depends on the wait time at the selected consulate.', 'nvcComplete': 'NVC COMPLETE', 'avgWaitTime': 'WAIT', 'interviewStart': 'INTERVIEW START', 'interviewEnd': 'INTERVIEW END', 'days': 'days', 'interviewForecast': 'INTERVIEW FORECAST', 'startingPoint': 'STARTING POINT', 'estimatedWindow': 'ESTIMATED WINDOW', 'startingPointCopy': 'NVC complete or documentarily qualified', 'estimatedWindowCopy': 'based on the selected consulate wait time', 'address': 'Address', 'consulateNote': 'Notes', 'estimatedScheduling': 'Estimated scheduling', 'mapView': 'Open in Maps ↗', 'daysToCurrent': 'DAYS REMAINING', 'avgMovement': 'AVG. MOVEMENT', 'currentBy': 'EST. CURRENT', 'interviewWindow': 'INTERVIEW WINDOW', 'cutoffProgression': 'CUTOFF DATE PROGRESSION', 'forecast': 'Forecast', 'movement': 'Data', 'exportTab': 'Export', 'bulletinsLoaded': 'bulletins', 'projectedWindow': 'PROJECTED INTERVIEW WINDOW', 'basedOn': 'Based on', 'monthsOf': 'months of data ·', 'confidenceWord': 'confidence', 'becomeCurrent': 'Become current', 'monthsFromNow': 'months from now', 'interviewSched': 'Interview scheduling', 'nvcNote': 'Includes 2–6 mo NVC buffer', 'mean': 'Mean', 'median': 'Median', 'stddev': 'Std dev', 'bulletinData': 'Download bulletin data CSV', 'forecastReport': 'Download forecast JSON', 'alreadyCurrent': 'This priority date is already current based on the latest available bulletin trend.', 'notEnough': 'Not enough movement data to generate a forecast.', 'retro': 'Recent trend does not support a forward forecast right now.', 'noData': 'No visa bulletin data loaded.', 'consulateCapacity': 'consulate capacity can still move this window'}, 'ko': {'label': '한국어', 'flag': '🇰🇷', 'brand': 'VISA FORECAST', 'sub': 'U.S. Department of State · Visa Bulletin Analysis', 'language': 'LANGUAGE', 'catType': 'CATEGORY', 'prefCat': 'PREFERENCE', 'region': 'REGION', 'consulate': 'INTERVIEW LOCATION', 'chartType': 'CHART', 'finalAction': 'Final Action', 'datesForFiling': 'Dates for Filing', 'priorityDate': 'PRIORITY DATE', 'confidence': 'CONFIDENCE', 'history': 'BULLETINS', 'nvcCompleteDate': 'NVC COMPLETE DATE', 'runBtn': 'GENERATE FORECAST', 'heroTitle': 'Visa Bulletin Forecast', 'months': 'months', 'categories': 'categories', 'consulates': 'consulates', 'liveData': 'LIVE', 'employmentBased': 'Employment', 'familyBased': 'Family', 'immediateRelative': 'IR / CR', 'irNote': 'Immediate relative visas are always current.', 'irExplain': 'After NVC complete or documentarily qualified status, the interview depends on the wait time at the selected consulate.', 'nvcComplete': 'NVC COMPLETE', 'avgWaitTime': 'WAIT', 'interviewStart': 'INTERVIEW START', 'interviewEnd': 'INTERVIEW END', 'days': 'days', 'interviewForecast': 'INTERVIEW FORECAST', 'startingPoint': 'STARTING POINT', 'estimatedWindow': 'ESTIMATED WINDOW', 'startingPointCopy': 'NVC complete or documentarily qualified', 'estimatedWindowCopy': 'based on the selected consulate wait time', 'address': 'Address', 'consulateNote': 'Notes', 'estimatedScheduling': 'Estimated scheduling', 'mapView': 'Open in Maps ↗', 'daysToCurrent': 'DAYS REMAINING', 'avgMovement': 'AVG. MOVEMENT', 'currentBy': 'EST. CURRENT', 'interviewWindow': 'INTERVIEW WINDOW', 'cutoffProgression': 'CUTOFF DATE PROGRESSION', 'forecast': 'Forecast', 'movement': 'Data', 'exportTab': 'Export', 'bulletinsLoaded': 'bulletins', 'projectedWindow': 'PROJECTED INTERVIEW WINDOW', 'basedOn': 'Based on', 'monthsOf': 'months of data ·', 'confidenceWord': 'confidence', 'becomeCurrent': 'Become current', 'monthsFromNow': 'months from now', 'interviewSched': 'Interview scheduling', 'nvcNote': 'Includes 2–6 mo NVC buffer', 'mean': 'Mean', 'median': 'Median', 'stddev': 'Std dev', 'bulletinData': 'Download bulletin data CSV', 'forecastReport': 'Download forecast JSON', 'alreadyCurrent': 'This priority date is already current based on the latest available bulletin trend.', 'notEnough': 'Not enough movement data to generate a forecast.', 'retro': 'Recent trend does not support a forward forecast right now.', 'noData': 'No visa bulletin data loaded.', 'consulateCapacity': 'consulate capacity can still move this window'}, 'vi': {'label': 'Tiếng Việt', 'flag': '🇻🇳', 'brand': 'VISA FORECAST', 'sub': 'U.S. Department of State · Visa Bulletin Analysis', 'language': 'LANGUAGE', 'catType': 'CATEGORY', 'prefCat': 'PREFERENCE', 'region': 'REGION', 'consulate': 'INTERVIEW LOCATION', 'chartType': 'CHART', 'finalAction': 'Final Action', 'datesForFiling': 'Dates for Filing', 'priorityDate': 'PRIORITY DATE', 'confidence': 'CONFIDENCE', 'history': 'BULLETINS', 'nvcCompleteDate': 'NVC COMPLETE DATE', 'runBtn': 'GENERATE FORECAST', 'heroTitle': 'Visa Bulletin Forecast', 'months': 'months', 'categories': 'categories', 'consulates': 'consulates', 'liveData': 'LIVE', 'employmentBased': 'Employment', 'familyBased': 'Family', 'immediateRelative': 'IR / CR', 'irNote': 'Immediate relative visas are always current.', 'irExplain': 'After NVC complete or documentarily qualified status, the interview depends on the wait time at the selected consulate.', 'nvcComplete': 'NVC COMPLETE', 'avgWaitTime': 'WAIT', 'interviewStart': 'INTERVIEW START', 'interviewEnd': 'INTERVIEW END', 'days': 'days', 'interviewForecast': 'INTERVIEW FORECAST', 'startingPoint': 'STARTING POINT', 'estimatedWindow': 'ESTIMATED WINDOW', 'startingPointCopy': 'NVC complete or documentarily qualified', 'estimatedWindowCopy': 'based on the selected consulate wait time', 'address': 'Address', 'consulateNote': 'Notes', 'estimatedScheduling': 'Estimated scheduling', 'mapView': 'Open in Maps ↗', 'daysToCurrent': 'DAYS REMAINING', 'avgMovement': 'AVG. MOVEMENT', 'currentBy': 'EST. CURRENT', 'interviewWindow': 'INTERVIEW WINDOW', 'cutoffProgression': 'CUTOFF DATE PROGRESSION', 'forecast': 'Forecast', 'movement': 'Data', 'exportTab': 'Export', 'bulletinsLoaded': 'bulletins', 'projectedWindow': 'PROJECTED INTERVIEW WINDOW', 'basedOn': 'Based on', 'monthsOf': 'months of data ·', 'confidenceWord': 'confidence', 'becomeCurrent': 'Become current', 'monthsFromNow': 'months from now', 'interviewSched': 'Interview scheduling', 'nvcNote': 'Includes 2–6 mo NVC buffer', 'mean': 'Mean', 'median': 'Median', 'stddev': 'Std dev', 'bulletinData': 'Download bulletin data CSV', 'forecastReport': 'Download forecast JSON', 'alreadyCurrent': 'This priority date is already current based on the latest available bulletin trend.', 'notEnough': 'Not enough movement data to generate a forecast.', 'retro': 'Recent trend does not support a forward forecast right now.', 'noData': 'No visa bulletin data loaded.', 'consulateCapacity': 'consulate capacity can still move this window'}, 'pt': {'label': 'Português', 'flag': '🇧🇷', 'brand': 'VISA FORECAST', 'sub': 'U.S. Department of State · Visa Bulletin Analysis', 'language': 'LANGUAGE', 'catType': 'CATEGORY', 'prefCat': 'PREFERENCE', 'region': 'REGION', 'consulate': 'INTERVIEW LOCATION', 'chartType': 'CHART', 'finalAction': 'Final Action', 'datesForFiling': 'Dates for Filing', 'priorityDate': 'PRIORITY DATE', 'confidence': 'CONFIDENCE', 'history': 'BULLETINS', 'nvcCompleteDate': 'NVC COMPLETE DATE', 'runBtn': 'GENERATE FORECAST', 'heroTitle': 'Visa Bulletin Forecast', 'months': 'months', 'categories': 'categories', 'consulates': 'consulates', 'liveData': 'LIVE', 'employmentBased': 'Employment', 'familyBased': 'Family', 'immediateRelative': 'IR / CR', 'irNote': 'Immediate relative visas are always current.', 'irExplain': 'After NVC complete or documentarily qualified status, the interview depends on the wait time at the selected consulate.', 'nvcComplete': 'NVC COMPLETE', 'avgWaitTime': 'WAIT', 'interviewStart': 'INTERVIEW START', 'interviewEnd': 'INTERVIEW END', 'days': 'days', 'interviewForecast': 'INTERVIEW FORECAST', 'startingPoint': 'STARTING POINT', 'estimatedWindow': 'ESTIMATED WINDOW', 'startingPointCopy': 'NVC complete or documentarily qualified', 'estimatedWindowCopy': 'based on the selected consulate wait time', 'address': 'Address', 'consulateNote': 'Notes', 'estimatedScheduling': 'Estimated scheduling', 'mapView': 'Open in Maps ↗', 'daysToCurrent': 'DAYS REMAINING', 'avgMovement': 'AVG. MOVEMENT', 'currentBy': 'EST. CURRENT', 'interviewWindow': 'INTERVIEW WINDOW', 'cutoffProgression': 'CUTOFF DATE PROGRESSION', 'forecast': 'Forecast', 'movement': 'Data', 'exportTab': 'Export', 'bulletinsLoaded': 'bulletins', 'projectedWindow': 'PROJECTED INTERVIEW WINDOW', 'basedOn': 'Based on', 'monthsOf': 'months of data ·', 'confidenceWord': 'confidence', 'becomeCurrent': 'Become current', 'monthsFromNow': 'months from now', 'interviewSched': 'Interview scheduling', 'nvcNote': 'Includes 2–6 mo NVC buffer', 'mean': 'Mean', 'median': 'Median', 'stddev': 'Std dev', 'bulletinData': 'Download bulletin data CSV', 'forecastReport': 'Download forecast JSON', 'alreadyCurrent': 'This priority date is already current based on the latest available bulletin trend.', 'notEnough': 'Not enough movement data to generate a forecast.', 'retro': 'Recent trend does not support a forward forecast right now.', 'noData': 'No visa bulletin data loaded.', 'consulateCapacity': 'consulate capacity can still move this window'}}

st.markdown('''
<style>
@import url("https://fonts.googleapis.com/css2?family=Instrument+Serif&family=JetBrains+Mono:wght@400;500;600&family=Karla:wght@400;500;600;700&display=swap");
:root{--bg:#0a0a0a;--line:#1a1a1a;--text:#cccccc;--muted:#444444;--accent:#caa072;}
html, body, [class*="css"] { font-family:"Karla", sans-serif; }
.stApp { background: var(--bg); color: var(--text); }
[data-testid="stSidebar"] { background: #0a0a0a; border-right: 1px solid var(--line); }
[data-testid="stSidebar"] > div:first-child { padding-top: 0.8rem; }
section[data-testid="stSidebar"] .stSelectbox label, section[data-testid="stSidebar"] .stDateInput label, section[data-testid="stSidebar"] .stSlider label, section[data-testid="stSidebar"] .stRadio label { font-family: "JetBrains Mono", monospace; font-size: 0.64rem !important; letter-spacing: .11em; color: var(--muted) !important; font-weight: 600; }
div[data-baseweb="select"] > div, .stDateInput > div > div { background: #0e0e0e; border: 1px solid var(--line); }
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
.metric-shell{ border:1px solid var(--line); padding:.95rem 1rem; }
.metric-l{ font-size:.56rem; color:#444; text-transform:uppercase; letter-spacing:.11em; font-weight:600; }
.metric-v{ font-family:"JetBrains Mono", monospace; color:#fff; margin-top:.28rem; }
.section-shell{ border:1px solid var(--line); padding:1rem 1.05rem .6rem 1.05rem; margin-bottom:1rem; }
.consulate-shell{ border:1px solid var(--line); margin-top:1rem; }
.consulate-top{ display:flex; align-items:center; justify-content:space-between; padding:.95rem 1.15rem; border-bottom:1px solid var(--line); background:#0e0e0e; }
.cons-grid{ display:grid; grid-template-columns:1fr 1fr 1fr; }
.cons-cell{ padding:.8rem 1rem; border-right:1px solid var(--line); }
.cons-cell:last-child{ border-right:none; }
.cons-label{ font-size:.56rem; color:#444; text-transform:uppercase; letter-spacing:.09em; font-weight:600; margin-bottom:.2rem; }
.cons-value{ font-size:.75rem; color:#777; line-height:1.55; }
.small-muted{ font-size:.72rem; color:#555; }
</style>
''', unsafe_allow_html=True)

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
        return int(nums[0]), int(nums[0])
    return 60, 120

def metric_block(label: str, value: str, border_color: Optional[str] = None):
    border_style = f"border-left:3px solid {border_color};" if border_color else ""
    st.markdown(f'<div class="metric-shell" style="{border_style}"><div class="metric-l">{label}</div><div class="metric-v">{value}</div></div>', unsafe_allow_html=True)

def consulate_block(consulate: dict, est_early: Optional[datetime], est_late: Optional[datetime], accent: str, tr: dict):
    footer = ""
    if est_early and est_late:
        footer = f'<div style="border-top:1px solid #1a1a1a;padding:.8rem 1.15rem;display:flex;align-items:center;justify-content:space-between;"><div class="cons-label" style="margin:0;">{tr["estimatedScheduling"]}</div><div style="font-family:JetBrains Mono,monospace;font-size:.86rem;color:{accent};">{est_early.strftime("%b %Y")} — {est_late.strftime("%b %Y")}</div></div>'
    st.markdown(f'<div class="consulate-shell"><div class="consulate-top"><div style="display:flex;align-items:center;gap:.65rem;"><div style="font-size:1.15rem;">{consulate.get("flag","📍")}</div><div><div style="font-family:Instrument Serif,serif;font-size:1.15rem;color:#fff;line-height:1;">{consulate["city"]}</div><div style="font-family:JetBrains Mono,monospace;font-size:.62rem;color:#444;margin-top:.18rem;">U.S. {consulate["name"]}</div></div></div><a href="https://www.google.com/maps/search/?api=1&query={consulate["lat"]},{consulate["lng"]}" target="_blank" style="font-family:JetBrains Mono,monospace;font-size:.62rem;color:{accent};text-decoration:none;border:1px solid {accent}33;padding:.35rem .7rem;letter-spacing:.05em;">{tr["mapView"]}</a></div><div class="cons-grid"><div class="cons-cell"><div class="cons-label">{tr["address"]}</div><div class="cons-value">{consulate["addr"]}</div></div><div class="cons-cell"><div class="cons-label">{tr["avgWaitTime"]}</div><div class="cons-value" style="color:{accent};">{consulate["wait"]}</div></div><div class="cons-cell"><div class="cons-label">{tr["consulateNote"]}</div><div class="cons-value">{consulate["note"]}</div></div></div>{footer}</div>', unsafe_allow_html=True)

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
            if "china" in h: col_map[i] = "china_mainland"
            elif "india" in h: col_map[i] = "india"
            elif "mexico" in h: col_map[i] = "mexico"
            elif "philippines" in h: col_map[i] = "philippines"
            elif any(x in h for x in ["all", "world", "other"]): col_map[i] = "all"
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
            for col_index, reg in col_map.items():
                if col_index < len(cells):
                    target[cat_key][reg] = cells[col_index].get_text(strip=True)
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
                for reg, cutoff in regs.items():
                    records.append({"bulletin_date": bulletin_date, "table_type": table_type, "category": cat, "region": reg, "cutoff_raw": cutoff, "cutoff_date": parse_date(cutoff)})
    df = pd.DataFrame(records)
    if not df.empty:
        df.sort_values(["category", "region", "bulletin_date"], inplace=True)
    return df

def movement(df: pd.DataFrame, category: str, region: str, table_type: str):
    mask = (df["category"] == category) & (df["region"] == region) & (df["table_type"] == table_type) & df["cutoff_date"].notna()
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
        return {"status": "CURRENT"}
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
    return {"status":"OK","days_remaining":int(days_remaining),"avg_move":round(avg_move),"projected_current":projected_current,"interview_early":interview_early,"interview_late":interview_late,"months_est":max(1,int(round(months_est))),"n":len(movements),"std_move":round(std_move,1),"current_early":current_early,"current_late":current_late}

def build_progression_chart(mv: pd.DataFrame, priority_date: datetime, fc: dict, accent: str):
    mv = mv.copy().dropna(subset=["cutoff_date"])
    fig = go.Figure()
    if fc.get("status") == "OK":
        band_x = [fc["current_early"], fc["current_late"], fc["current_late"], fc["current_early"]]
        band_y = [priority_date - timedelta(days=35), priority_date - timedelta(days=35), priority_date + timedelta(days=35), priority_date + timedelta(days=35)]
        fig.add_trace(go.Scatter(x=band_x, y=band_y, fill="toself", mode="lines", line=dict(color="rgba(0,0,0,0)"), fillcolor="rgba(202,160,114,0.10)", hoverinfo="skip", name="Forecast range"))
    fig.add_trace(go.Scatter(x=mv["bulletin_date"], y=mv["cutoff_date"], mode="lines+markers", name="Cutoff trend", line=dict(width=2.6, color=accent), marker=dict(size=6, color="#0a0a0a", line=dict(width=1.5, color=accent))))
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



def build_timeline_html(items, accent: str):
    parts = []
    for idx, item in enumerate(items):
        parts.append(f"""
        <div style="display:flex;align-items:flex-start;gap:.8rem;flex:1;">
            <div style="display:flex;flex-direction:column;align-items:center;min-width:16px;">
                <div style="width:12px;height:12px;border-radius:999px;background:{accent};margin-top:4px;"></div>
                {'<div style="width:2px;flex:1;background:#222;min-height:36px;margin-top:6px;"></div>' if idx < len(items)-1 else ''}
            </div>
            <div style="padding-bottom:.6rem;">
                <div class="metric-l" style="margin-bottom:.2rem;">{item['label']}</div>
                <div style="font-family:JetBrains Mono, monospace;color:#fff;font-size:.9rem;">{item['value']}</div>
                <div class="small-muted" style="margin-top:.15rem;">{item.get('note','')}</div>
            </div>
        </div>
        """)
    return '<div class="section-shell">' + "".join(parts) + '</div>'

def parse_wait_mid(wait_str: str) -> int:
    low, high = parse_wait_time(wait_str)
    return int(round((low + high) / 2))

def consulate_comparison(posts: list[dict], selected_post: Optional[dict]):
    if not posts:
        return None
    ranked = sorted(posts, key=lambda p: parse_wait_mid(p["wait"]))
    avg = round(sum(parse_wait_mid(p["wait"]) for p in posts) / len(posts))
    return {
        "selected": selected_post["city"] + " · " + selected_post["wait"] if selected_post else "—",
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
with st.sidebar:
    lang_code = st.selectbox("LANGUAGE", list(TRANSLATIONS.keys()), format_func=lambda k: f'{TRANSLATIONS[k]["flag"]} {TRANSLATIONS[k]["label"]}', key="lang_code")
    tr = TRANSLATIONS[lang_code]

    st.markdown(f'<div class="sidebar-brand"><div class="brand-kicker">{tr["brand"]}</div><div class="brand-sub">{tr["sub"]}</div></div>', unsafe_allow_html=True)
    case_type = st.radio(tr["catType"], ["ir", "family", "employment"], horizontal=True, format_func=lambda v: tr["immediateRelative"] if v=="ir" else tr["familyBased"] if v=="family" else tr["employmentBased"], key="case_type")

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
        table_type = st.selectbox(tr["chartType"], ["final_action", "dates_for_filing"], format_func=lambda x: tr["finalAction"] if x=="final_action" else tr["datesForFiling"], key="table_type")
        priority_date = st.date_input(tr["priorityDate"], datetime(2022,3,15), key="priority_date")
        confidence = st.select_slider(tr["confidence"], [0.8,0.9,0.95], value=0.8, key="confidence")
        history_months = st.slider(tr["history"], 6, 36, 13, key="history_months")
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
    a, b, c = st.columns(3)
    with a:
        st.markdown(f'<div class="mini-stat"><div class="num">12+</div><div class="sub">{tr["months"]}</div></div>', unsafe_allow_html=True)
    with b:
        st.markdown(f'<div class="mini-stat"><div class="num">15</div><div class="sub">{tr["categories"]}</div></div>', unsafe_allow_html=True)
    with c:
        st.markdown(f'<div class="mini-stat"><div class="num">80+</div><div class="sub">{tr["consulates"]}</div></div>', unsafe_allow_html=True)
    st.stop()

if case_type == "ir":
    st.markdown(f'<div class="divider-head"><div><div style="font-family:Instrument Serif, serif;font-size:1.9rem;color:#fff;">{CATEGORY_LABELS.get(category, category)}</div><div class="kicker">{region_label}{" · " + selected_post["city"] if selected_post else ""}</div></div><div class="live-pill">{tr["liveData"]}</div></div>', unsafe_allow_html=True)
    wait_early, wait_late = parse_wait_time(selected_post["wait"]) if selected_post else (60, 120)
    nvc_complete_dt = datetime.combine(nvc_complete_date, datetime.min.time())
    interview_early = nvc_complete_dt + timedelta(days=wait_early)
    interview_late = nvc_complete_dt + timedelta(days=wait_late)

    st.markdown(f'<div class="section-shell"><div style="font-family:Instrument Serif, serif;font-size:1.25rem;color:#fff;margin-bottom:.45rem;">{tr["irNote"]}</div><div class="small-muted">{tr["irExplain"]}</div></div>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1: metric_block(tr["nvcComplete"], nvc_complete_dt.strftime("%b %d, %Y"), "#3498db")
    with c2: metric_block(tr["avgWaitTime"], f"{wait_early}–{wait_late} {tr['days']}", "#2ecc71")
    with c3: metric_block(tr["interviewStart"], interview_early.strftime("%b %Y"), "#f39c12")
    with c4: metric_block(tr["interviewEnd"], interview_late.strftime("%b %Y"), "#e74c3c")

    st.markdown(f'<div class="section-shell"><div class="kicker" style="margin-bottom:.6rem;">{tr["interviewForecast"]}</div><div class="small-muted" style="margin-bottom:.85rem;">{tr["startingPointCopy"]}</div><div style="display:grid;grid-template-columns:1fr 1fr;gap:1px;"><div style="background:#111;padding:.95rem 1rem;"><div class="metric-l">{tr["startingPoint"]}</div><div style="font-family:JetBrains Mono, monospace;color:#fff;margin-top:.3rem;">{nvc_complete_dt.strftime("%B %d, %Y")}</div><div class="small-muted" style="margin-top:.15rem;">{tr["startingPointCopy"]}</div></div><div style="background:#111;padding:.95rem 1rem;"><div class="metric-l">{tr["estimatedWindow"]}</div><div style="font-family:JetBrains Mono, monospace;color:{accent};margin-top:.3rem;">{interview_early.strftime("%b %d, %Y")} — {interview_late.strftime("%b %d, %Y")}</div><div class="small-muted" style="margin-top:.15rem;">{tr["estimatedWindowCopy"]}</div></div></div></div>', unsafe_allow_html=True)

    timeline_items = [
        {"label": tr["nvcComplete"], "value": nvc_complete_dt.strftime("%b %d, %Y"), "note": tr["startingPointCopy"]},
        {"label": tr["avgWaitTime"], "value": f"{wait_early}–{wait_late} {tr['days']}", "note": tr["estimatedWindowCopy"]},
        {"label": tr["interviewWindow"], "value": f"{interview_early.strftime('%b %d, %Y')} — {interview_late.strftime('%b %d, %Y')}", "note": tr["estimatedScheduling"]},
    ]
    st.markdown(f'<div class="kicker" style="margin-bottom:.5rem;">{tr.get("timeline", "Timeline")}</div>', unsafe_allow_html=True)
    st.markdown(build_timeline_html(timeline_items, accent), unsafe_allow_html=True)

    comp = consulate_comparison(posts, selected_post)
    if comp:
        a1, a2, a3, a4 = st.columns(4)
        with a1: metric_block(tr.get("selectedPost", "Selected post"), comp["selected"])
        with a2: metric_block(tr.get("fastestPost", "Fastest post"), comp["fastest"])
        with a3: metric_block(tr.get("slowestPost", "Slowest post"), comp["slowest"])
        with a4: metric_block(tr.get("regionalAverage", "Regional average"), comp["average"])

    with st.expander(tr.get("shareSummary", "Share summary")):
        summary = f"{CATEGORY_LABELS.get(category, category)} | {region_label} | {selected_post['city'] if selected_post else '—'} | NVC complete: {nvc_complete_dt.strftime('%Y-%m-%d')} | Interview estimate: {interview_early.strftime('%Y-%m-%d')} to {interview_late.strftime('%Y-%m-%d')}"
        st.text_area(tr.get("copyReady", "Copy ready summary"), summary, height=90)

    if selected_post:
        consulate_block(selected_post, interview_early, interview_late, accent, tr)
        st.plotly_chart(build_consulate_map(posts, selected_post["id"], accent), use_container_width=True)

    st.markdown(f'<div class="kicker" style="margin-bottom:.5rem;">{tr.get("dataFreshness", "Data freshness")}</div>', unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)
    with f1: metric_block(tr.get("latestBulletin", "Latest bulletin"), latest_bulletin_dt.strftime("%b %Y"))
    with f2: metric_block(tr.get("lastRefresh", "Loaded now"), datetime.now().strftime("%Y-%m-%d %H:%M"))
    with f3: metric_block(tr.get("source", "Source"), tr.get("openSource", "travel.state.gov"))

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

st.markdown(f'<div class="divider-head"><div><div style="font-family:Instrument Serif, serif;font-size:1.9rem;color:#fff;">{region_label} · {CATEGORY_LABELS.get(category, category)}</div><div class="kicker">{selected_post["city"] if selected_post else ""} · {history_months} {tr["bulletinsLoaded"]}</div></div><div class="live-pill">{tr["liveData"]}</div></div>', unsafe_allow_html=True)

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
        with m2: metric_block(tr["avgMovement"], f'{fc["avg_move"]} d/mo')
        with m3: metric_block(tr["currentBy"], fc["projected_current"].strftime("%b %Y"))
        with m4: metric_block(tr["interviewWindow"], f'{fc["interview_early"].strftime("%b %Y")} — {fc["interview_late"].strftime("%b %Y")}')

    st.markdown(f'<div class="section-shell"><div class="kicker" style="margin-bottom:.6rem;">{tr["cutoffProgression"]}</div>', unsafe_allow_html=True)
    st.plotly_chart(build_progression_chart(mv, priority_dt, fc, accent), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if selected_post and fc["status"] == "OK":
        consulate_block(selected_post, fc["interview_early"], fc["interview_late"], accent, tr)
        st.plotly_chart(build_consulate_map(posts, selected_post["id"], accent), use_container_width=True)

    if fc["status"] == "OK":
        st.markdown(f'<div class="section-shell"><div style="font-family:Instrument Serif, serif;font-size:1.18rem;color:#fff;margin-bottom:.45rem;">{tr["projectedWindow"]}</div><div class="small-muted" style="margin-bottom:.9rem;">{tr["basedOn"]} {fc["n"]} {tr["monthsOf"]} {int(confidence*100)}% {tr["confidenceWord"]}. {tr["nvcNote"]}</div><div class="small-muted" style="margin-bottom:.9rem;">{tr.get("uncertainty", "")}</div><div style="display:grid;grid-template-columns:1fr 1fr;gap:1px;"><div style="background:#111;padding:.95rem 1rem;"><div class="metric-l">{tr["becomeCurrent"]}</div><div style="font-family:JetBrains Mono, monospace;color:#fff;margin-top:.3rem;">{fc["projected_current"].strftime("%B %Y")}</div><div class="small-muted" style="margin-top:.15rem;">{fc["months_est"]} {tr["monthsFromNow"]}</div></div><div style="background:#111;padding:.95rem 1rem;"><div class="metric-l">{tr["interviewSched"]}</div><div style="font-family:JetBrains Mono, monospace;color:{accent};margin-top:.3rem;">{fc["interview_early"].strftime("%b %Y")} — {fc["interview_late"].strftime("%b %Y")}</div><div class="small-muted" style="margin-top:.15rem;">{tr["consulateCapacity"]}</div></div></div></div>', unsafe_allow_html=True)

        timeline_items = [
            {"label": tr["priorityDate"], "value": priority_dt.strftime("%b %d, %Y"), "note": CATEGORY_LABELS.get(category, category)},
            {"label": tr["currentBy"], "value": fc["projected_current"].strftime("%b %Y"), "note": tr["becomeCurrent"]},
            {"label": tr["interviewWindow"], "value": f'{fc["interview_early"].strftime("%b %Y")} — {fc["interview_late"].strftime("%b %Y")}', "note": tr["interviewSched"]},
        ]
        st.markdown(f'<div class="kicker" style="margin-bottom:.5rem;">{tr.get("timeline", "Timeline")}</div>', unsafe_allow_html=True)
        st.markdown(build_timeline_html(timeline_items, accent), unsafe_allow_html=True)

        comp = consulate_comparison(posts, selected_post)
        if comp:
            a1, a2, a3, a4 = st.columns(4)
            with a1: metric_block(tr.get("selectedPost", "Selected post"), comp["selected"])
            with a2: metric_block(tr.get("fastestPost", "Fastest post"), comp["fastest"])
            with a3: metric_block(tr.get("slowestPost", "Slowest post"), comp["slowest"])
            with a4: metric_block(tr.get("regionalAverage", "Regional average"), comp["average"])

        with st.expander(tr.get("categoryHelp", "Category help")):
            st.write(category_help_text(category))

        with st.expander(tr.get("shareSummary", "Share summary")):
            summary = f"{CATEGORY_LABELS.get(category, category)} | {region_label} | {selected_post['city'] if selected_post else '—'} | Priority date: {priority_dt.strftime('%Y-%m-%d')} | Current estimate: {fc['projected_current'].strftime('%Y-%m-%d')} | Interview estimate: {fc['interview_early'].strftime('%Y-%m-%d')} to {fc['interview_late'].strftime('%Y-%m-%d')}"
            st.text_area(tr.get("copyReady", "Copy ready summary"), summary, height=90)

        st.markdown(f'<div class="kicker" style="margin-bottom:.5rem;">{tr.get("dataFreshness", "Data freshness")}</div>', unsafe_allow_html=True)
        f1, f2, f3 = st.columns(3)
        with f1: metric_block(tr.get("latestBulletin", "Latest bulletin"), latest_bulletin_dt.strftime("%b %Y"))
        with f2: metric_block(tr.get("lastRefresh", "Loaded now"), datetime.now().strftime("%Y-%m-%d %H:%M"))
        with f3: metric_block(tr.get("source", "Source"), tr.get("openSource", "travel.state.gov"))

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
    json_data = json.dumps({"category": category, "region": region, "table_type": table_type, "priority_date": priority_dt.strftime("%Y-%m-%d"), "forecast_status": fc["status"], "projected_current": fc["projected_current"].strftime("%Y-%m-%d") if fc.get("projected_current") else None, "interview_early": fc["interview_early"].strftime("%Y-%m-%d") if fc.get("interview_early") else None, "interview_late": fc["interview_late"].strftime("%Y-%m-%d") if fc.get("interview_late") else None}, indent=2)
    st.download_button(tr["bulletinData"], csv_data, file_name="visa_bulletin_data.csv", mime="text/csv")
    st.download_button(tr["forecastReport"], json_data, file_name="visa_forecast.json", mime="application/json")

st.markdown('<div style="position:fixed;bottom:10px;right:20px;font-size:10px;color:#555;font-family:JetBrains Mono, monospace;">github.com/roxannehernan</div>', unsafe_allow_html=True)
