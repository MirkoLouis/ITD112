"""Chart 1: scatterplot, R vs Python."""

import streamlit as st

from figure_compare import show_r_vs_python

st.title("Scatterplot")
st.write("Health spending per capita against life expectancy.")
show_r_vs_python("01_scatter")
