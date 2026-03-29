
import streamlit as st
from shared import setup_page, render_lang_picker, render_sidebar_brand, get_lang, build_guide_html

setup_page("How it Works")
with st.sidebar:
    _, tr = render_lang_picker()
    render_sidebar_brand(tr)

_, tr = get_lang()
st.markdown(f'<div style="max-width:780px;margin-bottom:1.2rem;"><h1 class="hero-title">{tr["guide_title"]}</h1></div>', unsafe_allow_html=True)
st.markdown(build_guide_html(tr, "family"), unsafe_allow_html=True)
