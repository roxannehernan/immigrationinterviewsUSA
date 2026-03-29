
from datetime import datetime
import json
import pandas as pd
import streamlit as st

from shared import (
    setup_page, render_lang_picker, render_sidebar_brand, get_lang,
    TRANSLATIONS, CHARGEABILITY_REGIONS, CATEGORY_LABELS, CONSULATES,
    FAMILY_CATEGORIES, EMPLOYMENT_CATEGORIES, IR_CATEGORIES,
    fetch_bulletins, forecast, movement, build_progression_chart,
    parse_wait_time, parse_wait_mid, metric_block, consulate_block,
    build_timeline_html, build_consulate_map, category_help_text, build_guide_html
)

def accent_for_case(case_type: str) -> str:
    if case_type == "ir":
        return "#2980b9"
    if case_type == "family":
        return "#8e44ad"
    return "#caa072"

def consulate_comparison(posts, selected_post):
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

setup_page("Visa Bulletin Forecast")

with st.sidebar:
    lang_code, tr = render_lang_picker()
    render_sidebar_brand(tr)

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
        history_months = 13
        nvc_complete_date = None
    else:
        table_type = "final_action"
        priority_date = datetime.today().date()
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
    pass

if case_type == "ir":
    st.markdown(
        f'<div class="divider-head"><div><div style="font-family:Instrument Serif, serif;font-size:1.9rem;color:#fff;">{CATEGORY_LABELS.get(category, category)}</div>'
        f'<div class="kicker">{region_label}{" · " + selected_post["city"] if selected_post else ""}</div></div><div class="live-pill">{tr["liveData"]}</div></div>',
        unsafe_allow_html=True,
    )
    wait_early, wait_late = parse_wait_time(selected_post["wait"]) if selected_post else (60, 120)
    nvc_complete_dt = datetime.combine(nvc_complete_date, datetime.min.time())
    interview_early = nvc_complete_dt + pd.Timedelta(days=wait_early)
    interview_late = nvc_complete_dt + pd.Timedelta(days=wait_late)

    st.markdown(f'<div class="section-shell"><div style="font-family:Instrument Serif, serif;font-size:1.25rem;color:#fff;margin-bottom:.45rem;">{tr["irNote"]}</div><div class="small-muted">{tr["irExplain"]}</div></div>', unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    with m1: metric_block(tr["nvcComplete"], nvc_complete_dt.strftime("%b %d, %Y"), "#3498db")
    with m2: metric_block(tr["avgWaitTime"], f"{wait_early}–{wait_late} {tr['days']}", "#2ecc71")
    with m3: metric_block(tr["interviewStart"], interview_early.strftime("%b %Y"), "#f39c12")
    with m4: metric_block(tr["interviewEnd"], interview_late.strftime("%b %Y"), "#e74c3c")

    st.markdown(f'<div class="kicker" style="margin-bottom:.5rem;">{tr["timeline"]}</div>', unsafe_allow_html=True)
    timeline_items = [
        {"label": tr["nvcComplete"], "value": nvc_complete_dt.strftime("%b %d, %Y"), "note": tr["startingPointCopy"]},
        {"label": tr["avgWaitTime"], "value": f"{wait_early}–{wait_late} {tr["days"]}", "note": tr["estimatedWindowCopy"]},
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
fc = forecast(df, category, region, priority_dt, table_type)
mv = movement(df, category, region, table_type)

st.markdown(
    f'<div class="divider-head"><div><div style="font-family:Instrument Serif, serif;font-size:1.9rem;color:#fff;">{region_label} · {CATEGORY_LABELS.get(category, category)}</div>'
    f'<div class="kicker">{selected_post["city"] if selected_post else ""}</div></div><div class="live-pill">{tr["liveData"]}</div></div>',
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
        with m2: metric_block(tr["avgMovement"], f'{fc["avg_move"]} d/mo')
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
            f'<div class="section-shell"><div style="font-family:Instrument Serif, serif;font-size:1.2rem;color:#fff;margin-bottom:.6rem;">{tr["forecast"]}</div>'
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:1px;">'
            f'<div style="background:#111;padding:.95rem 1rem;"><div class="metric-l">{tr["becomeCurrent"]}</div><div style="font-family:JetBrains Mono, monospace;color:#fff;margin-top:.3rem;">{fc["projected_current"].strftime("%B %Y")}</div><div class="small-muted" style="margin-top:.15rem;">{fc["months_est"]} {tr["monthsFromNow"]}</div></div>'
            f'<div style="background:#111;padding:.95rem 1rem;"><div class="metric-l">{tr["interviewWindow"]}</div><div style="font-family:JetBrains Mono, monospace;color:{accent};margin-top:.3rem;">{fc["interview_early"].strftime("%b %Y")} — {fc["interview_late"].strftime("%b %Y")}</div><div class="small-muted" style="margin-top:.15rem;">{tr["consulateCapacity"]}</div></div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

        st.markdown(f'<div class="kicker" style="margin-bottom:.5rem;">{tr["timeline"]}</div>', unsafe_allow_html=True)
        timeline_items = [
            {"label": tr["priorityDate"], "value": priority_dt.strftime("%b %d, %Y"), "note": CATEGORY_LABELS.get(category, category)},
            {"label": tr["currentBy"], "value": fc["projected_current"].strftime("%b %Y"), "note": tr["becomeCurrent"]},
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
    json_data = json.dumps({"category": category, "region": region, "table_type": table_type, "priority_date": priority_dt.strftime("%Y-%m-%d"), "forecast_status": fc["status"], "projected_current": fc["projected_current"].strftime("%Y-%m-%d") if fc.get("projected_current") else None, "interview_early": fc["interview_early"].strftime("%Y-%m-%d") if fc.get("interview_early") else None, "interview_late": fc["interview_late"].strftime("%Y-%m-%d") if fc.get("interview_late") else None}, indent=2)
    st.download_button(tr["bulletinData"], csv_data, file_name="visa_bulletin_data.csv", mime="text/csv")
    st.download_button(tr["forecastReport"], json_data, file_name="visa_forecast.json", mime="application/json")

st.markdown('<div style="position:fixed;bottom:10px;right:20px;font-size:10px;color:#555;font-family:JetBrains Mono, monospace;">github.com/roxannehernan</div>', unsafe_allow_html=True)
