import { useState, useMemo, useEffect } from "react";

const CONSULATES = {
  china_mainland: [
    { id: "gz", name: "Consulate Guangzhou", city: "Guangzhou", addr: "No. 1 Shamian South St", lat: 23.1058, lng: 113.2373, note: "Primary IV post for China", wait: "60–90 days" },
    { id: "bj", name: "Embassy Beijing", city: "Beijing", addr: "No. 55 An Jia Lou Rd", lat: 39.9526, lng: 116.4683, note: "Limited IV processing", wait: "45–75 days" },
    { id: "sh", name: "Consulate Shanghai", city: "Shanghai", addr: "1469 Huaihai Middle Rd", lat: 31.2116, lng: 121.4441, note: "Non-immigrant primarily", wait: "30–60 days" },
  ],
  india: [
    { id: "mum", name: "Consulate Mumbai", city: "Mumbai", addr: "C-49, G-Block, BKC", lat: 19.0596, lng: 72.8656, note: "Highest volume IV post in India", wait: "90–180 days" },
    { id: "del", name: "Embassy New Delhi", city: "New Delhi", addr: "Shantipath, Chanakyapuri", lat: 28.5979, lng: 77.1710, note: "Full IV services", wait: "60–120 days" },
    { id: "che", name: "Consulate Chennai", city: "Chennai", addr: "220 Anna Salai", lat: 13.0604, lng: 80.2497, note: "High EB — South India", wait: "60–120 days" },
    { id: "hyd", name: "Consulate Hyderabad", city: "Hyderabad", addr: "Paigah Palace", lat: 17.4065, lng: 78.4772, note: "Tech corridor — high EB", wait: "90–150 days" },
    { id: "kol", name: "Consulate Kolkata", city: "Kolkata", addr: "5/1 Ho Chi Minh Sarani", lat: 22.5449, lng: 88.3510, note: "Eastern India", wait: "30–60 days" },
  ],
  mexico: [
    { id: "cjs", name: "Consulate Ciudad Juárez", city: "Ciudad Juárez", addr: "Paseo de la Victoria #3650", lat: 31.6904, lng: -106.4245, note: "Highest IV volume worldwide", wait: "60–120 days" },
    { id: "cdmx", name: "Embassy Mexico City", city: "CDMX", addr: "Paseo de la Reforma 305", lat: 19.4276, lng: -99.1677, note: "Largest embassy in W. Hemisphere", wait: "120–240 days" },
    { id: "gdl", name: "Consulate Guadalajara", city: "Guadalajara", addr: "Progreso 175", lat: 20.6722, lng: -103.3625, note: "Western Mexico", wait: "60–90 days" },
    { id: "mty", name: "Consulate Monterrey", city: "Monterrey", addr: "Av. Alfonso Reyes 150", lat: 25.6714, lng: -100.3091, note: "Northeast Mexico", wait: "60–90 days" },
    { id: "tij", name: "Consulate Tijuana", city: "Tijuana", addr: "Paseo de las Culturas", lat: 32.5366, lng: -116.9717, note: "High volume border", wait: "60–90 days" },
  ],
  philippines: [{ id: "mnl", name: "Embassy Manila", city: "Manila", addr: "1201 Roxas Blvd", lat: 14.5619, lng: 120.9801, note: "Busiest IV post worldwide", wait: "90–180 days" }],
  el_salvador: [{ id: "ss", name: "Embassy San Salvador", city: "San Salvador", addr: "Blvd. Santa Elena", lat: 13.6664, lng: -89.2530, note: "Sole post", wait: "60–120 days" }],
  guatemala: [{ id: "gua", name: "Embassy Guatemala City", city: "Guatemala City", addr: "Av. Reforma 7-01", lat: 14.5980, lng: -90.5137, note: "Sole post", wait: "60–120 days" }],
  honduras: [{ id: "tgu", name: "Embassy Tegucigalpa", city: "Tegucigalpa", addr: "Av. La Paz", lat: 14.0910, lng: -87.1963, note: "Sole post", wait: "60–120 days" }],
  vietnam: [
    { id: "hcm", name: "Consulate HCMC", city: "Ho Chi Minh City", addr: "4 Le Duan Blvd", lat: 10.7816, lng: 106.7010, note: "Primary IV post", wait: "60–120 days" },
    { id: "han", name: "Embassy Hanoi", city: "Hanoi", addr: "7 Lang Ha St", lat: 21.0170, lng: 105.8132, note: "Full IV processing", wait: "45–90 days" },
  ],
  korea: [{ id: "sel", name: "Embassy Seoul", city: "Seoul", addr: "188 Sejong-daero", lat: 37.5661, lng: 126.9747, note: "Sole post", wait: "30–60 days" }],
  brazil: [
    { id: "sp", name: "Consulate São Paulo", city: "São Paulo", addr: "Rua Henri Dunant 500", lat: -23.6275, lng: -46.6958, note: "Highest volume Brazil", wait: "60–120 days" },
    { id: "rio", name: "Consulate Rio", city: "Rio de Janeiro", addr: "Av. Pres. Wilson 147", lat: -22.9028, lng: -43.1722, note: "Full IV", wait: "45–90 days" },
  ],
  bangladesh: [{ id: "dhk", name: "Embassy Dhaka", city: "Dhaka", addr: "Madani Ave", lat: 23.8103, lng: 90.4125, note: "High family volume", wait: "90–180 days" }],
  pakistan: [
    { id: "isl", name: "Embassy Islamabad", city: "Islamabad", addr: "Diplomatic Enclave", lat: 33.7215, lng: 73.0884, note: "Primary post", wait: "90–180 days" },
    { id: "khi", name: "Consulate Karachi", city: "Karachi", addr: "Mai Kolachi Rd", lat: 24.8465, lng: 67.0195, note: "Sindh & Balochistan", wait: "60–120 days" },
  ],
  all: [
    { id: "lon", name: "Embassy London", city: "London", addr: "33 Nine Elms Ln", lat: 51.48, lng: -0.12, note: "Major EU/UK post", wait: "30–60 days", flag: "🇬🇧" },
    { id: "fra", name: "Consulate Frankfurt", city: "Frankfurt", addr: "Gießener Str. 30", lat: 50.12, lng: 8.68, note: "Germany — high EB", wait: "30–45 days", flag: "🇩🇪" },
    { id: "mtl", name: "Consulate Montreal", city: "Montreal", addr: "Sainte-Catherine O", lat: 45.50, lng: -73.57, note: "Primary Canadian IV", wait: "30–60 days", flag: "🇨🇦" },
    { id: "syd", name: "Consulate Sydney", city: "Sydney", addr: "19-29 Martin Pl", lat: -33.87, lng: 151.21, note: "AU/NZ/Pacific", wait: "30–45 days", flag: "🇦🇺" },
    { id: "acc", name: "Embassy Accra", city: "Accra", addr: "Fourth Circular Rd", lat: 5.57, lng: -0.18, note: "West Africa hub", wait: "60–120 days", flag: "🇬🇭" },
    { id: "nbo", name: "Embassy Nairobi", city: "Nairobi", addr: "United Nations Ave", lat: -1.24, lng: 36.81, note: "East Africa hub", wait: "60–90 days", flag: "🇰🇪" },
    { id: "dxb", name: "Consulate Dubai", city: "Dubai", addr: "Al Seef Rd", lat: 25.26, lng: 55.30, note: "UAE", wait: "30–60 days", flag: "🇦🇪" },
    { id: "bkk", name: "Embassy Bangkok", city: "Bangkok", addr: "95 Wireless Rd", lat: 13.74, lng: 100.55, note: "Thailand/Laos/Cambodia", wait: "45–90 days", flag: "🇹🇭" },
    { id: "sto", name: "Embassy Santo Domingo", city: "Santo Domingo", addr: "Av. Colombia #57", lat: 18.46, lng: -69.93, note: "High family-based", wait: "60–120 days", flag: "🇩🇴" },
    { id: "bog", name: "Embassy Bogotá", city: "Bogotá", addr: "Calle 24 Bis #48-50", lat: 4.64, lng: -74.09, note: "Colombia", wait: "45–90 days", flag: "🇨🇴" },
    { id: "jnb", name: "Consulate Johannesburg", city: "Johannesburg", addr: "1 Sandton Dr", lat: -26.11, lng: 28.06, note: "Southern Africa", wait: "30–60 days", flag: "🇿🇦" },
    { id: "war", name: "Embassy Warsaw", city: "Warsaw", addr: "Aleje Ujazdowskie", lat: 52.22, lng: 21.02, note: "Poland", wait: "30–45 days", flag: "🇵🇱" },
  ],
};

