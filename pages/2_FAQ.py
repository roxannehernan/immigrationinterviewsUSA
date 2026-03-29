
import streamlit as st
from shared import setup_page, render_lang_picker, render_sidebar_brand, get_lang

setup_page("FAQ")
with st.sidebar:
    _, tr = render_lang_picker()
    render_sidebar_brand(tr)

_, tr = get_lang()
st.markdown(f'<div style="max-width:780px;margin-bottom:1.2rem;"><h1 class="hero-title">{tr["faq"]}</h1></div>', unsafe_allow_html=True)

for q, a in [
    (tr["faq_pd_q"], tr["faq_pd_a"]),
    (tr["faq_fa_q"], tr["faq_fa_a"]),
    (tr["faq_ir_q"], tr["faq_ir_a"]),
    (tr["faq_consulate_q"], tr["faq_consulate_a"]),
]:
    with st.expander(q, expanded=False):
        st.write(a)
