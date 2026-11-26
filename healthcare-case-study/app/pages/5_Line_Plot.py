"""Chart 2: line plot, R vs Python."""

import streamlit as st

from figure_compare import show_r_vs_python

st.title("Line Plot")
st.write("Life expectancy over time, the Philippines vs East Asia and Pacific.")
show_r_vs_python("02_line")