const T = {
  en: { brand: "VISA FORECAST", sub: "U.S. Department of State · Visa Bulletin Analysis", catType: "CATEGORY", prefCat: "PREFERENCE", region: "REGION", chartType: "CHART", finalAction: "Final Action", datesForFiling: "Dates for Filing", priorityDate: "PRIORITY DATE", runBtn: "GENERATE FORECAST", loading: "Retrieving bulletin data…", heroTitle: "Visa Bulletin Forecast", heroSub: "Consulate interview date projections based on U.S. Department of State visa bulletin cutoff data. Select your category, region, and consulate.", daysToCurrent: "DAYS REMAINING", avgMovement: "AVG. MOVEMENT", currentBy: "EST. CURRENT", interviewWindow: "INTERVIEW WINDOW", cutoffProgression: "CUTOFF DATE PROGRESSION", projectedWindow: "PROJECTED INTERVIEW WINDOW", basedOn: "Based on", monthsOf: "months of data ·", confidence: "confidence", becomeCurrent: "Become current", monthsFromNow: "months from now", interviewSched: "Interview scheduling", nvcNote: "Includes 2–6 mo NVC buffer", bulletin: "MONTH", cutoffDate: "CUTOFF", movementCol: "MOVEMENT", mean: "Mean", median: "Median", bulletinData: "Bulletin Data (CSV)", forecastReport: "Forecast (JSON)", disclaimer: "Statistical estimates only. Not legal advice. Data: travel.state.gov", employmentBased: "Employment", familyBased: "Family", immediateRelative: "IR / CR", language: "LANGUAGE", irNote: "Immediate relative visas are always current — no cutoff applies.", irExplain: "Processing depends on I-130 approval, NVC scheduling, and embassy capacity.", irPetition: "I-130 Petition", irPetitionTime: "6–14 mo", irNvc: "NVC Processing", irNvcTime: "2–6 mo", irInterview: "Consulate Interview", irInterviewTime: "1–3 mo after NVC", irTotal: "Total estimated", irTotalTime: "9–23 months", consulate: "INTERVIEW LOCATION", noConsulates: "No posts for this region", mapView: "Open in Maps", estimatedScheduling: "Est. scheduling", forecast: "Forecast", movement: "Data", exportTab: "Export", liveData: "LIVE", bulletinsLoaded: "bulletins", address: "Address", avgWaitTime: "Scheduling wait", consulateNote: "Notes" },
  es: { brand: "VISA FORECAST", sub: "Depto. de Estado · Boletín de Visas", catType: "CATEGORÍA", prefCat: "PREFERENCIA", region: "REGIÓN", chartType: "GRÁFICO", finalAction: "Acción Final", datesForFiling: "Presentación", priorityDate: "FECHA PRIORIDAD", runBtn: "GENERAR", loading: "Obteniendo datos…", heroTitle: "Pronóstico de Visas", heroSub: "Proyecciones de entrevistas consulares basadas en datos del Departamento de Estado.", daysToCurrent: "DÍAS", avgMovement: "MOV. PROM.", currentBy: "EST. AL DÍA", interviewWindow: "VENTANA", cutoffProgression: "PROGRESIÓN", projectedWindow: "VENTANA PROYECTADA", basedOn: "Basado en", monthsOf: "meses ·", confidence: "confianza", becomeCurrent: "Al día", monthsFromNow: "meses", interviewSched: "Programación", nvcNote: "Incluye 2–6 meses NVC", bulletin: "MES", cutoffDate: "FECHA", movementCol: "MOV.", mean: "Media", median: "Mediana", bulletinData: "CSV", forecastReport: "JSON", disclaimer: "Solo estimaciones. No es asesoría legal.", employmentBased: "Empleo", familyBased: "Familia", immediateRelative: "IR / CR", language: "IDIOMA", irNote: "Las visas IR/CR siempre están al día.", irExplain: "Depende de I-130 y NVC.", irPetition: "I-130", irPetitionTime: "6–14 meses", irNvc: "NVC", irNvcTime: "2–6 meses", irInterview: "Entrevista", irInterviewTime: "1–3 meses", irTotal: "Total", irTotalTime: "9–23 meses", consulate: "LUGAR", noConsulates: "Sin consulados", mapView: "Mapa", estimatedScheduling: "Est.", forecast: "Pronóstico", movement: "Datos", exportTab: "Exportar", liveData: "VIVO", bulletinsLoaded: "boletines", address: "Dirección", avgWaitTime: "Espera", consulateNote: "Notas" },
  zh: { brand: "签证预测", sub: "美国国务院 · 签证公告", catType: "类别", prefCat: "优先", region: "地区", chartType: "图表", finalAction: "最终行动", datesForFiling: "递交日", priorityDate: "优先日", runBtn: "生成预测", loading: "获取中…", heroTitle: "签证公告预测", heroSub: "基于国务院数据的领事面试预测。", daysToCurrent: "剩余天", avgMovement: "平均", currentBy: "预计", interviewWindow: "面试窗口", cutoffProgression: "趋势", projectedWindow: "预计窗口", basedOn: "基于", monthsOf: "月 ·", confidence: "置信度", becomeCurrent: "变当前", monthsFromNow: "月后", interviewSched: "面试", nvcNote: "含2-6月NVC", bulletin: "月", cutoffDate: "截止", movementCol: "进度", mean: "均值", median: "中位", bulletinData: "CSV", forecastReport: "JSON", disclaimer: "仅估计，非法律建议", employmentBased: "职业", familyBased: "亲属", immediateRelative: "直系", language: "语言", irNote: "直系亲属签证始终当前。", irExplain: "取决于I-130和NVC。", irPetition: "I-130", irPetitionTime: "6-14月", irNvc: "NVC", irNvcTime: "2-6月", irInterview: "面试", irInterviewTime: "1-3月", irTotal: "总计", irTotalTime: "9-23月", consulate: "地点", noConsulates: "无", mapView: "地图", estimatedScheduling: "预计", forecast: "预测", movement: "数据", exportTab: "导出", liveData: "实时", bulletinsLoaded: "公告", address: "地址", avgWaitTime: "等待", consulateNote: "备注" },
  hi: { brand: "वीज़ा पूर्वानुमान", sub: "विदेश विभाग · बुलेटिन", catType: "श्रेणी", prefCat: "वरीयता", region: "क्षेत्र", chartType: "चार्ट", finalAction: "अंतिम", datesForFiling: "फाइलिंग", priorityDate: "प्राथमिकता तिथि", runBtn: "पूर्वानुमान", loading: "प्राप्त हो रहा…", heroTitle: "वीज़ा पूर्वानुमान", heroSub: "विदेश विभाग डेटा आधारित अनुमान।", daysToCurrent: "शेष दिन", avgMovement: "औसत", currentBy: "अनुमान", interviewWindow: "साक्षात्कार", cutoffProgression: "प्रगति", projectedWindow: "अनुमानित विंडो", basedOn: "आधारित", monthsOf: "माह ·", confidence: "विश्वास", becomeCurrent: "करंट", monthsFromNow: "माह बाद", interviewSched: "शेड्यूल", nvcNote: "2-6 माह NVC", bulletin: "माह", cutoffDate: "कटऑफ", movementCol: "प्रगति", mean: "औसत", median: "मध्य", bulletinData: "CSV", forecastReport: "JSON", disclaimer: "केवल अनुमान।", employmentBased: "रोज़गार", familyBased: "परिवार", immediateRelative: "IR/CR", language: "भाषा", irNote: "IR/CR हमेशा करंट।", irExplain: "I-130 और NVC पर निर्भर।", irPetition: "I-130", irPetitionTime: "6-14 माह", irNvc: "NVC", irNvcTime: "2-6 माह", irInterview: "साक्षात्कार", irInterviewTime: "1-3 माह", irTotal: "कुल", irTotalTime: "9-23 माह", consulate: "स्थान", noConsulates: "कोई नहीं", mapView: "मानचित्र", estimatedScheduling: "अनुमानित", forecast: "पूर्वानुमान", movement: "डेटा", exportTab: "निर्यात", liveData: "लाइव", bulletinsLoaded: "बुलेटिन", address: "पता", avgWaitTime: "प्रतीक्षा", consulateNote: "नोट" },
  tl: { brand: "VISA FORECAST", sub: "Dept. of State · Bulletin", catType: "KATEGORYA", prefCat: "PREFERENCE", region: "REHIYON", chartType: "TSART", finalAction: "Final Action", datesForFiling: "Filing", priorityDate: "PRIORITY DATE", runBtn: "FORECAST", loading: "Kinukuha…", heroTitle: "Visa Forecast", heroSub: "Projection batay sa Department of State.", daysToCurrent: "ARAW", avgMovement: "AVG", currentBy: "EST.", interviewWindow: "WINDOW", cutoffProgression: "PROGRESSION", projectedWindow: "PROJECTED", basedOn: "Batay sa", monthsOf: "buwan ·", confidence: "confidence", becomeCurrent: "Current", monthsFromNow: "buwan", interviewSched: "Schedule", nvcNote: "2–6 buwan NVC", bulletin: "BUWAN", cutoffDate: "CUTOFF", movementCol: "MOVE", mean: "Mean", median: "Median", bulletinData: "CSV", forecastReport: "JSON", disclaimer: "Tantya lamang.", employmentBased: "Trabaho", familyBased: "Pamilya", immediateRelative: "IR/CR", language: "WIKA", irNote: "IR/CR laging current.", irExplain: "Depende sa I-130.", irPetition: "I-130", irPetitionTime: "6–14 buwan", irNvc: "NVC", irNvcTime: "2–6 buwan", irInterview: "Panayam", irInterviewTime: "1–3 buwan", irTotal: "Total", irTotalTime: "9–23 buwan", consulate: "LUGAR", noConsulates: "Wala", mapView: "Mapa", estimatedScheduling: "Est.", forecast: "Forecast", movement: "Data", exportTab: "Export", liveData: "LIVE", bulletinsLoaded: "bulletin", address: "Address", avgWaitTime: "Wait", consulateNote: "Notes" },
  ko: { brand: "비자예측", sub: "국무부 · 공보 분석", catType: "카테고리", prefCat: "우선", region: "지역", chartType: "차트", finalAction: "최종", datesForFiling: "접수", priorityDate: "우선일", runBtn: "예측 생성", loading: "로딩…", heroTitle: "비자 공보 예측", heroSub: "국무부 데이터 기반 면접 예측.", daysToCurrent: "남은일", avgMovement: "평균", currentBy: "예상", interviewWindow: "면접", cutoffProgression: "추이", projectedWindow: "예상 기간", basedOn: "기반", monthsOf: "월 ·", confidence: "신뢰", becomeCurrent: "현재화", monthsFromNow: "월후", interviewSched: "일정", nvcNote: "2-6월 NVC", bulletin: "월", cutoffDate: "마감", movementCol: "진행", mean: "평균", median: "중앙", bulletinData: "CSV", forecastReport: "JSON", disclaimer: "추정치. 법적 조언 아님.", employmentBased: "취업", familyBased: "가족", immediateRelative: "직계", language: "언어", irNote: "IR/CR은 항상 현재.", irExplain: "I-130 및 NVC에 따름.", irPetition: "I-130", irPetitionTime: "6-14월", irNvc: "NVC", irNvcTime: "2-6월", irInterview: "면접", irInterviewTime: "1-3월", irTotal: "총", irTotalTime: "9-23월", consulate: "장소", noConsulates: "없음", mapView: "지도", estimatedScheduling: "예상", forecast: "예측", movement: "데이터", exportTab: "내보내기", liveData: "실시간", bulletinsLoaded: "공보", address: "주소", avgWaitTime: "대기", consulateNote: "참고" },
  vi: { brand: "DỰ BÁO VISA", sub: "Bộ Ngoại giao · Bản tin Visa", catType: "LOẠI", prefCat: "DANH MỤC", region: "VÙNG", chartType: "BIỂU ĐỒ", finalAction: "Hành động cuối", datesForFiling: "Ngày nộp", priorityDate: "NGÀY ƯU TIÊN", runBtn: "DỰ BÁO", loading: "Đang lấy…", heroTitle: "Dự Báo Visa", heroSub: "Dự báo phỏng vấn lãnh sự.", daysToCurrent: "NGÀY", avgMovement: "TB", currentBy: "DỰ KIẾN", interviewWindow: "CỬA SỔ", cutoffProgression: "TIẾN TRÌNH", projectedWindow: "DỰ KIẾN", basedOn: "Dựa trên", monthsOf: "tháng ·", confidence: "tin cậy", becomeCurrent: "Hiện tại", monthsFromNow: "tháng", interviewSched: "Lịch", nvcNote: "2–6 tháng NVC", bulletin: "THÁNG", cutoffDate: "GIỚI HẠN", movementCol: "TIẾN", mean: "TB", median: "Trung vị", bulletinData: "CSV", forecastReport: "JSON", disclaimer: "Ước tính. Không phải tư vấn.", employmentBased: "Việc làm", familyBased: "Gia đình", immediateRelative: "IR/CR", language: "NGÔN NGỮ", irNote: "IR/CR luôn hiện tại.", irExplain: "Phụ thuộc I-130 và NVC.", irPetition: "I-130", irPetitionTime: "6–14 tháng", irNvc: "NVC", irNvcTime: "2–6 tháng", irInterview: "PV", irInterviewTime: "1–3 tháng", irTotal: "Tổng", irTotalTime: "9–23 tháng", consulate: "NƠI PV", noConsulates: "Không có", mapView: "Bản đồ", estimatedScheduling: "Dự kiến", forecast: "Dự báo", movement: "Dữ liệu", exportTab: "Xuất", liveData: "LIVE", bulletinsLoaded: "bản tin", address: "Địa chỉ", avgWaitTime: "Chờ", consulateNote: "Ghi chú" },
  pt: { brand: "VISA FORECAST", sub: "Dept. de Estado · Boletim", catType: "TIPO", prefCat: "PREFERÊNCIA", region: "REGIÃO", chartType: "GRÁFICO", finalAction: "Ação Final", datesForFiling: "Preenchimento", priorityDate: "DATA PRIORIDADE", runBtn: "GERAR", loading: "Buscando…", heroTitle: "Previsão de Vistos", heroSub: "Projeções de entrevista consular.", daysToCurrent: "DIAS", avgMovement: "MOV", currentBy: "EST.", interviewWindow: "JANELA", cutoffProgression: "PROGRESSÃO", projectedWindow: "PROJETADA", basedOn: "Baseado em", monthsOf: "meses ·", confidence: "confiança", becomeCurrent: "Atual", monthsFromNow: "meses", interviewSched: "Agendamento", nvcNote: "2–6 meses NVC", bulletin: "MÊS", cutoffDate: "LIMITE", movementCol: "MOV.", mean: "Média", median: "Mediana", bulletinData: "CSV", forecastReport: "JSON", disclaimer: "Apenas estimativas.", employmentBased: "Emprego", familyBased: "Família", immediateRelative: "IR/CR", language: "IDIOMA", irNote: "IR/CR sempre atuais.", irExplain: "Depende do I-130 e NVC.", irPetition: "I-130", irPetitionTime: "6–14 meses", irNvc: "NVC", irNvcTime: "2–6 meses", irInterview: "Entrevista", irInterviewTime: "1–3 meses", irTotal: "Total", irTotalTime: "9–23 meses", consulate: "LOCAL", noConsulates: "Sem consulados", mapView: "Mapa", estimatedScheduling: "Est.", forecast: "Previsão", movement: "Dados", exportTab: "Exportar", liveData: "AO VIVO", bulletinsLoaded: "boletins", address: "Endereço", avgWaitTime: "Espera", consulateNote: "Notas" },
};

