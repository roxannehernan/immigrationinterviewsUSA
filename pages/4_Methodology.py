
import streamlit as st
from shared import setup_page, render_lang_picker, render_sidebar_brand, get_lang

setup_page("Methodology")
with st.sidebar:
    _, tr = render_lang_picker()
    render_sidebar_brand(tr)

_, tr = get_lang()
st.markdown('<div style="max-width:820px;margin-bottom:1.2rem;"><h1 class="hero-title">Methodology</h1></div>', unsafe_allow_html=True)

st.markdown("""
<div class="section-shell">
<div style="font-family:Instrument Serif, serif;font-size:1.2rem;color:#fff;margin-bottom:.35rem;">What the forecast uses</div>
<div class="small-muted">
For family and employment categories, the forecast uses historical visa bulletin movement and projects when a priority date may become current.
For IR and CR categories, the forecast starts from NVC complete and applies the selected consulate wait range.
</div>
</div>
<div class="section-shell">
<div style="font-family:Instrument Serif, serif;font-size:1.2rem;color:#fff;margin-bottom:.35rem;">What it does not do</div>
<div class="small-muted">
This tool does not replace official case status, attorney advice, or embassy communication. It provides directional timing estimates.
</div>
</div>
""", unsafe_allow_html=True)
