"""Streamlit entry point. On Streamlit Community Cloud set the main file
path to healthcare-case-study/app/Home.py."""

import streamlit as st

st.set_page_config(page_title="Healthcare System Indicators", layout="wide")

st.title(
    "Visualization of Healthcare System Indicators and Health Outcomes: "
    "The Philippines in Comparison with East Asia and Pacific Economies, "
    "2000 to 2023"
)
st.write(
    "Use the pages in the sidebar, in order: Dataset, Preparation, EDA, "
    "the four R vs Python charts (Scatterplot, Line Plot, Heatmap, "
    "Cluster Map), R vs Python, Predictive Model, Findings and References."
)
st.caption(
    "Data: World Bank World Development Indicators (WDI), licensed CC BY 4.0."
)
st.warning(
    "Scaffold only: the CSVs in data/processed are stubs with fake rows."
)