const LANGS = [
  { code: "en", label: "English", flag: "🇺🇸" }, { code: "es", label: "Español", flag: "🇲🇽" },
  { code: "zh", label: "中文", flag: "🇨🇳" }, { code: "hi", label: "हिन्दी", flag: "🇮🇳" },
  { code: "tl", label: "Filipino", flag: "🇵🇭" }, { code: "ko", label: "한국어", flag: "🇰🇷" },
  { code: "vi", label: "Tiếng Việt", flag: "🇻🇳" }, { code: "pt", label: "Português", flag: "🇧🇷" },
];

const CATS = {
  ir: [{ k: "IR1", l: "IR-1 · Spouse of USC" }, { k: "CR1", l: "CR-1 · Spouse (<2yr)" }, { k: "IR2", l: "IR-2 · Child" }, { k: "IR5", l: "IR-5 · Parent" }, { k: "K1", l: "K-1 · Fiancé(e)" }],
  family: [{ k: "F1", l: "F-1 · Unmarried Sons/Daughters" }, { k: "F2A", l: "F-2A · Spouses/Children" }, { k: "F2B", l: "F-2B · Unmarried Adult Children" }, { k: "F3", l: "F-3 · Married Sons/Daughters" }, { k: "F4", l: "F-4 · Brothers/Sisters" }],
  employment: [{ k: "EB1", l: "EB-1 · Priority Workers" }, { k: "EB2", l: "EB-2 · Advanced Degree" }, { k: "EB3", l: "EB-3 · Skilled Workers" }, { k: "EB4", l: "EB-4 · Special Immigrants" }, { k: "EB5", l: "EB-5 · Investors" }],
};

