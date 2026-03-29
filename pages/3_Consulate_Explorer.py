
import streamlit as st
import pandas as pd
from shared import setup_page, render_lang_picker, render_sidebar_brand, get_lang, CHARGEABILITY_REGIONS, CONSULATES, parse_wait_time

setup_page("Consulate Explorer")
with st.sidebar:
    _, tr = render_lang_picker()
    render_sidebar_brand(tr)

_, tr = get_lang()
st.markdown(f'<div style="max-width:780px;margin-bottom:1.2rem;"><h1 class="hero-title">Consulate Explorer</h1></div>', unsafe_allow_html=True)

region_label = st.selectbox(tr["region"], list(CHARGEABILITY_REGIONS.keys()))
region = CHARGEABILITY_REGIONS[region_label]
posts = CONSULATES.get(region, [])

rows = []
for p in posts:
    low, high = parse_wait_time(p["wait"])
    rows.append({
        "City": p["city"],
        "Post": p["name"],
        "Wait": p["wait"],
        "Fast end": low,
        "Slow end": high,
        "Address": p["addr"],
        "Note": p["note"],
    })

df = pd.DataFrame(rows).sort_values(["Fast end", "Slow end"]) if rows else pd.DataFrame()
if df.empty:
    st.info("No consulates available for this region.")
else:
    st.dataframe(df, use_container_width=True, hide_index=True)
