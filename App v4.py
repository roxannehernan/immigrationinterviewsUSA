
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Visa Forecast", layout="wide")

# Dark premium styling
st.markdown("""
<style>
.stApp {background:#050505;color:#e6e6e6;font-family:Inter, sans-serif;}
.block-container {padding-top:1.5rem;}
.card {
    background:#0d0d0d;
    border:1px solid #1f1f1f;
    padding:18px;
    border-radius:10px;
}
.metric {
    font-size:28px;
    font-weight:600;
    color:#ffffff;
}
.label {
    font-size:11px;
    color:#888;
    text-transform:uppercase;
    letter-spacing:.08em;
}
</style>
""", unsafe_allow_html=True)

# Mock data (replace with your pipeline)
dates = pd.date_range(end=datetime.today(), periods=12, freq='M')
cutoffs = pd.to_datetime("2020-01-01") + pd.to_timedelta(np.linspace(0, 900, 12), unit='D')

df = pd.DataFrame({"month": dates, "cutoff": cutoffs})

# Forecast logic (simple projection)
avg_move = (df["cutoff"].diff().dt.days.mean())
last_cutoff = df["cutoff"].iloc[-1]
future_months = pd.date_range(start=dates[-1], periods=6, freq='M')

forecast_cutoffs = [
    last_cutoff + timedelta(days=avg_move * i) for i in range(1,7)
]

forecast_df = pd.DataFrame({
    "month": future_months,
    "cutoff": forecast_cutoffs
})

# Layout
st.title("Visa Bulletin Forecast")

c1, c2, c3 = st.columns(3)

with c1:
    st.markdown('<div class="card"><div class="label">Avg Movement</div><div class="metric">{:.1f} days</div></div>'.format(avg_move), unsafe_allow_html=True)

with c2:
    st.markdown('<div class="card"><div class="label">Latest Cutoff</div><div class="metric">{}</div></div>'.format(last_cutoff.strftime("%b %Y")), unsafe_allow_html=True)

with c3:
    st.markdown('<div class="card"><div class="label">Forecast Horizon</div><div class="metric">6 Months</div></div>', unsafe_allow_html=True)

# Forecast visual (clean + premium)
fig = go.Figure()

# historical
fig.add_trace(go.Scatter(
    x=df["month"],
    y=df["cutoff"],
    mode="lines+markers",
    name="Actual",
    line=dict(width=3),
))

# forecast
fig.add_trace(go.Scatter(
    x=forecast_df["month"],
    y=forecast_df["cutoff"],
    mode="lines+markers",
    name="Forecast",
    line=dict(dash="dash", width=3),
))

# confidence band
upper = forecast_df["cutoff"] + pd.to_timedelta(60, unit='D')
lower = forecast_df["cutoff"] - pd.to_timedelta(60, unit='D')

fig.add_trace(go.Scatter(
    x=list(forecast_df["month"]) + list(forecast_df["month"][::-1]),
    y=list(upper) + list(lower[::-1]),
    fill='toself',
    opacity=0.1,
    line=dict(color='rgba(255,255,255,0)'),
    name="Confidence"
))

fig.update_layout(
    height=420,
    paper_bgcolor="#050505",
    plot_bgcolor="#050505",
    font=dict(color="#aaa"),
    margin=dict(l=10,r=10,t=10,b=10),
    legend=dict(orientation="h", y=1.02),
)

st.plotly_chart(fig, use_container_width=True)

# Map (simple scatter geo)
locations = pd.DataFrame({
    "city": ["Ciudad Juárez", "CDMX", "Mumbai"],
    "lat": [31.74, 19.43, 19.07],
    "lon": [-106.48, -99.13, 72.87]
})

map_fig = go.Figure(go.Scattergeo(
    lat=locations["lat"],
    lon=locations["lon"],
    text=locations["city"],
    mode='markers',
    marker=dict(size=8)
))

map_fig.update_layout(
    geo=dict(
        bgcolor="#050505",
        showland=True,
        landcolor="#0f0f0f",
        countrycolor="#333"
    ),
    paper_bgcolor="#050505",
    height=300,
    margin=dict(l=0,r=0,t=0,b=0)
)

st.plotly_chart(map_fig, use_container_width=True)