const REGIONS = [
  { k: "all", l: "Rest of World", f: "🌍" }, { k: "china_mainland", l: "China", f: "🇨🇳" },
  { k: "india", l: "India", f: "🇮🇳" }, { k: "mexico", l: "Mexico", f: "🇲🇽" },
  { k: "philippines", l: "Philippines", f: "🇵🇭" }, { k: "el_salvador", l: "El Salvador", f: "🇸🇻" },
  { k: "guatemala", l: "Guatemala", f: "🇬🇹" }, { k: "honduras", l: "Honduras", f: "🇭🇳" },
  { k: "vietnam", l: "Vietnam", f: "🇻🇳" }, { k: "korea", l: "South Korea", f: "🇰🇷" },
  { k: "brazil", l: "Brazil", f: "🇧🇷" }, { k: "bangladesh", l: "Bangladesh", f: "🇧🇩" },
  { k: "pakistan", l: "Pakistan", f: "🇵🇰" },
];

function generateMock() {
  const ms = ["Apr 25", "May 25", "Jun 25", "Jul 25", "Aug 25", "Sep 25", "Oct 25", "Nov 25", "Dec 25", "Jan 26", "Feb 26", "Mar 26"];
  let c = new Date(2021, 3, 1).getTime();
  return ms.map(function(label, i) {
    var m = i === 0 ? 0 : Math.floor(Math.random() * 55) + 14;
    c += m * 86400000;
    return { label: label, cutoff: new Date(c), cutoffStr: new Date(c).toISOString().slice(0, 10), movement: i === 0 ? null : m };
  });
}

