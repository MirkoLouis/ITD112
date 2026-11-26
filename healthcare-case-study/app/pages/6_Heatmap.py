"""Chart 3: correlation heatmap, R vs Python."""

import streamlit as st

from figure_compare import show_r_vs_python

st.title("Heatmap")
st.write("Correlation of healthcare system indicators and health outcomes.")
show_r_vs_python("03_heatmap")
