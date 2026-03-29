"""
Visa Bulletin Forecast — Streamlit Web App (v4 Editorial)
Deploy: streamlit run app_v4.py
"""
import re, json
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Optional
import requests
from bs4 import BeautifulSoup

st.set_page_config(page_title="Visa Bulletin Forecast", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

BASE_URL = "https://travel.state.gov"
VISA_BULLETIN_INDEX = f"{BASE_URL}/content/travel/en/legal/visa-law0/visa-bulletin.html"
FAMILY_CATEGORIES = ["F1","F2A","F2B","F3","F4"]
EMPLOYMENT_CATEGORIES = ["EB1","EB2","EB3","EB4","EB5"]
IR_CATEGORIES = ["IR1","CR1","IR2","IR5","K1"]
ALL_CATEGORIES = FAMILY_CATEGORIES + EMPLOYMENT_CATEGORIES

CHARGEABILITY_REGIONS = {
    "🌍 Rest of World":"all","🇨🇳 China":"china_mainland","🇮🇳 India":"india",
    "🇲🇽 Mexico":"mexico","🇵🇭 Philippines":"philippines","🇸🇻 El Salvador":"el_salvador",
    "🇬🇹 Guatemala":"guatemala","🇭🇳 Honduras":"honduras","🇻🇳 Vietnam":"vietnam",
    "🇰🇷 South Korea":"korea","🇧🇷 Brazil":"brazil","🇧🇩 Bangladesh":"bangladesh","🇵🇰 Pakistan":"pakistan",
}

CATEGORY_LABELS = {
    "F1":"F-1 · Unmarried Sons/Daughters","F2A":"F-2A · Spouses/Children of LPR",
    "F2B":"F-2B · Unmarried Adult Children","F3":"F-3 · Married Sons/Daughters",
    "F4":"F-4 · Brothers/Sisters","EB1":"EB-1 · Priority Workers",
    "EB2":"EB-2 · Advanced Degree","EB3":"EB-3 · Skilled Workers",
    "EB4":"EB-4 · Special Immigrants","EB5":"EB-5 · Investors",
    "IR1":"IR-1 · Spouse of U.S. Citizen","CR1":"CR-1 · Spouse (<2yr)",
    "IR2":"IR-2 · Child","IR5":"IR-5 · Parent","K1":"K-1 · Fiancé(e)",
}

CONSULATES = {
    "india":[("Mumbai","C-49 BKC","90–180d"),("New Delhi","Shantipath","60–120d"),("Chennai","220 Anna Salai","60–120d"),("Hyderabad","Paigah Palace","90–150d"),("Kolkata","Ho Chi Minh Sarani","30–60d")],
    "china_mainland":[("Guangzhou","Shamian Island","60–90d"),("Beijing","An Jia Lou Rd","45–75d"),("Shanghai","Huaihai Middle Rd","30–60d")],
    "mexico":[("Ciudad Juárez","Paseo de la Victoria","60–120d"),("CDMX","Paseo de la Reforma","120–240d"),("Guadalajara","Progreso 175","60–90d"),("Monterrey","Av. Alfonso Reyes","60–90d"),("Tijuana","Mesa de Otay","60–90d")],
    "philippines":[("Manila","1201 Roxas Blvd","90–180d")],
    "all":[("London","33 Nine Elms Ln","30–60d"),("Frankfurt","Gießener Str.","30–45d"),("Montreal","Sainte-Catherine","30–60d"),("Sydney","19-29 Martin Pl","30–45d"),("Bangkok","95 Wireless Rd","45–90d"),("Santo Domingo","Av. Colombia","60–120d")],
    "vietnam":[("HCMC","4 Le Duan Blvd","60–120d"),("Hanoi","7 Lang Ha St","45–90d")],
    "korea":[("Seoul","188 Sejong-daero","30–60d")],
    "brazil":[("São Paulo","Rua Henri Dunant","60–120d"),("Rio de Janeiro","Av. Pres. Wilson","45–90d")],
    "bangladesh":[("Dhaka","Madani Ave","90–180d")],
    "pakistan":[("Islamabad","Diplomatic Enclave","90–180d"),("Karachi","Mai Kolachi Rd","60–120d")],
    "el_salvador":[("San Salvador","Blvd. Santa Elena","60–120d")],
    "guatemala":[("Guatemala City","Av. Reforma","60–120d")],
    "honduras":[("Tegucigalpa","Av. La Paz","60–120d")],
}

MONTH_MAP = {"january":1,"february":2,"march":3,"april":4,"may":5,"june":6,"july":7,"august":8,"september":9,"october":10,"november":11,"december":12}

st.markdown("""<style>
.stApp{background:#0a0a0a;color:#ccc;font-family:'Karla',sans-serif}
[data-testid="stSidebar"]{background:#0a0a0a!important;border-right:1px solid #1a1a1a}
.m-box{border:1px solid #1a1a1a;padding:14px 16px}
.m-lbl{font-size:9px;color:#444;text-transform:uppercase;letter-spacing:.1em;font-weight:600}
.m-val{font-size:20px;color:#fff;margin-top:4px;font-family:monospace}
.m-val.sm{font-size:14px}
</style>""",unsafe_allow_html=True)

# ─── Scraper ───
@st.cache_data(ttl=3600,show_spinner=False)
def fetch_links(n=13):
    s=requests.Session();s.headers["User-Agent"]="Mozilla/5.0"
    r=s.get(VISA_BULLETIN_INDEX,timeout=30);r.raise_for_status()
    soup=BeautifulSoup(r.text,"html.parser");out=[]
    for a in soup.find_all("a",href=True):
        m=re.search(r"visa-bulletin-for-(\w+)-(\d{4})",a["href"],re.I)
        if m and m.group(1).lower() in MONTH_MAP:
            url=a["href"] if a["href"].startswith("http") else BASE_URL+a["href"]
            out.append({"mn":m.group(1).lower(),"mi":MONTH_MAP[m.group(1).lower()],"yr":int(m.group(2)),"url":url})
    seen=set();u=[]
    for b in out:
        k=(b["yr"],b["mi"])
        if k not in seen:seen.add(k);u.append(b)
    u.sort(key=lambda x:(x["yr"],x["mi"]),reverse=True)
    return u[:n]

def parse_date(raw):
    raw=raw.strip().upper()
    if raw in("C","CURRENT",""):return datetime.today()
    if raw in("U","UNAVAILABLE"):return None
    for f in("%d%b%y","%d%b%Y","%d-%b-%y","%d-%b-%Y","%b %d, %Y","%B %d, %Y"):
        try:return datetime.strptime(raw,f)
        except:pass
    return None

@st.cache_data(ttl=3600,show_spinner=False)
def parse_page(url):
    s=requests.Session();s.headers["User-Agent"]="Mozilla/5.0"
    r=s.get(url,timeout=30);r.raise_for_status();soup=BeautifulSoup(r.text,"html.parser")
    tables=soup.find_all("table");res={"final_action":{},"dates_for_filing":{}}
    for t in tables:
        rows=t.find_all("tr")
        if len(rows)<2:continue
        hdr=[h.get_text(strip=True).lower() for h in rows[0].find_all(["th","td"])]
        prev=t.find_previous(["h2","h3","h4","p","strong"])
        tgt=res["dates_for_filing"] if prev and "filing" in prev.get_text(strip=True).lower() else res["final_action"]
        cm={}
        for i,h in enumerate(hdr):
            if i==0:continue
            if "china" in h:cm[i]="china_mainland"
            elif "india" in h:cm[i]="india"
            elif "mexico" in h:cm[i]="mexico"
            elif "philippines" in h:cm[i]="philippines"
            elif any(x in h for x in["all","world","other"]):cm[i]="all"
        if not cm:continue
        for row in rows[1:]:
            cells=row.find_all(["th","td"])
            if not cells:continue
            ct=re.sub(r"[^A-Z0-9_]","",cells[0].get_text(strip=True).upper())
            ck=next((c for c in ALL_CATEGORIES if c.replace("_","") in ct.replace("_","")),None)
            if not ck:continue
            if ck not in tgt:tgt[ck]={}
            for ci,rg in cm.items():
                if ci<len(cells):tgt[ck][rg]=cells[ci].get_text(strip=True)
    return res

def fetch_bulletins(n=13):
    links=fetch_links(n);recs=[];prog=st.progress(0)
    for i,lk in enumerate(links):
        bd=datetime(lk["yr"],lk["mi"],1);prog.progress((i+1)/len(links),text=f'{lk["mn"].title()} {lk["yr"]}')
        try:data=parse_page(lk["url"])
        except:continue
        for tt,cats in data.items():
            for cat,regs in cats.items():
                for rg,ds in regs.items():recs.append({"bulletin_date":bd,"table_type":tt,"category":cat,"region":rg,"cutoff_raw":ds,"cutoff_date":parse_date(ds)})
    prog.empty();df=pd.DataFrame(recs)
    if not df.empty:df.sort_values(["category","region","bulletin_date"],inplace=True)
    return df

def movement(df,cat,reg,tt):
    m=(df["category"]==cat)&(df["region"]==reg)&(df["table_type"]==tt)&(df["cutoff_date"].notna())
    s=df.loc[m].copy().sort_values("bulletin_date")
    s["prev"]=s["cutoff_date"].shift(1);s["move"]=(s["cutoff_date"]-s["prev"]).dt.days
    return s.dropna(subset=["move"])

def forecast(df,cat,reg,pd_dt,tt,conf):
    mv=movement(df,cat,reg,tt)
    if mv.empty:return{"error":True}
    lt=mv.iloc[-1];lc=lt["cutoff_date"];lb=lt["bulletin_date"];dr=(pd_dt-lc).days
    if dr<=0:return{"status":"CURRENT"}
    ms=mv["move"].values;am=np.mean(ms);sm=np.std(ms,ddof=1) if len(ms)>1 else 0
    if am<=0:return{"status":"RETRO"}
    me=dr/am;p=lb+timedelta(days=me*30.44)
    z={.8:1.28,.9:1.645,.95:1.96}.get(conf,1.28)
    de=lb+timedelta(days=(dr/(am+z*sm))*30.44) if sm>0 else p-timedelta(60)
    dl=lb+timedelta(days=(dr/max(am-z*sm,am*.25))*30.44) if sm>0 else p+timedelta(120)
    return{"status":"OK","dr":dr,"am":round(am,1),"p":p,"de":de,"dl":dl,"ie":de+timedelta(60),"il":dl+timedelta(180),"n":len(ms)}

# ─── Sidebar ───
with st.sidebar:
    st.markdown("**VISA FORECAST**")
    st.caption("U.S. Dept. of State · Bulletin Analysis")
    ct=st.radio("Type",["IR/CR","Family","Employment"],horizontal=True)
    is_ir="IR" in ct
    if is_ir:cat=st.selectbox("Category",IR_CATEGORIES,format_func=lambda c:CATEGORY_LABELS.get(c,c))
    elif "Family" in ct:cat=st.selectbox("Category",FAMILY_CATEGORIES,format_func=lambda c:CATEGORY_LABELS.get(c,c))
    else:cat=st.selectbox("Category",EMPLOYMENT_CATEGORIES,format_func=lambda c:CATEGORY_LABELS.get(c,c))
    rl=st.selectbox("Region",list(CHARGEABILITY_REGIONS.keys()));rg=CHARGEABILITY_REGIONS[rl]
    cl=CONSULATES.get(rg,[])
    con=st.selectbox("Interview Location",[c[0] for c in cl]) if cl else None
    sc=next((c for c in cl if c[0]==con),None) if con else None
    if not is_ir:
        tt=st.selectbox("Chart",["final_action","dates_for_filing"],format_func=lambda t:"Final Action" if "final" in t else "Dates for Filing")
        pd_in=st.date_input("Priority Date",datetime(2022,3,15))
        conf=st.select_slider("Confidence",[.8,.9,.95],.8,format_func=lambda x:f"{x:.0%}")
        mo=st.slider("History (months)",6,36,13)
    go_btn=st.button("GENERATE FORECAST",use_container_width=True,type="primary")

# ─── Main ───
if go_btn:
    if is_ir:
        st.markdown(f"## {CATEGORY_LABELS.get(cat,cat)}")
        st.info("IR/CR visas are always current. No visa bulletin cutoff applies.")
        c1,c2,c3,c4=st.columns(4)
        for col,l,v in[(c1,"I-130 Petition","6–14 mo"),(c2,"NVC Processing","2–6 mo"),(c3,"Interview","1–3 mo"),(c4,"Total","9–23 mo")]:
            col.metric(l,v)
        if sc:st.markdown(f"**{sc[0]}** — {sc[1]} · Wait: {sc[2]}")
    else:
        df=fetch_bulletins(mo)
        if df.empty:st.error("No data.");st.stop()
        pd_dt=datetime.combine(pd_in,datetime.min.time())
        fc=forecast(df,cat,rg,pd_dt,tt,conf)
        st.markdown(f"## {rl} · {CATEGORY_LABELS.get(cat,cat)}")
        if fc.get("status")=="OK":
            c1,c2,c3,c4=st.columns(4)
            c1.metric("Days Remaining",f'{fc["dr"]:,}')
            c2.metric("Avg Movement",f'{fc["am"]} d/mo')
            c3.metric("Est. Current",fc["p"].strftime("%b %Y"))
            c4.metric("Interview",f'{fc["ie"].strftime("%b %Y")} – {fc["il"].strftime("%b %Y")}')
        mv=movement(df,cat,rg,tt)
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=mv["bulletin_date"],y=mv["cutoff_date"],mode="lines+markers",line=dict(color="#c0392b",width=2),marker=dict(size=5)))
        fig.add_hline(y=pd_dt,line_dash="dash",line_color="#c0392b",opacity=.4)
        fig.update_layout(template="plotly_dark",paper_bgcolor="#0a0a0a",plot_bgcolor="#0a0a0a",height=350,margin=dict(l=50,r=20,t=20,b=40),font=dict(size=10,color="#555"))
        st.plotly_chart(fig,use_container_width=True)
        if sc and fc.get("status")=="OK":
            st.markdown(f"**📍 {sc[0]}** — {sc[1]} · Scheduling wait: **{sc[2]}** · Est. interview: **{fc['ie'].strftime('%b %Y')} – {fc['il'].strftime('%b %Y')}**")
        with st.expander("Movement Data"):st.dataframe(mv[["bulletin_date","cutoff_date","move"]].rename(columns={"bulletin_date":"Month","cutoff_date":"Cutoff","move":"Days"}),hide_index=True,use_container_width=True)
        st.download_button("↓ CSV",df.to_csv(index=False),"visa_data.csv","text/csv",use_container_width=True)
else:
    st.markdown("# Visa Bulletin Forecast")
    st.markdown("Consulate interview projections from Department of State data. Configure your case in the sidebar and click **Generate Forecast**.")