function Chart(props) {
  var data = props.data;
  var priorityDate = props.priorityDate;
  var accent = props.accent;
  var W = 640, H = 220;
  var P = { t: 16, r: 20, b: 36, l: 70 };
  var cw = W - P.l - P.r, ch = H - P.t - P.b;
  var allT = data.map(function(d) { return d.cutoff.getTime(); });
  if (priorityDate) allT.push(priorityDate.getTime());
  var yMin = Math.min.apply(null, allT), yMax = Math.max.apply(null, allT), yR = yMax - yMin || 1;
  var xFn = function(i) { return P.l + (i / (data.length - 1)) * cw; };
  var yFn = function(t) { return P.t + ch - ((t - yMin) / yR) * ch; };
  var fmt = function(d) { return d.toLocaleDateString("en-US", { month: "short", year: "2-digit" }); };
  var linePath = data.map(function(d, i) { return (i === 0 ? "M" : "L") + xFn(i) + "," + yFn(d.cutoff.getTime()); }).join(" ");

  var gridLines = [0, 0.25, 0.5, 0.75, 1].map(function(f, i) {
    return <line key={"g" + i} x1={P.l} x2={W - P.r} y1={P.t + ch * (1 - f)} y2={P.t + ch * (1 - f)} stroke="#1a1a1a" strokeWidth={1} />;
  });

  var yLabels = [0, 0.5, 1].map(function(f, i) {
    return <text key={"y" + i} x={P.l - 8} y={P.t + ch * (1 - f) + 4} textAnchor="end" fontSize={9} fill="#555" fontFamily="'JetBrains Mono', monospace">{fmt(new Date(yMin + yR * f))}</text>;
  });

  var dots = data.map(function(d, i) {
    return <circle key={"d" + i} cx={xFn(i)} cy={yFn(d.cutoff.getTime())} r={2.5} fill="#0a0a0a" stroke={accent} strokeWidth={1.5} />;
  });

  var xLabels = data.filter(function(_, i) { return i % 2 === 0; }).map(function(d) {
    var idx = data.indexOf(d);
    return <text key={"x" + idx} x={xFn(idx)} y={H - 6} textAnchor="middle" fontSize={8.5} fill="#555" fontFamily="'JetBrains Mono', monospace">{d.label}</text>;
  });

  return (
    <svg viewBox={"0 0 " + W + " " + H} style={{ width: "100%" }}>
      {gridLines}
      {yLabels}
      {priorityDate ? (
        <>
          <line x1={P.l} x2={W - P.r} y1={yFn(priorityDate.getTime())} y2={yFn(priorityDate.getTime())} stroke="#c0392b" strokeWidth={1} strokeDasharray="4,3" />
          <text x={W - P.r} y={yFn(priorityDate.getTime()) - 6} textAnchor="end" fontSize={8.5} fill="#c0392b" fontFamily="'JetBrains Mono', monospace" fontWeight={600}>PD</text>
        </>
      ) : null}
      <path d={linePath} fill="none" stroke={accent} strokeWidth={2} strokeLinejoin="round" />
      {dots}
      {xLabels}
    </svg>
  );
}

function Fld(props) {
  return (
    <div>
      <div style={{ fontSize: 9, fontWeight: 600, color: "#333", letterSpacing: ".1em", marginBottom: 4, fontFamily: "'JetBrains Mono', monospace" }}>{props.label}</div>
      {props.children}
    </div>
  );
}

function ConsulateBlock(props) {
  var con = props.con;
  var tr = props.tr;
  var accent = props.accent;
  var intE = props.intE;
  var intL = props.intL;
  var fmtMY = function(d) { return d ? d.toLocaleDateString("en-US", { month: "short", year: "numeric" }) : ""; };
  var rf = REGIONS.find(function(r) { return (CONSULATES[r.k] || []).some(function(c) { return c.id === con.id; }); });

  var details = [
    { l: tr.address, v: con.addr, acc: false },
    { l: tr.avgWaitTime, v: con.wait, acc: true },
    { l: tr.consulateNote, v: con.note, acc: false },
  ];

  return (
    <div style={{ border: "1px solid #1a1a1a", marginTop: 20 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 20px", borderBottom: "1px solid #1a1a1a", background: "#0e0e0e" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 20 }}>{con.flag || (rf ? rf.f : "📍")}</span>
          <div>
            <div style={{ fontFamily: "'Instrument Serif', serif", fontSize: 17, color: "#fff" }}>{con.city}</div>
            <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 9, color: "#444", marginTop: 1 }}>U.S. {con.name}</div>
          </div>
        </div>
        <a href={"https://www.google.com/maps/search/?api=1&query=" + con.lat + "," + con.lng} target="_blank" rel="noopener noreferrer" style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 9, color: accent, textDecoration: "none", border: "1px solid " + accent + "33", padding: "4px 10px", letterSpacing: ".05em" }}>
          {tr.mapView} ↗
        </a>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr" }}>
        {details.map(function(d, i) {
          return (
            <div key={i} style={{ padding: "12px 16px", borderRight: i < 2 ? "1px solid #1a1a1a" : "none" }}>
              <div style={{ fontSize: 8.5, color: "#444", textTransform: "uppercase", letterSpacing: ".08em", fontWeight: 600, marginBottom: 3 }}>{d.l}</div>
              <div style={{ fontSize: 11, color: d.acc ? accent : "#777", lineHeight: 1.5 }}>{d.v}</div>
            </div>
          );
        })}
      </div>
      {intE && intL ? (
        <div style={{ borderTop: "1px solid #1a1a1a", padding: "12px 20px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ fontSize: 9, color: "#444", textTransform: "uppercase", letterSpacing: ".08em", fontWeight: 600 }}>{tr.estimatedScheduling}</div>
          <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 13, color: accent }}>{fmtMY(intE)} — {fmtMY(intL)}</div>
        </div>
      ) : null}
    </div>
  );
}

var selectStyle = { width: "100%", padding: "7px 8px", border: "1px solid #1a1a1a", fontSize: 11.5, color: "#aaa", background: "#0e0e0e", outline: "none", fontFamily: "'Karla', sans-serif" };
var tdStyle = { padding: "8px 14px", fontSize: 12, color: "#666" };

export default function App() {
  var _lang = useState("en");
  var lang = _lang[0], setLang = _lang[1];
  var tr = T[lang];

  var _catType = useState("employment");
  var catType = _catType[0], setCatType = _catType[1];

  var _category = useState("EB2");
  var category = _category[0], setCategory = _category[1];

  var _regionK = useState("india");
  var regionK = _regionK[0], setRegionK = _regionK[1];

  var _pdStr = useState("2022-03-15");
  var pdStr = _pdStr[0], setPdStr = _pdStr[1];

  var _hasRun = useState(false);
  var hasRun = _hasRun[0], setHasRun = _hasRun[1];

  var _loading = useState(false);
  var loading = _loading[0], setLoading = _loading[1];

  var _tab = useState("forecast");
  var tab = _tab[0], setTab = _tab[1];

  var _consulateId = useState("");
  var consulateId = _consulateId[0], setConsulateId = _consulateId[1];

  var cats = CATS[catType];
  var isIR = catType === "ir";
  var data = useMemo(function() { return generateMock(); }, [hasRun]);
  var rc = CONSULATES[regionK] || [];
  var con = rc.find(function(c) { return c.id === consulateId; }) || null;

  useEffect(function() {
    var list = CONSULATES[regionK] || [];
    setConsulateId(list.length > 0 ? list[0].id : "");
  }, [regionK]);

  var pd = new Date(pdStr);
  var last = data[data.length - 1].cutoff;
  var daysRem = Math.max(0, Math.floor((pd - last) / 86400000));
  var moves = data.filter(function(d) { return d.movement !== null; }).map(function(d) { return d.movement; });
  var avg = Math.round(moves.reduce(function(a, b) { return a + b; }, 0) / moves.length);
  var monthsEst = avg > 0 ? Math.ceil(daysRem / avg) : 0;
  var proj = new Date(Date.now() + monthsEst * 30.44 * 86400000);
  var intE = new Date(proj.getTime() + 60 * 86400000);
  var intL = new Date(proj.getTime() + 180 * 86400000);
  var fmtMY = function(d) { return d.toLocaleDateString("en-US", { month: "short", year: "numeric" }); };
  var fmtF = function(d) { return d.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" }); };
  var curR = REGIONS.find(function(r) { return r.k === regionK; });
  var accent = catType === "ir" ? "#2980b9" : catType === "family" ? "#8e44ad" : "#c0392b";

  var handleRun = function() {
    setLoading(true);
    setTimeout(function() { setHasRun(true); setLoading(false); }, 1000);
  };

  var catTypeButtons = [
    { k: "ir", l: tr.immediateRelative },
    { k: "family", l: tr.familyBased },
    { k: "employment", l: tr.employmentBased },
  ];

  var tabButtons = [
    ["forecast", tr.forecast],
    ["table", tr.movement],
    ["export", tr.exportTab],
  ];

  var metrics = [
    { l: tr.daysToCurrent, v: daysRem.toLocaleString(), sm: false },
    { l: tr.avgMovement, v: avg + " d/mo", sm: false },
    { l: tr.currentBy, v: fmtMY(proj), sm: true },
    { l: tr.interviewWindow, v: fmtMY(intE) + " – " + fmtMY(intL), sm: true },
  ];

  var irSteps = [
    { l: tr.irPetition, v: tr.irPetitionTime, c: "#2980b9" },
    { l: tr.irNvc, v: tr.irNvcTime, c: "#27ae60" },
    { l: tr.irInterview, v: tr.irInterviewTime, c: "#f39c12" },
    { l: tr.irTotal, v: tr.irTotalTime, c: "#c0392b" },
  ];

  return (
    <>
      <style>{"\
        @import url('https://fonts.googleapis.com/css2?family=Instrument+Serif&family=JetBrains+Mono:wght@400;500;600&family=Karla:wght@400;500;600;700&display=swap');\
        * { box-sizing: border-box; margin: 0; padding: 0; }\
        ::selection { background: " + accent + "; color: #fff; }\
        ::-webkit-scrollbar { width: 4px; }\
        ::-webkit-scrollbar-track { background: #0a0a0a; }\
        ::-webkit-scrollbar-thumb { background: #222; }\
        select, input[type=date] { color-scheme: dark; }\
        @keyframes spin { to { transform: rotate(360deg); } }\
      "}</style>

      <div style={{ fontFamily: "'Karla', sans-serif", background: "#0a0a0a", minHeight: "100vh", color: "#ccc", display: "flex" }}>
        {/* SIDEBAR */}
        <div style={{ width: 272, minWidth: 272, borderRight: "1px solid #1a1a1a", padding: "20px 18px", display: "flex", flexDirection: "column", gap: 14, overflowY: "auto" }}>
          <div style={{ borderBottom: "1px solid #1a1a1a", paddingBottom: 14 }}>
            <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, fontWeight: 600, letterSpacing: ".15em", color: "#fff" }}>{tr.brand}</div>
            <div style={{ fontSize: 10, color: "#444", marginTop: 2, lineHeight: 1.4 }}>{tr.sub}</div>
          </div>

          <Fld label={tr.language}>
            <select value={lang} onChange={function(e) { setLang(e.target.value); }} style={selectStyle}>
              {LANGS.map(function(l) { return <option key={l.code} value={l.code}>{l.flag} {l.label}</option>; })}
            </select>
          </Fld>

          <Fld label={tr.catType}>
            <div style={{ display: "flex", gap: 1 }}>
              {catTypeButtons.map(function(c) {
                return (
                  <button key={c.k} onClick={function() { setCatType(c.k); setCategory(CATS[c.k][0].k); }} style={{ flex: 1, padding: "6px 2px", fontSize: 10, fontWeight: catType === c.k ? 700 : 400, fontFamily: "'Karla', sans-serif", cursor: "pointer", border: "1px solid " + (catType === c.k ? "#555" : "#1a1a1a"), background: catType === c.k ? "#1a1a1a" : "transparent", color: catType === c.k ? "#fff" : "#555", letterSpacing: ".03em" }}>
                    {c.l}
                  </button>
                );
              })}
            </div>
          </Fld>

          <Fld label={tr.prefCat}>
            <select value={category} onChange={function(e) { setCategory(e.target.value); }} style={selectStyle}>
              {cats.map(function(c) { return <option key={c.k} value={c.k}>{c.l}</option>; })}
            </select>
          </Fld>

          <Fld label={tr.region}>
            <select value={regionK} onChange={function(e) { setRegionK(e.target.value); }} style={selectStyle}>
              {REGIONS.map(function(r) { return <option key={r.k} value={r.k}>{r.f}  {r.l}</option>; })}
            </select>
          </Fld>

          <Fld label={tr.consulate}>
            {rc.length > 0 ? (
              <select value={consulateId} onChange={function(e) { setConsulateId(e.target.value); }} style={selectStyle}>
                {rc.map(function(c) { return <option key={c.id} value={c.id}>{c.city} — {c.name}</option>; })}
              </select>
            ) : (
              <div style={{ fontSize: 10, color: "#333", padding: "4px 0" }}>{tr.noConsulates}</div>
            )}
          </Fld>

          {!isIR ? (
            <Fld label={tr.chartType}>
              <select style={selectStyle}>
                <option>{tr.finalAction}</option>
                <option>{tr.datesForFiling}</option>
              </select>
            </Fld>
          ) : null}

          <div style={{ borderTop: "1px solid #1a1a1a", paddingTop: 12 }}>
            {!isIR ? (
              <Fld label={tr.priorityDate}>
                <input type="date" value={pdStr} onChange={function(e) { setPdStr(e.target.value); }} style={Object.assign({}, selectStyle, { fontFamily: "'JetBrains Mono', monospace" })} />
              </Fld>
            ) : null}
            <button onClick={handleRun} disabled={loading} style={{ width: "100%", padding: "10px", background: loading ? "#111" : "#fff", color: loading ? "#444" : "#000", border: "none", fontSize: 11, fontWeight: 700, letterSpacing: ".1em", cursor: loading ? "wait" : "pointer", fontFamily: "'Karla', sans-serif", marginTop: 8 }}>
              {loading ? tr.loading : tr.runBtn}
            </button>
          </div>

          <div style={{ marginTop: "auto", fontSize: 8.5, color: "#333", lineHeight: 1.6, borderTop: "1px solid #1a1a1a", paddingTop: 10 }}>{tr.disclaimer}</div>
        </div>

        {/* MAIN */}
        <div style={{ flex: 1, padding: "28px 36px", overflowY: "auto" }}>
          {!hasRun && !loading ? (
            <div style={{ maxWidth: 580 }}>
              <h1 style={{ fontFamily: "'Instrument Serif', serif", fontSize: 48, fontWeight: 400, color: "#fff", lineHeight: 1.05, marginBottom: 12, letterSpacing: "-0.02em" }}>{tr.heroTitle}</h1>
              <p style={{ fontSize: 14, color: "#555", lineHeight: 1.8, maxWidth: 500 }}>{tr.heroSub}</p>
              <div style={{ marginTop: 36, display: "flex", gap: 1 }}>
                {[{ n: "12+", s: "months" }, { n: "15", s: "categories" }, { n: "80+", s: "consulates" }].map(function(m, i) {
                  return (
                    <div key={i} style={{ flex: 1, padding: "18px 20px", border: "1px solid #1a1a1a" }}>
                      <div style={{ fontFamily: "'Instrument Serif', serif", fontSize: 32, color: "#fff" }}>{m.n}</div>
                      <div style={{ fontSize: 10, color: "#444", letterSpacing: ".06em", textTransform: "uppercase", marginTop: 2 }}>{m.s}</div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : null}

          {loading ? (
            <div style={{ display: "flex", alignItems: "center", gap: 12, color: "#444", fontSize: 12, marginTop: 40 }}>
              <div style={{ width: 12, height: 12, border: "2px solid #333", borderTopColor: "#888", borderRadius: "50%", animation: "spin .8s linear infinite" }} />
              {tr.loading}
            </div>
          ) : null}

          {hasRun && !loading ? (
            <div>
              <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 4, borderBottom: "1px solid #1a1a1a", paddingBottom: 12 }}>
                <div>
                  <h2 style={{ fontFamily: "'Instrument Serif', serif", fontSize: 28, fontWeight: 400, color: "#fff", letterSpacing: "-0.01em" }}>
                    {curR ? curR.f : ""} {(cats.find(function(c) { return c.k === category; }) || {}).l || category}
                  </h2>
                  <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 9.5, color: "#444", marginTop: 3, letterSpacing: ".05em" }}>
                    {curR ? curR.l : ""}{con ? " · " + con.city : ""} · 12 {tr.bulletinsLoaded}
                  </div>
                </div>
                <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 9, letterSpacing: ".12em", color: accent, border: "1px solid " + accent + "33", padding: "3px 10px" }}>{tr.liveData}</div>
              </div>

              {isIR ? (
                <div style={{ marginTop: 20 }}>
                  <div style={{ border: "1px solid #1a1a1a", padding: "20px 24px", marginBottom: 20 }}>
                    <div style={{ fontFamily: "'Instrument Serif', serif", fontSize: 20, color: "#fff", marginBottom: 8 }}>{tr.irNote}</div>
                    <p style={{ fontSize: 12.5, color: "#555", lineHeight: 1.7 }}>{tr.irExplain}</p>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1 }}>
                    {irSteps.map(function(s, i) {
                      return (
                        <div key={i} style={{ padding: "16px 20px", border: "1px solid #1a1a1a", borderLeft: "3px solid " + s.c }}>
                          <div style={{ fontSize: 9.5, color: "#555", textTransform: "uppercase", letterSpacing: ".07em", fontWeight: 600 }}>{s.l}</div>
                          <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 16, color: "#fff", marginTop: 4 }}>{s.v}</div>
                        </div>
                      );
                    })}
                  </div>
                  {con ? <ConsulateBlock con={con} tr={tr} accent={accent} intE={null} intL={null} /> : null}
                </div>
              ) : (
                <>
                  <div style={{ display: "flex", gap: 0, marginTop: 16, marginBottom: 20, borderBottom: "1px solid #1a1a1a" }}>
                    {tabButtons.map(function(pair) {
                      var k = pair[0], l = pair[1];
                      return (
                        <button key={k} onClick={function() { setTab(k); }} style={{ padding: "8px 18px", fontSize: 10.5, fontWeight: tab === k ? 700 : 400, cursor: "pointer", fontFamily: "'Karla', sans-serif", border: "none", borderBottom: tab === k ? "2px solid " + accent : "2px solid transparent", background: "transparent", color: tab === k ? "#fff" : "#444", letterSpacing: ".04em", textTransform: "uppercase" }}>
                          {l}
                        </button>
                      );
                    })}
                  </div>

                  {tab === "forecast" ? (
                    <>
                      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 1, marginBottom: 22 }}>
                        {metrics.map(function(m, i) {
                          return (
                            <div key={i} style={{ padding: "14px 16px", border: "1px solid #1a1a1a" }}>
                              <div style={{ fontSize: 8.5, color: "#444", textTransform: "uppercase", letterSpacing: ".1em", fontWeight: 600 }}>{m.l}</div>
                              <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: m.sm ? 13 : 18, color: "#fff", marginTop: 4 }}>{m.v}</div>
                            </div>
                          );
                        })}
                      </div>

                      <div style={{ border: "1px solid #1a1a1a", padding: "16px 18px 8px", marginBottom: 20 }}>
                        <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 9, color: "#444", letterSpacing: ".1em", textTransform: "uppercase", marginBottom: 8 }}>{tr.cutoffProgression}</div>
                        <Chart data={data} priorityDate={pd} accent={accent} />
                      </div>

                      {con ? <ConsulateBlock con={con} tr={tr} accent={accent} intE={intE} intL={intL} /> : null}

                      <div style={{ border: "1px solid #1a1a1a", borderLeft: "3px solid " + accent, padding: "20px 24px", marginTop: 20 }}>
                        <div style={{ fontFamily: "'Instrument Serif', serif", fontSize: 18, color: "#fff", marginBottom: 10 }}>{tr.projectedWindow}</div>
                        <div style={{ fontSize: 11, color: "#555", marginBottom: 14 }}>{tr.basedOn} 11 {tr.monthsOf} 80% {tr.confidence}</div>
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1 }}>
                          <div style={{ padding: "14px 16px", background: "#111" }}>
                            <div style={{ fontSize: 8.5, color: "#444", textTransform: "uppercase", letterSpacing: ".08em", fontWeight: 600 }}>{tr.becomeCurrent}</div>
                            <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 15, color: "#fff", marginTop: 4 }}>{fmtF(proj)}</div>
                            <div style={{ fontSize: 10, color: "#333", marginTop: 2 }}>~{monthsEst} {tr.monthsFromNow}</div>
                          </div>
                          <div style={{ padding: "14px 16px", background: "#111" }}>
                            <div style={{ fontSize: 8.5, color: "#444", textTransform: "uppercase", letterSpacing: ".08em", fontWeight: 600 }}>{tr.interviewSched}</div>
                            <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 15, color: accent, marginTop: 4 }}>{fmtMY(intE)} — {fmtMY(intL)}</div>
                            <div style={{ fontSize: 10, color: "#333", marginTop: 2 }}>{tr.nvcNote}</div>
                          </div>
                        </div>
                      </div>
                    </>
                  ) : null}

                  {tab === "table" ? (
                    <div style={{ border: "1px solid #1a1a1a" }}>
                      <table style={{ width: "100%", borderCollapse: "collapse" }}>
                        <thead>
                          <tr>
                            {[tr.bulletin, tr.cutoffDate, tr.movementCol].map(function(h) {
                              return <th key={h} style={{ textAlign: "left", padding: "8px 14px", borderBottom: "1px solid #1a1a1a", fontSize: 8.5, fontWeight: 600, color: "#444", letterSpacing: ".1em", fontFamily: "'JetBrains Mono', monospace" }}>{h}</th>;
                            })}
                          </tr>
                        </thead>
                        <tbody>
                          {data.map(function(d, i) {
                            return (
                              <tr key={i} style={{ borderBottom: "1px solid #111" }}>
                                <td style={tdStyle}>{d.label}</td>
                                <td style={Object.assign({}, tdStyle, { fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#777" })}>{d.cutoffStr}</td>
                                <td style={tdStyle}>
                                  {d.movement !== null ? (
                                    <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, fontWeight: 600, color: d.movement > 35 ? "#27ae60" : d.movement > 15 ? accent : "#c0392b" }}>+{d.movement}d</span>
                                  ) : (
                                    <span style={{ color: "#222" }}>—</span>
                                  )}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                      <div style={{ padding: "8px 14px", borderTop: "1px solid #1a1a1a", fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: "#333" }}>
                        {tr.mean} {avg}d · {tr.median} {avg - 3}d · σ {Math.round(avg * 0.38)}d
                      </div>
                    </div>
                  ) : null}

                  {tab === "export" ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: 1, maxWidth: 360 }}>
                      {[tr.bulletinData, tr.forecastReport].map(function(l, i) {
                        return (
                          <div key={i} style={{ padding: "14px 18px", border: "1px solid #1a1a1a", cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                            <span style={{ fontSize: 12.5, color: "#999" }}>{l}</span>
                            <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: "#444" }}>↓</span>
                          </div>
                        );
                      })}
                    </div>
                  ) : null}
                </>
              )}
            </div>
          ) : null}
        </div>
      </div>
    </>
  );
}
